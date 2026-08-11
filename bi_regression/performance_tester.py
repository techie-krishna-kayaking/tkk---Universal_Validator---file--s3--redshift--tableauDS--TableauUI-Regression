"""
performance_tester.py — Measures Tableau dashboard load & interaction performance.

For each dashboard (and each discovered view), and for N iterations:
  1. COLD load  — the browser HTTP cache is cleared/disabled, then the dashboard
     is loaded from scratch. This is the "uncached" worst-case timing.
  2. WARM load  — the dashboard is reloaded with the cache populated. This is
     the "cached" best-case timing.
  3. Per-chart timing — while the viz renders, every worksheet zone is polled
     and the moment each chart finishes rendering is recorded, so we know how
     long every individual chart took as well as the full-dashboard load.
  4. Filter refresh — if a filter/tab interaction is configured, the time for
     the dashboard to re-render after the interaction is measured.
  5. min / max / average are computed and compared against thresholds.

Results feed the HTML report and the CSV file in the output folder.
"""
from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from playwright.sync_api import Page

from bi_regression.config_parser import TestConfig, PerformanceDashboard
from bi_regression.browser_manager import BrowserManager
from bi_regression.output_manager import OutputManager
from bi_regression.filter_manager import FilterManager
from bi_regression.tab_navigator import TabNavigator


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ChartTiming:
    """Load time of a single chart/worksheet within one dashboard load."""
    name: str
    load_ms: float
    rendered: bool = True


@dataclass
class LoadPass:
    """One full-dashboard load (either cold/uncached or warm/cached)."""
    mode: str                       # "cold" | "warm"
    iteration: int
    full_load_ms: float
    charts: List[ChartTiming] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def chart_count(self) -> int:
        return len(self.charts)

    @property
    def slowest_chart_ms(self) -> float:
        return max((c.load_ms for c in self.charts), default=0.0)


@dataclass
class FilterRefresh:
    iteration: int
    label: str
    refresh_ms: float


@dataclass
class ChartStat:
    """Aggregated per-chart timing across all iterations."""
    name: str
    cold_avg_ms: float
    warm_avg_ms: float
    max_ms: float


@dataclass
class PerfDashboardResult:
    label: str
    url: str
    passed: bool
    loads: List[LoadPass] = field(default_factory=list)
    filter_refreshes: List[FilterRefresh] = field(default_factory=list)
    chart_stats: List[ChartStat] = field(default_factory=list)

    # Full-dashboard load — cold (uncached)
    cold_full_min: float = 0.0
    cold_full_max: float = 0.0
    cold_full_avg: float = 0.0
    # Full-dashboard load — warm (cached)
    warm_full_min: float = 0.0
    warm_full_max: float = 0.0
    warm_full_avg: float = 0.0
    # Filter refresh
    filter_min: float = 0.0
    filter_max: float = 0.0
    filter_avg: float = 0.0
    filter_name: str = ""
    has_filter: bool = False

    chart_count: int = 0
    max_time_ms: float = 0.0

    cold_threshold: float = 0.0
    filter_threshold: float = 0.0
    cold_passed: bool = True
    filter_passed: bool = True

    screenshot_path: str = ""
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Tableau render-detection selectors (same as browser_manager)
# ---------------------------------------------------------------------------

_TABLEAU_SELECTORS = [
    "tableau-viz",
    "#tableau-viz",
    ".tab-storyboard",
    "[data-tb-test-id='DesktopLayout']",
    ".tabCanvas",
    ".vizContainer",
]


