"""
comparison_runner.py — Orchestrates full two-dashboard comparison.

Flow
----
1. Open dashboard_url_1 in Page A, detect all tabs.
2. Open dashboard_url_2 in Page B, detect all tabs.
3. Align tabs by name: matched → compare, unmatched → FAIL with reason.
4. For each matched pair: screenshot both, SSIM diff, save composite.
5. Return list of DiffResult objects for the reporter.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin

from bi_regression.config_parser import TestConfig
from bi_regression.browser_manager import BrowserManager
from bi_regression.tab_navigator import TabNavigator, TabInfo
from bi_regression.visual_diff import DiffResult, compare_images, create_missing_tab_image
from bi_regression.output_manager import OutputManager
from bi_regression.filter_manager import FilterManager


@dataclass
class WorkbookView:
    name: str
    url: str
    index: int


class ComparisonRunner:
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
        self.cfg = config.comparison
        self._deprecated_page_hints: Set[str] = set()

    # ------------------------------------------------------------------

    def run(self) -> List[DiffResult]:
        """Execute the full comparison and return results."""
        cfg_list = self.cfg if isinstance(self.cfg, list) else [self.cfg]
        all_results: List[DiffResult] = []

        for cfg in cfg_list:
            url_a = cfg.dashboard_url_1
            url_b = cfg.dashboard_url_2
            label_a = cfg.label_1
            label_b = cfg.label_2
            threshold = cfg.ssim_threshold

            self.logger.info(
                "[bold yellow]╔══════════════════════════════════════════════╗[/]"
            )
            self.logger.info(
                "[bold yellow]║   REGRESSION / COMPARISON TESTING            ║[/]"
            )
            self.logger.info(
                "[bold yellow]╚══════════════════════════════════════════════╝[/]"
            )
            self.logger.info(f"  {label_a}: {url_a}")
            self.logger.info(f"  {label_b}: {url_b}")

            # Open two tabs in the same authenticated session
            # NOTE: create each page right before navigating — creating both
            # upfront can cause the second page to be invalidated by Tableau's
            # SPA lifecycle when connected via CDP.
            page_a = self.bm.new_page()
            self.bm.navigate_with_retry(page_a, url_a, label=label_a)

            page_b = self.bm.new_page()
            self.bm.navigate_with_retry(page_b, url_b, label=label_b)

            self._deprecated_page_hints = self._normalized_name_set(
                getattr(cfg, "deprecated_pages", None) or []
            )
            if self._deprecated_page_hints:
                self.logger.info(
                    "Configured deprecated page hint(s): %s",
                    ", ".join(sorted(self._deprecated_page_hints))
                )


            if self._is_workbook_url(url_a) and self._is_workbook_url(url_b):
                workbook_results = self._run_workbook_comparison(
                    page_a=page_a,
                    page_b=page_b,
                    cfg=cfg,
                    label_a=label_a,
                    label_b=label_b,
                    threshold=threshold,
                )
                all_results.extend(workbook_results)
            else:
                dashboard_results = self._compare_loaded_dashboards(
                    page_a=page_a,
                    page_b=page_b,
                    label_a=label_a,
                    label_b=label_b,
                    threshold=threshold,
                    tab_name_prefix="",
                    sequence_entity="Page",
                    sequence_slug="sequence_mismatch",
                    filter_scenarios=cfg.filter_scenarios or [],
                    enforce_sequence=bool(getattr(cfg, "enforce_page_sequence", True)),
                )
                all_results.extend(dashboard_results)

            page_a.close()
            page_b.close()

        self._log_summary(all_results)
        return all_results

    def _run_workbook_comparison(
        self,
        page_a,
        page_b,
        cfg,
        label_a: str,
        label_b: str,
        threshold: float,
    ) -> List[DiffResult]:
        """Compare two workbook landing pages by expanding and testing each listed view."""
        results: List[DiffResult] = []

        views_a = self._discover_workbook_views(page_a, label_a)
        views_b = self._discover_workbook_views(page_b, label_b)

        self.logger.info(
            "Workbook views discovered: %s=%d, %s=%d",
            label_a,
            len(views_a),
            label_b,
            len(views_b),
        )

        tabs_a = [TabInfo(name=v.name, index=v.index) for v in views_a]
        tabs_b = [TabInfo(name=v.name, index=v.index) for v in views_b]

        if bool(getattr(cfg, "enforce_page_sequence", True)):
            sequence_result = self._build_sequence_validation_result(
                tabs_a=tabs_a,
                tabs_b=tabs_b,
                label_a=label_a,
                label_b=label_b,
                entity_name="Workbook View",
                artifact_slug="workbook_view_sequence_mismatch",
            )
            if sequence_result:
                results.append(sequence_result)

        view_pairs = TabNavigator.align_tabs(tabs_a, tabs_b, label_a, label_b)

        map_a = {v.name.lower(): v for v in views_a}
        map_b = {v.name.lower(): v for v in views_b}

        for view_a_tab, view_b_tab in view_pairs:
            view_name = view_a_tab.name if view_a_tab.exists else view_b_tab.name
            view_name_key = view_name.strip().lower()

            if not view_a_tab.exists or not view_b_tab.exists:
                reason = view_a_tab.reason if not view_a_tab.exists else view_b_tab.reason
                if view_name_key in self._deprecated_page_hints:
                    reason = f"Deprecated page (configured hint): {reason}"
                else:
                    reason = f"Possible deprecated page (auto-detected): {reason}"

                placeholder = str(self.output.fail_path(f"missing_workbook_view_{_slug(view_name)}"))
                create_missing_tab_image(f"Workbook View: {view_name}", reason, placeholder)
                results.append(
                    DiffResult(
                        tab_name=f"Workbook View: {view_name}",
                        passed=False,
                        ssim_score=0.0,
                        baseline_path=placeholder if not view_a_tab.exists else "",
                        target_path=placeholder if not view_b_tab.exists else "",
                        diff_path=placeholder,
                        label_a=label_a,
                        label_b=label_b,
                        reason=reason,
                    )
                )
                continue

            view_a = map_a.get(view_name_key)
            view_b = map_b.get(view_name_key)
            if not view_a or not view_b:
                continue

            self.logger.info(
                "Comparing workbook view '%s'\n  %s: %s\n  %s: %s",
                view_name,
                label_a,
                view_a.url,
                label_b,
                view_b.url,
            )

            self.bm.navigate_with_retry(page_a, view_a.url, label=f"{label_a}::{view_name}")
            self.bm.navigate_with_retry(page_b, view_b.url, label=f"{label_b}::{view_name}")

            per_view_results = self._compare_loaded_dashboards(
                page_a=page_a,
                page_b=page_b,
                label_a=label_a,
                label_b=label_b,
                threshold=threshold,
                tab_name_prefix=f"{view_name} :: ",
                sequence_entity=f"Page Sequence ({view_name})",
                sequence_slug=f"sequence_mismatch_{_slug(view_name)}",
                filter_scenarios=cfg.filter_scenarios or [],
                enforce_sequence=bool(getattr(cfg, "enforce_page_sequence", True)),
            )
            results.extend(per_view_results)

        return results

    def _discover_workbook_views(self, page, label: str) -> List[WorkbookView]:
        """Extract listed workbook views (name + URL) from a workbook page."""
        self.logger.info(f"Discovering workbook views for {label}...")
        
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        
        time.sleep(2)
        
        # Try to navigate to the Views section
        self.logger.debug(f"[{label}] Checking current page content...")
        try:
            # Wait a bit for React to render
            page.wait_for_timeout(2000)
            # Try scrolling to trigger lazy loading
            page.evaluate("window.scrollBy(0, 500)")
            time.sleep(1)
        except Exception:
            pass
        
        views = self._extract_workbook_view_links(page)

        if not views:
            self.logger.info(f"[{label}] Initial extraction returned no views; trying Views tab click…")
            try:
                page.get_by_text("Views", exact=False).first.click(timeout=3000)
                time.sleep(2)
                views = self._extract_workbook_view_links(page)
            except Exception as e:
                self.logger.debug(f"[{label}] Views tab click failed: {e}")

        if not views:
            self.logger.warning(f"Could not discover workbook views on {label} page")
            return []

        normalized: List[WorkbookView] = []
        for idx, item in enumerate(views):
            name = str(item.get("name", "")).strip() or f"View_{idx + 1}"
            url = str(item.get("url", "")).strip()
            if not url:
                continue
            normalized.append(WorkbookView(name=name, url=url, index=idx))

        self.logger.info(
            f"{label} workbook views: {', '.join(v.name for v in normalized)}"
        )
        return normalized

    def _extract_workbook_view_links(self, page) -> List[dict]:
        """Extract workbook view links using multiple strategies including table scanning."""
        script = """
        () => {
          const out = [];
          const seen = new Set();
          
          // Strategy 1: Standard links with /views/ in href
          let candidates = Array.from(document.querySelectorAll('a[href*="/views/"]'));
          for (const el of candidates) {
            if (el.offsetParent === null) continue;
            const name = (el.textContent || '').trim();
            if (!name || name.length < 2) continue;
            const href = el.getAttribute('href') || el.href;
            if (!href) continue;
            const key = name.toLowerCase();
            if (seen.has(key)) continue;
            seen.add(key);
            out.push({ name, url: href });
          }
          
          if (out.length > 0) return out;
          
          // Strategy 2: Look for items with onclick handlers that might navigate
          candidates = Array.from(document.querySelectorAll('[role="button"], [role="link"], .item, .list-item, [data-test-selector*="view"]'));
          for (const el of candidates) {
            if (el.offsetParent === null) continue;
            const style = window.getComputedStyle(el);
            if (style.visibility === 'hidden' || style.display === 'none') continue;
            
            const name = (el.textContent || '').trim();
            if (!name || name.length < 2) continue;
            
            // Skip generic UI elements
            if (['home', 'favorites', 'recents', 'collections', 'all', 'explore', 'menu', 'nav'].some(x => name.toLowerCase().includes(x))) {
              continue;
            }
            
            let href = null;
            const link = el.querySelector('a');
            if (link && link.href) {
              href = link.href;
            } else if (el.href) {
              href = el.href;
            } else {
              // Try to extract from onclick
              const onclick = el.getAttribute('onclick') || '';
              const match = onclick.match(/(?:navigate|href|url|to)\\(['\"]([^'\"]+)['\"]/i);
              if (match) href = match[1];
            }
            
            if (!href) continue;
            
            const key = name.toLowerCase();
            if (seen.has(key)) continue;
            seen.add(key);
            out.push({ name, url: href });
          }
          
          if (out.length > 0) return out;
          
          // Strategy 3: Scan all visible links/buttons and filter by text patterns
          const allLinks = Array.from(document.querySelectorAll('a, button, div[role="button"]'));
          const filtered = [];
          
          for (const el of allLinks) {
            if (el.offsetParent === null) continue;
            const name = (el.textContent || '').trim();
            
            // Heuristic: view names are typically 2-30 chars, not navigation words
            if (!name || name.length < 2 || name.length > 50) continue;
            if (['home', 'favorites', 'recents', 'collections', 'all', 'explore', 'skip', 'sign', 'help', 'settings'].some(x => name.toLowerCase().includes(x))) {
              continue;
            }
            
            let href = el.href || el.getAttribute('href') || '';
            if (!href && el.getAttribute('onclick')) {
              const match = el.getAttribute('onclick').match(/['\"]([^'\"]+)['\"]/);
              if (match) href = match[1];
            }
            
            if (href) {
              filtered.push({ name, href, el });
            }
          }
          
          // De-duplicate and return
          for (const item of filtered) {
            const key = item.name.toLowerCase();
            if (!seen.has(key)) {
              seen.add(key);
              out.push({ name: item.name, url: item.href });
            }
          }
          
          return out;
        }
        """
        try:
            extracted = page.evaluate(script) or []
            
            if isinstance(extracted, dict) and '_debug' in extracted:
                debug_info = extracted['_debug']
                self.logger.debug(f"_extract_workbook_view_links DEBUG: {debug_info}")
                return []
            
            if extracted:
                self.logger.debug(f"_extract_workbook_view_links found {len(extracted)} views: {[e.get('name') for e in extracted]}")
            else:
                self.logger.debug("_extract_workbook_view_links: no views found with any strategy")
            return extracted
        except Exception as e:
            self.logger.debug(f"_extract_workbook_view_links error: {e}")
            return []

    def _compare_loaded_dashboards(
        self,
        page_a,
        page_b,
        label_a: str,
        label_b: str,
        threshold: float,
        tab_name_prefix: str,
        sequence_entity: str,
        sequence_slug: str,
        filter_scenarios,
        enforce_sequence: bool,
    ) -> List[DiffResult]:
        """Compare already-loaded dashboard pages, including all tabs and optional filter scenarios."""
        results: List[DiffResult] = []

        nav_a = TabNavigator(page_a, self.logger)
        nav_b = TabNavigator(page_b, self.logger)
        tabs_a = nav_a.get_all_tabs()
        tabs_b = nav_b.get_all_tabs()

        pairs = TabNavigator.align_tabs(tabs_a, tabs_b, label_a, label_b)
        self.logger.info(
            f"Tab alignment: {len(pairs)} pair(s) — "
            + f"{sum(1 for a, b in pairs if a.exists and b.exists)} matched, "
            + f"{sum(1 for a, b in pairs if not a.exists or not b.exists)} missing."
        )

        if enforce_sequence:
            sequence_result = self._build_sequence_validation_result(
                tabs_a=tabs_a,
                tabs_b=tabs_b,
                label_a=label_a,
                label_b=label_b,
                entity_name=sequence_entity,
                artifact_slug=sequence_slug,
            )
            if sequence_result:
                results.append(sequence_result)

        scenarios = filter_scenarios or []
        if not scenarios:
            tab_results = self._compare_all_tabs(
                page_a,
                page_b,
                pairs,
                nav_a,
                nav_b,
                label_a,
                label_b,
                threshold,
                scenario_label="",
                tab_name_prefix=tab_name_prefix,
            )
            results.extend(tab_results)
            return results

        for scenario in scenarios:
            self.logger.info(
                f"[bold magenta]Filter scenario:[/] '{scenario.label}' "
                f"({len(scenario.filters)} filter(s))"
            )

            fm_a = FilterManager(page_a, self.logger)
            fm_b = FilterManager(page_b, self.logger)
            render_wait = self.config.browser.render_wait_seconds

            self.logger.info(f"  Applying filters to {label_a}…")
            applied_a = fm_a.apply_scenario(scenario.filters, render_wait)

            self.logger.info(f"  Applying filters to {label_b}…")
            applied_b = fm_b.apply_scenario(scenario.filters, render_wait)

            self.logger.info(
                f"  Filters applied: {applied_a}/{len(scenario.filters)} on {label_a}, "
                f"{applied_b}/{len(scenario.filters)} on {label_b}"
            )

            tab_results = self._compare_all_tabs(
                page_a,
                page_b,
                pairs,
                nav_a,
                nav_b,
                label_a,
                label_b,
                threshold,
                scenario_label=scenario.label,
                tab_name_prefix=tab_name_prefix,
            )
            results.extend(tab_results)

        return results

    @staticmethod
    def _is_workbook_url(url: str) -> bool:
        return "/workbooks/" in str(url).lower()

    def _build_sequence_validation_result(
        self,
        tabs_a: List[TabInfo],
        tabs_b: List[TabInfo],
        label_a: str,
        label_b: str,
        entity_name: str = "Page",
        artifact_slug: str = "sequence_mismatch",
    ) -> DiffResult | None:
        """Return a failing synthetic result when page order differs."""
        names_a = [t.name for t in tabs_a]
        names_b = [t.name for t in tabs_b]
        names_a_l = [n.lower() for n in names_a]
        names_b_l = [n.lower() for n in names_b]

        common = [n for n in names_a_l if n in set(names_b_l)]
        seq_a_common = [names_a[names_a_l.index(n)] for n in common]
        seq_b_common = [names_b[names_b_l.index(n)] for n in common]

        if seq_a_common == seq_b_common:
            return None

        reason = (
            f"{entity_name} mismatch for common entries. "
            f"{label_a}: {seq_a_common} | {label_b}: {seq_b_common}"
        )
        self.logger.warning("%s", reason)

        placeholder = str(self.output.fail_path(artifact_slug))
        create_missing_tab_image(entity_name, reason, placeholder)

        return DiffResult(
            tab_name=entity_name,
            passed=False,
            ssim_score=0.0,
            baseline_path=placeholder,
            target_path=placeholder,
            diff_path=placeholder,
            label_a=label_a,
            label_b=label_b,
            reason=reason,
        )

    @staticmethod
    def _normalized_name_set(names: List[str]) -> Set[str]:
        return {str(name).strip().lower() for name in names if str(name).strip()}

    # ------------------------------------------------------------------

    def _compare_all_tabs(
        self,
        page_a, page_b,
        pairs, nav_a, nav_b,
        label_a, label_b,
        threshold,
        scenario_label: str = "",
        tab_name_prefix: str = "",
    ) -> List[DiffResult]:
        """Compare every tab pair and return results."""
        results: List[DiffResult] = []
        for tab_a, tab_b in pairs:
            result = self._compare_tab_pair(
                page_a, page_b,
                tab_a, tab_b,
                nav_a, nav_b,
                label_a, label_b,
                threshold,
                scenario_label=scenario_label,
                tab_name_prefix=tab_name_prefix,
            )
            results.append(result)
        return results

    # ------------------------------------------------------------------

    def _compare_tab_pair(
        self,
        page_a, page_b,
        tab_a: TabInfo, tab_b: TabInfo,
        nav_a: TabNavigator, nav_b: TabNavigator,
        label_a: str, label_b: str,
        threshold: float,
        scenario_label: str = "",
        tab_name_prefix: str = "",
    ) -> DiffResult:

        tab_name = tab_a.name if tab_a.exists else tab_b.name
        report_tab_name = f"{tab_name_prefix}{tab_name}" if tab_name_prefix else tab_name
        display_name = f"{report_tab_name} [{scenario_label}]" if scenario_label else report_tab_name

        # ---- Handle missing tab ----------------------------------------
        if not tab_a.exists or not tab_b.exists:
            reason = tab_a.reason if not tab_a.exists else tab_b.reason
            tab_name_key = tab_name.strip().lower()
            if tab_name_key in self._deprecated_page_hints:
                reason = f"Deprecated page (configured hint): {reason}"
            else:
                reason = f"Possible deprecated page (auto-detected): {reason}"
            self.logger.warning(
                f"  [yellow]MISSING TAB[/] '{tab_name}': {reason}"
            )
            placeholder = str(self.output.fail_path(f"missing_{_slug(display_name)}"))
            create_missing_tab_image(report_tab_name, reason, placeholder)
            return DiffResult(
                tab_name=report_tab_name,
                passed=False,
                ssim_score=0.0,
                baseline_path=placeholder if not tab_a.exists else "",
                target_path=placeholder if not tab_b.exists else "",
                diff_path=placeholder,
                label_a=label_a,
                label_b=label_b,
                scenario_label=scenario_label,
                reason=reason,
            )

        self.logger.info(f"  Comparing tab: [cyan]'{display_name}'[/]")

        # ---- Navigate both pages to their respective tab ---------------
        if tab_a.index > 0:
            nav_a.navigate_to_tab(tab_a, render_wait=self.config.browser.render_wait_seconds)
        if tab_b.index > 0:
            nav_b.navigate_to_tab(tab_b, render_wait=self.config.browser.render_wait_seconds)

        # ---- Screenshot both pages -------------------------------------
        slug = _slug(display_name)
        ss_a_path = str(self.output.pass_path(f"{label_a}_{slug}"))
        ss_b_path = str(self.output.pass_path(f"{label_b}_{slug}"))

        try:
            page_a.screenshot(path=ss_a_path, full_page=True)
            self.logger.debug(f"  Screenshot saved: {ss_a_path}")
        except Exception as e:
            self.logger.error(f"  Screenshot failed for {label_a}/'{tab_name}': {e}")
            return DiffResult(
                tab_name=report_tab_name, passed=False, ssim_score=0.0,
                baseline_path="", target_path="", diff_path="",
                label_a=label_a, label_b=label_b,
                scenario_label=scenario_label,
            )

        try:
            page_b.screenshot(path=ss_b_path, full_page=True)
            self.logger.debug(f"  Screenshot saved: {ss_b_path}")
        except Exception as e:
            self.logger.error(f"  Screenshot failed for {label_b}/'{tab_name}': {e}")
            return DiffResult(
                tab_name=report_tab_name, passed=False, ssim_score=0.0,
                baseline_path=ss_a_path, target_path="", diff_path="",
                label_a=label_a, label_b=label_b,
                scenario_label=scenario_label,
            )

        # ---- Visual diff -----------------------------------------------
        diff_p = str(self.output.diff_path(slug))
        result = compare_images(
            baseline_path=ss_a_path,
            target_path=ss_b_path,
            diff_output_path=diff_p,
            threshold=threshold,
            tab_name=report_tab_name,
            label_a=label_a,
            label_b=label_b,
        )
        result.scenario_label = scenario_label

        # Move individual screenshots to pass/ or fail/ bucket
        if result.passed:
            self.logger.info(
                f"  [green]PASS[/] '{tab_name}' — SSIM: {result.ssim_score:.4f}"
            )
        else:
            # Rename screenshots from pass/ to fail/
            ss_a_fail = str(self.output.fail_path(f"{label_a}_{slug}"))
            ss_b_fail = str(self.output.fail_path(f"{label_b}_{slug}"))
            _safe_rename(ss_a_path, ss_a_fail)
            _safe_rename(ss_b_path, ss_b_fail)
            result.baseline_path = ss_a_fail
            result.target_path   = ss_b_fail
            self.logger.warning(
                f"  [red]FAIL[/] '{tab_name}' — SSIM: {result.ssim_score:.4f} "
                f"(threshold: {threshold}) | Diff pixels: {result.diff_pixel_count}"
            )

        return result

    # ------------------------------------------------------------------

    def _log_summary(self, results: List[DiffResult]):
        passed = sum(1 for r in results if r.passed)
        total  = len(results)
        self.logger.info(
            f"[bold]REGRESSION / COMPARISON TESTING Summary:[/] {passed}/{total} tabs passed."
        )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _slug(name: str) -> str:
    return re.sub(r"[^\w]+", "_", name).strip("_").lower()[:40]


def _safe_rename(src: str, dst: str):
    try:
        Path(src).rename(dst)
    except Exception:
        pass
