"""
performance_reporter.py — Generates HTML report + CSV for performance test results.

Outputs:
  • Self-contained HTML report (dark-themed, matching existing report style)
  • Single CSV file with all iteration data (collated)
"""
from __future__ import annotations

import base64
import csv
from datetime import datetime
from pathlib import Path
from typing import List

from jinja2 import Template

from bi_regression.config_parser import TestConfig
from bi_regression.performance_tester import PerfDashboardResult


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

_PERF_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Performance Test Report — {{ run_date }}</title>
  <style>
    :root {
      --bg:        #0f1117;
      --surface:   #1a1d27;
      --card:      #22253a;
      --border:    #2e3150;
      --accent:    #5b6af0;
      --pass:      #22c55e;
      --fail:      #ef4444;
      --warn:      #f59e0b;
      --text:      #e2e8f0;
      --muted:     #94a3b8;
      --radius:    12px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; }

    .header {
      background: linear-gradient(135deg, #1e2240 0%, #0f1117 100%);
      border-bottom: 1px solid var(--border);
      padding: 32px 40px;
    }
    .header h1 { font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }
    .header h1 span { color: var(--accent); }
    .header .type-badge {
      display: inline-block; margin-left: 16px;
      font-size: 12px; font-weight: 700; padding: 4px 14px;
      border-radius: 20px; text-transform: uppercase; letter-spacing: 1.5px;
      background: rgba(91,106,240,0.2); color: var(--accent); border: 1px solid var(--accent);
      vertical-align: middle;
    }
    .meta { color: var(--muted); font-size: 13px; margin-top: 6px; }

    .summary { display: flex; gap: 16px; padding: 24px 40px; flex-wrap: wrap; }
    .stat-card {
      background: var(--card); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 20px 28px; min-width: 150px; flex: 1;
    }
    .stat-card .label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); }
    .stat-card .value { font-size: 36px; font-weight: 700; margin-top: 6px; }
    .stat-card.pass .value { color: var(--pass); }
    .stat-card.fail .value { color: var(--fail); }
    .stat-card.total .value { color: var(--accent); }

    .section { padding: 0 40px 40px; }
    .section h2 { font-size: 18px; font-weight: 600; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }

    .results { display: flex; flex-direction: column; gap: 24px; }

    .result-card {
      background: var(--card); border: 1px solid var(--border);
      border-radius: var(--radius); overflow: hidden;
    }
    .result-card.pass { border-left: 4px solid var(--pass); }
    .result-card.fail { border-left: 4px solid var(--fail); }

    .card-header {
      display: flex; align-items: center; gap: 16px;
      padding: 16px 20px; cursor: pointer; user-select: none;
    }
    .card-header:hover { background: rgba(255,255,255,0.03); }
    .badge {
      font-size: 11px; font-weight: 700; padding: 3px 10px;
      border-radius: 20px; text-transform: uppercase; letter-spacing: 1px;
    }
    .badge.pass { background: rgba(34,197,94,0.15); color: var(--pass); border: 1px solid var(--pass); }
    .badge.fail { background: rgba(239,68,68,0.15); color: var(--fail); border: 1px solid var(--fail); }
    .dash-name { font-size: 15px; font-weight: 600; flex: 1; }
    .dash-url { font-size: 12px; color: var(--muted); max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .arrow { color: var(--muted); font-size: 18px; transition: transform 0.2s; }
    .card-header.open .arrow { transform: rotate(90deg); }

    .card-body { display: none; padding: 0 20px 20px; }
    .card-body.open { display: block; }

    /* Metrics grid */
    .metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
    .metric-box {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 8px; padding: 16px;
    }
    .metric-box h4 {
      font-size: 13px; font-weight: 600; margin-bottom: 12px;
      display: flex; align-items: center; gap: 8px;
    }
    .metric-box h4 .metric-badge {
      font-size: 10px; font-weight: 700; padding: 2px 8px;
      border-radius: 10px; text-transform: uppercase;
    }
    .metric-badge.pass { background: rgba(34,197,94,0.15); color: var(--pass); }
    .metric-badge.fail { background: rgba(239,68,68,0.15); color: var(--fail); }

    .metric-stats { display: flex; gap: 20px; flex-wrap: wrap; }
    .metric-stat { text-align: center; }
    .metric-stat .ms-label { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); }
    .metric-stat .ms-value { font-size: 22px; font-weight: 700; margin-top: 2px; }
    .metric-stat .ms-value.pass-color { color: var(--pass); }
    .metric-stat .ms-value.fail-color { color: var(--fail); }
    .metric-stat .ms-value.accent-color { color: var(--accent); }

    .threshold-line { margin-top: 10px; font-size: 12px; color: var(--muted); }
    .threshold-line strong { color: var(--text); }

    /* Iteration table */
    .iter-table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }
    .iter-table th {
      text-align: left; padding: 8px 12px;
      background: rgba(255,255,255,0.05);
      color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
    }
    .iter-table td { padding: 8px 12px; border-top: 1px solid var(--border); }
    .iter-table tr:hover td { background: rgba(255,255,255,0.02); }
    .iter-table .ms { font-family: monospace; font-weight: 600; }

    /* Per-chart table */
    .chart-table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }
    .chart-table th {
      text-align: left; padding: 8px 12px;
      background: rgba(255,255,255,0.05);
      color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
    }
    .chart-table td { padding: 8px 12px; border-top: 1px solid var(--border); }
    .chart-table tr:hover td { background: rgba(255,255,255,0.02); }
    .chart-table .ms { font-family: monospace; font-weight: 600; }
    .cold-color { color: #60a5fa; }
    .warm-color { color: var(--warn); }
    .metric-badge.cold { background: rgba(96,165,250,0.15); color: #60a5fa; }
    .metric-badge.warm { background: rgba(245,158,11,0.15); color: var(--warn); }

    .max-banner {
      margin-top: 16px; padding: 12px 16px; border-radius: 8px;
      background: rgba(91,106,240,0.12); border: 1px solid var(--accent);
      font-size: 13px; color: var(--text);
    }
    .max-banner strong { color: var(--accent); font-size: 16px; }

    /* Screenshot */
    .screenshot-section { margin-top: 20px; }
    .screenshot-section .ss-label {
      font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
      color: var(--muted); margin-bottom: 8px;
    }
    .screenshot-section img {
      width: 100%; border-radius: 8px; border: 1px solid var(--border); cursor: pointer;
    }
    .screenshot-section img:hover { border-color: var(--accent); }

    /* Bar chart */
    .bar-chart { display: flex; align-items: flex-end; gap: 6px; height: 120px; margin-top: 16px; padding: 0 4px; }
    .bar-group { display: flex; flex-direction: column; align-items: center; flex: 1; gap: 4px; }
    .bar {
      width: 100%; min-width: 20px; border-radius: 4px 4px 0 0;
      transition: height 0.3s;
    }
    .bar.render { background: var(--accent); }
    .bar.interaction { background: var(--warn); }
    .bar-label { font-size: 10px; color: var(--muted); }
    .bar-chart-legend { display: flex; gap: 16px; margin-top: 8px; font-size: 11px; color: var(--muted); }
    .bar-chart-legend .dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; margin-right: 4px; }

    /* Lightbox */
    .lightbox { display:none; position:fixed; z-index:1000; top:0; left:0; width:100vw; height:100vh;
      background:rgba(0,0,0,0.92); justify-content:center; align-items:center; cursor:zoom-out; }
    .lightbox.show { display:flex; }
    .lightbox img { max-width:95vw; max-height:95vh; border-radius:8px; }

    .footer { text-align: center; color: var(--muted); font-size: 12px; padding: 24px; border-top: 1px solid var(--border); margin-top: 20px; }
  </style>
</head>
<body>

<div class="header">
  <h1>Tableau <span>Performance Test</span> Report <span class="type-badge">PERFORMANCE TESTING</span></h1>
  <p class="meta">
    Run Date: {{ run_date }}
    &nbsp;|&nbsp; Iterations per dashboard: <strong>{{ iterations }}</strong>
    &nbsp;|&nbsp; Output: {{ run_dir }}
  </p>
</div>

<div class="summary">
  <div class="stat-card total">
    <div class="label">Dashboards Tested</div>
    <div class="value">{{ total }}</div>
  </div>
  <div class="stat-card pass">
    <div class="label">Passed</div>
    <div class="value">{{ passed }}</div>
  </div>
  <div class="stat-card fail">
    <div class="label">Failed</div>
    <div class="value">{{ failed }}</div>
  </div>
  <div class="stat-card total">
    <div class="label">Charts Measured</div>
    <div class="value">{{ total_charts }}</div>
  </div>
  <div class="stat-card total">
    <div class="label">Max Load Time</div>
    <div class="value">{{ "%.0f"|format(overall_max_ms) }}<small style="font-size:16px;">ms</small></div>
  </div>
</div>

<div class="section">
  <h2>Dashboard Results</h2>
  <div class="results">
    {% for r in results %}
    <div class="result-card {{ 'pass' if r.passed else 'fail' }}">
      <div class="card-header" onclick="toggle(this)">
        <span class="badge {{ 'pass' if r.passed else 'fail' }}">{{ 'PASS' if r.passed else 'FAIL' }}</span>
        <span class="dash-name">{{ r.label }}</span>
        <span class="dash-url" title="{{ r.url }}">{{ r.url }}</span>
        <span class="arrow">▶</span>
      </div>
      <div class="card-body">

        <div class="max-banner">
          Maximum time observed: <strong>{{ "%.0f"|format(r.max_time_ms) }} ms</strong>
          &nbsp;·&nbsp; {{ r.chart_count }} chart(s) measured
        </div>

        <!-- Cold vs Warm full-dashboard load -->
        <div class="metrics-grid">
          <div class="metric-box">
            <h4>Cold Load — Uncached
              <span class="metric-badge {{ 'pass' if r.cold_passed else 'fail' }}">
                {{ 'PASS' if r.cold_passed else 'FAIL' }}
              </span>
            </h4>
            <div class="metric-stats">
              <div class="metric-stat">
                <div class="ms-label">Min</div>
                <div class="ms-value accent-color">{{ "%.0f"|format(r.cold_full_min) }}<small>ms</small></div>
              </div>
              <div class="metric-stat">
                <div class="ms-label">Avg</div>
                <div class="ms-value {{ 'pass-color' if r.cold_passed else 'fail-color' }}">{{ "%.0f"|format(r.cold_full_avg) }}<small>ms</small></div>
              </div>
              <div class="metric-stat">
                <div class="ms-label">Max</div>
                <div class="ms-value accent-color">{{ "%.0f"|format(r.cold_full_max) }}<small>ms</small></div>
              </div>
            </div>
            <div class="threshold-line">Threshold: <strong>{{ "%.0f"|format(r.cold_threshold) }} ms</strong> (full dashboard, cache cleared)</div>
          </div>

          <div class="metric-box">
            <h4>Warm Load — Cached
              <span class="metric-badge warm">CACHED</span>
            </h4>
            <div class="metric-stats">
              <div class="metric-stat">
                <div class="ms-label">Min</div>
                <div class="ms-value warm-color">{{ "%.0f"|format(r.warm_full_min) }}<small>ms</small></div>
              </div>
              <div class="metric-stat">
                <div class="ms-label">Avg</div>
                <div class="ms-value warm-color">{{ "%.0f"|format(r.warm_full_avg) }}<small>ms</small></div>
              </div>
              <div class="metric-stat">
                <div class="ms-label">Max</div>
                <div class="ms-value warm-color">{{ "%.0f"|format(r.warm_full_max) }}<small>ms</small></div>
              </div>
            </div>
            <div class="threshold-line">Best-case timing with browser cache populated</div>
          </div>
        </div>

        <!-- Filter refresh -->
        {% if r.has_filter %}
        <div class="metric-box" style="margin-top:16px;">
          <h4>Filter Refresh — {{ r.filter_name }}
            <span class="metric-badge {{ 'pass' if r.filter_passed else 'fail' }}">
              {{ 'PASS' if r.filter_passed else 'FAIL' }}
            </span>
          </h4>
          <div class="metric-stats">
            <div class="metric-stat">
              <div class="ms-label">Min</div>
              <div class="ms-value accent-color">{{ "%.0f"|format(r.filter_min) }}<small>ms</small></div>
            </div>
            <div class="metric-stat">
              <div class="ms-label">Avg</div>
              <div class="ms-value {{ 'pass-color' if r.filter_passed else 'fail-color' }}">{{ "%.0f"|format(r.filter_avg) }}<small>ms</small></div>
            </div>
            <div class="metric-stat">
              <div class="ms-label">Max</div>
              <div class="ms-value accent-color">{{ "%.0f"|format(r.filter_max) }}<small>ms</small></div>
            </div>
          </div>
          <div class="threshold-line">Threshold: <strong>{{ "%.0f"|format(r.filter_threshold) }} ms</strong> (time to re-render after filter change)</div>
        </div>
        {% endif %}

        <!-- Per-chart load times -->
        {% if r.chart_stats %}
        <h4 style="margin-top:20px; font-size:13px; color:var(--muted);">Per-Chart Load Times</h4>
        <table class="chart-table">
          <thead>
            <tr>
              <th>Chart / Worksheet</th>
              <th>Cold Avg (ms)</th>
              <th>Warm Avg (ms)</th>
              <th>Max (ms)</th>
            </tr>
          </thead>
          <tbody>
            {% for c in r.chart_stats %}
            <tr>
              <td>{{ c.name }}</td>
              <td class="ms cold-color">{{ "%.0f"|format(c.cold_avg_ms) }}</td>
              <td class="ms warm-color">{{ "%.0f"|format(c.warm_avg_ms) }}</td>
              <td class="ms">{{ "%.0f"|format(c.max_ms) }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
        {% endif %}

        <!-- Full-dashboard load per iteration -->
        <h4 style="margin-top:20px; font-size:13px; color:var(--muted);">Full-Dashboard Load per Iteration</h4>
        <table class="iter-table">
          <thead>
            <tr>
              <th>Iteration</th>
              <th>Mode</th>
              <th>Full Load (ms)</th>
              <th>Charts</th>
            </tr>
          </thead>
          <tbody>
            {% for lp in r.loads %}
            <tr>
              <td>{{ lp.iteration }}</td>
              <td>{{ lp.mode|upper }}</td>
              <td class="ms">{{ "%.0f"|format(lp.full_load_ms) }}</td>
              <td>{{ lp.chart_count }}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>

        {% if r.screenshot_b64 %}
        <div class="screenshot-section">
          <div class="ss-label">Dashboard Screenshot (first render)</div>
          <img src="data:image/png;base64,{{ r.screenshot_b64 }}" alt="Dashboard screenshot" onclick="openLightbox(this)"/>
        </div>
        {% endif %}

      </div>
    </div>
    {% endfor %}
  </div>
</div>

<div class="footer">
  Generated by <strong>Tableau Dashboard Testing Framework</strong> — Performance Testing &nbsp;|&nbsp; {{ run_date }}
</div>

<div class="lightbox" id="lightbox" onclick="closeLightbox()">
  <img id="lightbox-img" src="" alt="Full size"/>
</div>

<script>
function toggle(header) {
  header.classList.toggle('open');
  header.nextElementSibling.classList.toggle('open');
}
function openLightbox(img) {
  event.stopPropagation();
  document.getElementById('lightbox-img').src = img.src;
  document.getElementById('lightbox').classList.add('show');
}
function closeLightbox() {
  document.getElementById('lightbox').classList.remove('show');
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });
document.querySelectorAll('.result-card.fail .card-header').forEach(h => {
  h.classList.add('open');
  h.nextElementSibling.classList.add('open');
});
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# PerformanceReporter
# ---------------------------------------------------------------------------

class PerformanceReporter:
    def __init__(
        self,
        run_dir: Path,
        config: TestConfig,
        results: List[PerfDashboardResult],
    ):
        self.run_dir = run_dir
        self.config = config
        self.results = results

    def generate(self) -> Path:
        """Generate both the HTML report and CSV file. Returns the HTML path."""
        html_path = self._generate_html()
        csv_path = self._generate_csv()
        self._print_terminal_report(html_path, csv_path)
        return html_path

    # ------------------------------------------------------------------

    def _print_terminal_report(self, html_path: Path, csv_path: Path) -> None:
        """Print a readable performance summary to the terminal."""
        results = self.results
        total = len(results)
        passed = sum(1 for r in results if r.passed)

        out = []
        out.append("")
        out.append("=" * 92)
        out.append("  TABLEAU DASHBOARD PERFORMANCE REPORT")
        out.append("=" * 92)
        out.append(
            f"  Run: {datetime.now():%Y-%m-%d %H:%M:%S}   "
            f"Sheets: {total}   Iterations: {self.config.performance.iterations}   "
            f"Passed: {passed}/{total}"
        )
        out.append(f"  Output folder : {self.run_dir}")
        out.append(f"  HTML report   : {html_path}")
        out.append(f"  CSV file      : {csv_path}")
        out.append("-" * 92)
        out.append(
            f"  {'Sheet':<34}{'Charts':>6}{'ColdAvg':>10}{'ColdMax':>10}"
            f"{'WarmAvg':>10}{'Max':>10}  Result   (ms)"
        )
        out.append("-" * 92)
        for r in results:
            name = r.label.split("›")[-1].strip() if "›" in r.label else r.label
            res = "PASS" if r.passed else "FAIL"
            out.append(
                f"  {name[:33]:<34}{r.chart_count:>6}{r.cold_full_avg:>10.0f}"
                f"{r.cold_full_max:>10.0f}{r.warm_full_avg:>10.0f}{r.max_time_ms:>10.0f}  {res}"
            )
            for cs in r.chart_stats:
                out.append(
                    f"      • {cs.name[:44]:<44} cold {cs.cold_avg_ms:>7.0f}  "
                    f"warm {cs.warm_avg_ms:>7.0f}  max {cs.max_ms:>7.0f}"
                )
            if r.has_filter:
                out.append(
                    f"      ⟳ filter '{r.filter_name}': avg {r.filter_avg:.0f}ms "
                    f"(threshold {r.filter_threshold:.0f}ms) → "
                    f"{'PASS' if r.filter_passed else 'FAIL'}"
                )
        out.append("=" * 92)
        print("\n".join(out))

    # ------------------------------------------------------------------

    def _generate_html(self) -> Path:
        rows = []
        total_charts = 0
        overall_max = 0.0
        for r in self.results:
            total_charts += r.chart_count
            overall_max = max(overall_max, r.max_time_ms)

            loads = [
                {
                    "mode": lp.mode,
                    "iteration": lp.iteration,
                    "full_load_ms": lp.full_load_ms,
                    "chart_count": lp.chart_count,
                }
                for lp in r.loads
            ]
            chart_stats = [
                {
                    "name": cs.name,
                    "cold_avg_ms": cs.cold_avg_ms,
                    "warm_avg_ms": cs.warm_avg_ms,
                    "max_ms": cs.max_ms,
                }
                for cs in r.chart_stats
            ]

            rows.append({
                "label": r.label,
                "url": r.url,
                "passed": r.passed,
                "cold_full_min": r.cold_full_min,
                "cold_full_max": r.cold_full_max,
                "cold_full_avg": r.cold_full_avg,
                "warm_full_min": r.warm_full_min,
                "warm_full_max": r.warm_full_max,
                "warm_full_avg": r.warm_full_avg,
                "cold_threshold": r.cold_threshold,
                "cold_passed": r.cold_passed,
                "has_filter": r.has_filter,
                "filter_name": r.filter_name,
                "filter_min": r.filter_min,
                "filter_max": r.filter_max,
                "filter_avg": r.filter_avg,
                "filter_threshold": r.filter_threshold,
                "filter_passed": r.filter_passed,
                "chart_count": r.chart_count,
                "max_time_ms": r.max_time_ms,
                "chart_stats": chart_stats,
                "loads": loads,
                "screenshot_b64": _img_b64(r.screenshot_path),
            })

        passed = sum(1 for r in rows if r["passed"])
        data = {
            "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "run_dir": str(self.run_dir),
            "iterations": self.config.performance.iterations,
            "total": len(rows),
            "passed": passed,
            "failed": len(rows) - passed,
            "total_charts": total_charts,
            "overall_max_ms": overall_max,
            "results": rows,
        }

        html = Template(_PERF_TEMPLATE).render(**data)
        out = self.run_dir / "report.html"
        out.write_text(html, encoding="utf-8")
        return out

    # ------------------------------------------------------------------

    def _generate_csv(self) -> Path:
        """Write a long-format CSV with full-load, per-chart and filter rows."""
        out = self.run_dir / "performance_results.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "dashboard_label",
                "dashboard_url",
                "iteration",
                "load_mode",
                "metric_type",
                "chart_name",
                "value_ms",
                "threshold_ms",
                "pass",
            ])
            for r in self.results:
                for lp in r.loads:
                    is_cold = lp.mode == "cold"
                    writer.writerow([
                        r.label,
                        r.url,
                        lp.iteration,
                        lp.mode,
                        "full_dashboard_load",
                        "",
                        f"{lp.full_load_ms:.0f}",
                        f"{r.cold_threshold:.0f}" if is_cold else "",
                        (lp.full_load_ms <= r.cold_threshold) if is_cold else "",
                    ])
                    for c in lp.charts:
                        writer.writerow([
                            r.label,
                            r.url,
                            lp.iteration,
                            lp.mode,
                            "chart_load",
                            c.name,
                            f"{c.load_ms:.0f}",
                            "",
                            "" if c.rendered else "NOT_RENDERED",
                        ])
                for fr in r.filter_refreshes:
                    writer.writerow([
                        r.label,
                        r.url,
                        fr.iteration,
                        "warm",
                        "filter_refresh",
                        fr.label,
                        f"{fr.refresh_ms:.0f}",
                        f"{r.filter_threshold:.0f}",
                        fr.refresh_ms <= r.filter_threshold,
                    ])
        return out


# ---------------------------------------------------------------------------

def _img_b64(path: str) -> str:
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None