# JS run inside each Tableau frame to enumerate worksheet zones and report which
# charts have finished rendering. A zone counts as a chart when it holds a
# graphical render surface (SVG marks, <canvas>, or a server-rendered <img>).
_CHART_PROBE_JS = r"""
() => {
  const zones = Array.from(document.querySelectorAll("div[id^='tabZoneId']"));
  const charts = [];
  let idx = 0;
  for (const z of zones) {
    const svg = z.querySelector('svg');
    const canvas = z.querySelector('canvas');
    const img = z.querySelector('img');
    const surface = svg || canvas || img;
    if (!surface) continue;
    const rect = surface.getBoundingClientRect();
    if (rect.width < 30 || rect.height < 30) continue;

    let isChart = false, ready = false;
    if (svg) {
      const marks = svg.querySelectorAll('path,rect,circle,polygon,line,image,use').length;
      isChart = marks > 0;
      ready = marks > 0;
    } else if (img) {
      isChart = true;
      ready = img.complete && img.naturalWidth > 0;
    } else if (canvas) {
      isChart = true;
      ready = true;
    }
    if (!isChart) continue;

    const loading = !!z.querySelector(
      ".tab-loading-indicator,[class*='oadingIndicator'],[class*='loading-indicator']"
    );
    ready = ready && !loading;

    let name = (z.getAttribute('aria-label') || '').trim();
    if (!name) {
      const t = z.querySelector("[class*='titleText'],.tab-title,.tab-vizHeader");
      if (t) name = (t.textContent || '').trim();
    }
    if (!name) name = 'Chart ' + (idx + 1);
    charts.push({ key: z.id || ('zone_' + idx), name: name.substring(0, 80), ready });
    idx++;
  }
  const spinner = !!document.querySelector(
    ".tab-loading-indicator,.tab-loading,[class*='LoadingIndicator']"
  );
  return { charts, spinner, zoneCount: zones.length };
}
"""


# ---------------------------------------------------------------------------
# PerformanceTester
# ---------------------------------------------------------------------------

class PerformanceTester:
    def __init__(
        self,
        browser_mgr: BrowserManager,
        config: TestConfig,
        output_mgr: OutputManager,
        logger: logging.Logger,
    ):
        self.bm = browser_mgr
        self.config = config
        self.output = output_mgr
        self.logger = logger
        self.perf_cfg = config.performance

    # ------------------------------------------------------------------

    def run(self) -> List[PerfDashboardResult]:
        self.logger.info(
            "[bold magenta]╔══════════════════════════════════════╗[/]"
        )
        self.logger.info(
            "[bold magenta]║       PERFORMANCE TESTING            ║[/]"
        )
        self.logger.info(
            "[bold magenta]╚══════════════════════════════════════╝[/]"
        )

        iterations = self.perf_cfg.iterations
        results: List[PerfDashboardResult] = []

        # Make sure the Tableau/Okta session is live before timing anything
        if self.perf_cfg.dashboards:
            self._ensure_authenticated(self.perf_cfg.dashboards[0].url)

        for dash in self.perf_cfg.dashboards:
            self.logger.info(
                f"[bold]Dashboard:[/] {dash.label}  |  Iterations: {iterations}"
            )
            self.logger.info(f"  URL: [cyan]{dash.url}[/]")

            if dash.test_all_views:
                view_urls = self._discover_view_urls(dash.url)
                if not view_urls:
                    self.logger.warning("  No views discovered — falling back to workbook URL")
                    view_urls = [(dash.label, dash.url)]
                else:
                    self.logger.info(f"  Discovered {len(view_urls)} view(s): {[v[0] for v in view_urls]}")
                for view_label, view_url in view_urls:
                    view_dash = dash.model_copy(update={"label": f"{dash.label} › {view_label}", "url": view_url, "test_all_views": False})
                    results.append(self._test_dashboard(view_dash, iterations))
            else:
                results.append(self._test_dashboard(dash, iterations))

        self._log_summary(results)
        return results

    # ------------------------------------------------------------------

    def _discover_view_urls(self, workbook_url: str) -> List[tuple]:
        """
        Navigate to a Tableau workbook overview page and return
        [(view_label, absolute_url), ...] for every view found.
        """
        page = self.bm.new_page()
        view_urls: List[tuple] = []
        base = re.match(r"(https?://[^/#]+)", workbook_url)
        base_url = base.group(1) if base else ""
        try:
            self.logger.info(f"  Discovering views from: {workbook_url}")
            page.goto(workbook_url, wait_until="domcontentloaded",
                      timeout=self.config.browser.page_load_timeout)
            page.bring_to_front()
            # If redirected to login, pause and let the user sign in
            self._check_for_sso_redirect(page)
            if page.url != workbook_url:
                page.goto(workbook_url, wait_until="domcontentloaded",
                          timeout=self.config.browser.page_load_timeout)
                page.bring_to_front()
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass

            # Tableau Cloud renders the view list asynchronously (SPA). View
            # links use redirect_to_view/<id> (older versions use /views/).
            anchors_data: list = []
            for _ in range(30):
                anchors_data = self._safe_eval_view_anchors(page)
                if anchors_data:
                    break
                time.sleep(1)

            seen: set = set()
            for o in anchors_data:
                href = o.get("href") or ""
                if href.startswith("http"):
                    abs_url = href
                elif href.startswith("/"):
                    abs_url = base_url + href
                else:
                    abs_url = base_url + "/" + href.lstrip("/")
                if abs_url in seen:
                    continue
                seen.add(abs_url)
                label = (o.get("text") or "").strip() or abs_url.rstrip("/").split("/")[-1]
                view_urls.append((label, abs_url))

            self.logger.info(
                f"  ✅ Discovered {len(view_urls)} view(s): {[v[0] for v in view_urls]}"
            )
        except Exception as e:
            self.logger.error(f"  ❌ View discovery failed: {e}", exc_info=True)
        finally:
            try:
                page.close()
            except Exception:
                pass
        return view_urls

    def _safe_eval_view_anchors(self, page: Page) -> list:
        """Return [{href,text}] for Tableau view links, tolerant of SPA re-renders."""
        js = (
            "els => els"
            ".map(a => ({href: a.getAttribute('href') || '', text: (a.innerText||'').trim().slice(0,60)}))"
            ".filter(o => /redirect_to_view\\/|\\/views\\//.test(o.href))"
        )
        try:
            return page.eval_on_selector_all("a", js) or []
        except Exception:
            return []

    def _resolve_view_url(self, page: Page, redirect_url: str, workbook_url: str) -> Optional[str]:
        """Deprecated: redirect_to_view URLs render directly via goto, no resolution needed."""
        return redirect_url

    # ------------------------------------------------------------------
    # Authentication gate
    # ------------------------------------------------------------------

    def _ensure_authenticated(self, probe_url: str) -> None:
        """Open Tableau and, if the session bounced to SSO/Okta, pause for one login."""
        self.logger.info("  Checking Tableau/Okta session…")
        page = self.bm.new_page()
        try:
            page.goto(probe_url, wait_until="domcontentloaded",
                      timeout=self.config.browser.page_load_timeout)
            page.bring_to_front()
            if self._auth_status(page, timeout=30) == "ok":
                self.logger.info("  [green]✓ Tableau session is active[/]")
                return
            self._prompt_login()
            page.goto(probe_url, wait_until="domcontentloaded",
                      timeout=self.config.browser.page_load_timeout)
            if self._auth_status(page, timeout=120) == "ok":
                self.logger.info("  [green]✓ Logged in — Tableau session active[/]")
            else:
                self.logger.warning("  [yellow]Could not confirm session; continuing anyway[/]")
        finally:
            self._close_page(page)

    def _auth_status(self, page: Page, timeout: int) -> str:
        """Return 'ok' when Tableau views are visible, 'login' when a sign-in is needed."""
        start = time.time()
        auth_since: Optional[float] = None
        while time.time() - start < timeout:
            url = (page.url or "").lower()
            on_auth = ("sso.online.tableau.com" in url or "signin" in url
                       or any(s in url for s in ("okta", "idp", "saml")))
            if "tableau.com" in url and not on_auth:
                try:
                    n = page.eval_on_selector_all(
                        "a",
                        "els => els.filter(a => /redirect_to_view|\\/views\\//.test(a.getAttribute('href')||'')).length",
                    )
                    if n and n > 0:
                        return "ok"
                except Exception:
                    pass
            if on_auth:
                if auth_since is None:
                    auth_since = time.time()
                try:
                    lf = page.eval_on_selector_all(
                        "input[type=password],input[name=identifier],input[name=username]",
                        "els => els.length",
                    )
                except Exception:
                    lf = 0
                if (lf and lf > 0) or (time.time() - auth_since > 8):
                    return "login"
            else:
                auth_since = None
            time.sleep(1)
        return "timeout"

    def _prompt_login(self) -> None:
        print(f"\n{'='*60}")
        print("  LOGIN REQUIRED")
        print("  Your Tableau/Okta session needs a sign-in.")
        print("  → Sign in using the Edge window that just opened,")
        print("    then return here and press Enter to continue.")
        print(f"{'='*60}")
        input("  ▶  Press Enter once you are logged in and can see the dashboards… ")
        time.sleep(5)

    # ------------------------------------------------------------------

    def _test_dashboard(
        self, dash: PerformanceDashboard, num_iterations: int
    ) -> PerfDashboardResult:
        result = PerfDashboardResult(
            label=dash.label,
            url=dash.url,
            passed=False,
            filter_name=self._interaction_label(dash),
            has_filter=dash.interaction is not None,
        )
        screenshot_path = ""

        print(f"\n{'='*60}")
        print(f"TESTING DASHBOARD: {dash.label}")
        print(f"URL: {dash.url}")
        print(f"{'='*60}\n")

        for i in range(1, num_iterations + 1):
            self.logger.info(f"  [cyan]Iteration {i}/{num_iterations}[/]")

            try:
                # ---- COLD (uncached) load — own fresh tab ----
                cold, cold_page = self._load_and_measure(dash, "cold")
                cold.iteration = i
                result.loads.append(cold)
                self.logger.info(
                    f"    ❄️  Cold (uncached) full load: [bold]{cold.full_load_ms:.0f} ms[/] "
                    f"| {cold.chart_count} chart(s) | slowest {cold.slowest_chart_ms:.0f} ms"
                )
                self._close_page(cold_page)

                # ---- WARM (cached) load — own fresh tab, cache now populated ----
                warm, warm_page = self._load_and_measure(dash, "warm")
                warm.iteration = i
                result.loads.append(warm)
                self.logger.info(
                    f"    🔥 Warm (cached) full load: [bold]{warm.full_load_ms:.0f} ms[/] "
                    f"| {warm.chart_count} chart(s) | slowest {warm.slowest_chart_ms:.0f} ms"
                )

                # ---- Screenshot once, after the warm render ----
                if i == 1:
                    screenshot_path = self._take_screenshot(warm_page, dash.label)

                # ---- Filter / interaction refresh (on the warm-loaded page) ----
                if dash.interaction:
                    refresh_ms, applied = self._measure_interaction(warm_page, dash)
                    if applied:
                        result.filter_refreshes.append(
                            FilterRefresh(iteration=i, label=result.filter_name, refresh_ms=refresh_ms)
                        )
                        self.logger.info(
                            f"    🎛️  Filter refresh ({dash.interaction.type}): "
                            f"[bold]{refresh_ms:.0f} ms[/]"
                        )
                    else:
                        self.logger.info(
                            f"    🎛️  Filter '{result.filter_name}' not present on this sheet — skipped"
                        )
                self._close_page(warm_page)

            except Exception as exc:
                self.logger.error(f"    Iteration {i} failed: {exc}")

        result.screenshot_path = screenshot_path
        self._finalize(result, dash)
        self._log_dashboard(result)
        return result

    # ------------------------------------------------------------------
    # Aggregation & logging
    # ------------------------------------------------------------------

    def _finalize(self, result: PerfDashboardResult, dash: PerformanceDashboard) -> None:
        cold_full = [lp.full_load_ms for lp in result.loads if lp.mode == "cold"]
        warm_full = [lp.full_load_ms for lp in result.loads if lp.mode == "warm"]
        filt = [fr.refresh_ms for fr in result.filter_refreshes]

        result.cold_full_min, result.cold_full_max, result.cold_full_avg = _stats(cold_full)
        result.warm_full_min, result.warm_full_max, result.warm_full_avg = _stats(warm_full)
        result.filter_min, result.filter_max, result.filter_avg = _stats(filt)
        # Only report a filter section when the filter was actually applied
        result.has_filter = bool(filt)

        # Per-chart aggregation across iterations
        cold_by_name: Dict[str, List[float]] = defaultdict(list)
        warm_by_name: Dict[str, List[float]] = defaultdict(list)
        order: List[str] = []
        for lp in result.loads:
            for c in lp.charts:
                if c.name not in order:
                    order.append(c.name)
                (cold_by_name if lp.mode == "cold" else warm_by_name)[c.name].append(c.load_ms)

        chart_stats: List[ChartStat] = []
        for name in order:
            c_list = cold_by_name.get(name, [])
            w_list = warm_by_name.get(name, [])
            c_avg = sum(c_list) / len(c_list) if c_list else 0.0
            w_avg = sum(w_list) / len(w_list) if w_list else 0.0
            mx = max(c_list + w_list) if (c_list or w_list) else 0.0
            chart_stats.append(ChartStat(name=name, cold_avg_ms=c_avg, warm_avg_ms=w_avg, max_ms=mx))
        result.chart_stats = chart_stats
        result.chart_count = len(order)

        # Thresholds — first_render_ms applies to the cold (uncached) full load
        result.cold_threshold = dash.thresholds.first_render_ms
        result.filter_threshold = dash.thresholds.interaction_ms
        result.cold_passed = (result.cold_full_avg <= result.cold_threshold) if cold_full else False
        result.filter_passed = (result.filter_avg <= result.filter_threshold) if filt else True
        result.passed = result.cold_passed and result.filter_passed

        # Overall maximum time observed anywhere for this dashboard
        result.max_time_ms = max(
            cold_full + warm_full + [cs.max_ms for cs in chart_stats] + filt + [0.0]
        )

    def _log_dashboard(self, result: PerfDashboardResult) -> None:
        self.logger.info(
            f"  Cold (uncached) — min {result.cold_full_min:.0f} / avg "
            f"[bold]{result.cold_full_avg:.0f}[/] / max {result.cold_full_max:.0f} ms "
            f"(threshold {result.cold_threshold:.0f}) → "
            f"[{'green' if result.cold_passed else 'red'}]{'PASS' if result.cold_passed else 'FAIL'}[/]"
        )
        self.logger.info(
            f"  Warm (cached)   — min {result.warm_full_min:.0f} / avg "
            f"[bold]{result.warm_full_avg:.0f}[/] / max {result.warm_full_max:.0f} ms"
        )
        if result.has_filter:
            self.logger.info(
                f"  Filter refresh  — min {result.filter_min:.0f} / avg "
                f"[bold]{result.filter_avg:.0f}[/] / max {result.filter_max:.0f} ms "
                f"(threshold {result.filter_threshold:.0f}) → "
                f"[{'green' if result.filter_passed else 'red'}]{'PASS' if result.filter_passed else 'FAIL'}[/]"
            )
        for cs in result.chart_stats:
            self.logger.info(
                f"    • {cs.name}: cold {cs.cold_avg_ms:.0f} ms | "
                f"warm {cs.warm_avg_ms:.0f} ms | max {cs.max_ms:.0f} ms"
            )

    # ------------------------------------------------------------------
    # Timing helpers
    # ------------------------------------------------------------------

    def _load_and_measure(
        self, dash: PerformanceDashboard, mode: str
    ):
        """Load the dashboard once in a fresh tab and time the full render + charts.

        Returns (LoadPass, page). The caller owns closing the page (kept open so
        the warm pass can be screenshotted / filtered before closing).

        mode="cold": clear + disable the HTTP cache first (uncached timing).
        mode="warm": load with the cache enabled (cached timing).
        """
        cold = mode == "cold"
        page = self.bm.new_page()

        # Cold = start from an empty cache (cleared) but keep caching ENABLED so
        # this load populates the cache; the following warm load then reuses it.
        try:
            client = page.context.new_cdp_session(page)
            client.send("Network.enable")
            if cold:
                client.send("Network.clearBrowserCache")
        except Exception as e:
            self.logger.debug(f"    CDP cache control unavailable ({e}); timing without cache clear")

        start = time.perf_counter()
        self.logger.info(f"    🌐 [{mode}] Navigating to: {dash.url}")
        page.goto(dash.url, wait_until="domcontentloaded",
                  timeout=self.config.browser.page_load_timeout)
        page.bring_to_front()
        self._check_for_sso_redirect(page)

        charts, full_ms = self._poll_until_loaded(page, start)

        # Settle so the screenshot / next interaction is stable
        time.sleep(self.config.browser.render_wait_seconds)

        return LoadPass(mode=mode, iteration=0, full_load_ms=full_ms, charts=charts), page

    def _close_page(self, page) -> None:
        try:
            if page is not None:
                page.close()
        except Exception:
            pass

    def _poll_until_loaded(self, page: Page, start: float):
        """Poll the viz until the chart set is stable; record per-chart appearance times."""
        deadline = start + (self.config.browser.page_load_timeout / 1000.0)
        first_seen: Dict[str, float] = {}
        names: Dict[str, str] = {}
        full_ms: Optional[float] = None
        stable_since: Optional[float] = None
        last_count = -1

        while time.perf_counter() < deadline:
            info = self._probe(page)
            now = time.perf_counter()
            charts = info.get("charts", [])
            zone_count = info.get("zoneCount", 0)
            spinner = info.get("spinner")
            for c in charts:
                names[c["key"]] = c["name"]
                if c["key"] not in first_seen:
                    first_seen[c["key"]] = (now - start) * 1000.0

            count = len(charts)
            present = count > 0 or zone_count > 0
            # Fully loaded when the chart set is stable and no global spinner.
            # (Per-chart 'ready' flags are unreliable: some zones keep a hidden
            # loading element, so 'all ready' can never become true.)
            if present and not spinner and count == last_count:
                if stable_since is None:
                    stable_since = now
                elif now - stable_since >= 2.0:
                    full_ms = (now - start) * 1000.0
                    break
            else:
                stable_since = None
            last_count = count
            time.sleep(0.5)

        if full_ms is None:
            if not names:
                self.logger.warning("    No worksheet zones detected; using container-render timing.")
                self._wait_for_tableau_rendered(page)
            else:
                self.logger.warning("    Load not confirmed within timeout; recording elapsed time.")
            full_ms = (time.perf_counter() - start) * 1000.0

        timings: List[ChartTiming] = []
        for key, name in names.items():
            timings.append(ChartTiming(name=name, load_ms=first_seen.get(key, full_ms), rendered=True))
        timings.sort(key=lambda c: c.load_ms)
        return timings, full_ms

    def _probe(self, page: Page) -> dict:
        """Run the chart-probe JS in whichever frame exposes the most charts."""
        best = {"charts": [], "spinner": False, "zoneCount": 0}
        for frame in page.frames:
            try:
                r = frame.evaluate(_CHART_PROBE_JS)
            except Exception:
                continue
            if r and len(r.get("charts", [])) >= len(best["charts"]):
                best = r
        return best

    def _take_screenshot(self, page: Page, label: str) -> str:
        ss_path = self.output.perf_screenshot_path(f"render_{_slug(label)}")
        try:
            page.screenshot(path=str(ss_path), full_page=True)
            return str(ss_path)
        except Exception as e:
            self.logger.warning(f"    Screenshot failed: {e}")
            return ""

    def _check_for_sso_redirect(self, page: Page) -> None:
        """Pause and let the user log in if the browser landed on a login page."""
        url_indicators = ("okta", "signin", "login", "signon", "auth", "saml",
                           "idp", "microsoftonline")
        login_selectors = (
            "input[type='password']",
            "input[name='username']",
            "input[name='email']",
        )

        def _needs_login() -> bool:
            cur = (page.url or "").lower()
            if any(s in cur for s in url_indicators):
                return True
            for sel in login_selectors:
                try:
                    if page.locator(sel).count() > 0:
                        return True
                except Exception:
                    pass
            return False

        if not _needs_login():
            return

        print(f"\n{'='*60}")
        print("  LOGIN REQUIRED")
        print("  Tableau Cloud needs you to sign in.")
        print("  → Log in using the Edge window that just opened,")
        print("    then come back here and press Enter to continue.")
        print(f"{'='*60}")
        input("  ▶  Press Enter once you are logged in... ")
        # give the SPA a moment to finish routing after login
        time.sleep(5)

    def _wait_for_tableau_rendered(self, page: Page, label: str = "") -> None:
        """Wait until a Tableau container element appears in any frame."""
        tag = f"[{label}] " if label else ""
        timeout = 60  # seconds
        start = time.time()

        while time.time() - start < timeout:
            for frame in page.frames:
                for sel in _TABLEAU_SELECTORS:
                    try:
                        if frame.locator(sel).count() > 0:
                            # Found a Tableau container — give a small extra settle time
                            time.sleep(self.config.browser.render_wait_seconds)
                            return
                    except Exception:
                        pass
            time.sleep(0.5)

        # Fallback: wait for networkidle
        self.logger.warning(f"{tag}No Tableau selector found — falling back to networkidle.")
        try:
            page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception:
            pass
        time.sleep(self.config.browser.render_wait_seconds)

    def _measure_interaction(self, page: Page, dash: PerformanceDashboard):
        """Perform the configured interaction; return (time_ms, applied)."""
        interaction = dash.interaction
        applied = False
        start = time.perf_counter()

        if interaction.type == "tab_switch":
            nav = TabNavigator(page, self.logger)
            tabs = nav.get_all_tabs()
            target_idx = interaction.tab_index if interaction.tab_index is not None else 1
            if target_idx < len(tabs):
                applied = nav.navigate_to_tab(
                    tabs[target_idx], render_wait=self.config.browser.render_wait_seconds
                )
            else:
                self.logger.warning(
                    f"    Tab index {target_idx} out of range (only {len(tabs)} tabs found)"
                )
        elif interaction.type == "filter":
            if interaction.filter_name and interaction.filter_value:
                from bi_regression.config_parser import FilterSetting
                fm = FilterManager(page, self.logger)
                count = fm.apply_scenario(
                    [FilterSetting(name=interaction.filter_name, value=interaction.filter_value)],
                    render_wait=self.config.browser.render_wait_seconds,
                )
                applied = bool(count)
            else:
                self.logger.warning("    Filter interaction configured but filter_name/filter_value missing")

        end = time.perf_counter()
        return (end - start) * 1000, applied

    def _interaction_label(self, dash: PerformanceDashboard) -> str:
        it = dash.interaction
        if not it:
            return ""
        if it.type == "filter" and it.filter_name:
            return f"{it.filter_name} = {it.filter_value}"
        if it.type == "tab_switch":
            return f"tab #{it.tab_index if it.tab_index is not None else 1}"
        return it.type

    # ------------------------------------------------------------------

    def _log_summary(self, results: List[PerfDashboardResult]):
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        self.logger.info(
            f"[bold]Performance Test Summary:[/] {passed}/{total} dashboard(s) passed."
        )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    return re.sub(r"[^\w]+", "_", name).strip("_").lower()[:40]


def _stats(values: List[float]):
    """Return (min, max, avg) for a list of numbers, or zeros if empty."""
    if not values:
        return 0.0, 0.0, 0.0
    return min(values), max(values), sum(values) / len(values)
