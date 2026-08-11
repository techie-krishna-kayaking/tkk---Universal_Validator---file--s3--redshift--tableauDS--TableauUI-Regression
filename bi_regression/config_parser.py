"""
config_parser.py — Load and validate the YAML config using Pydantic v2 models.

Design decisions:
  - test_type is OPTIONAL — auto-detected from which section is present
  - browser is OPTIONAL — defaults to a dedicated automation Edge profile
  This allows minimal config files like test.yaml that only define the test section.
"""
import os

import yaml
from pydantic import BaseModel, field_validator, model_validator
from typing import List, Optional, Union


class UIStandards(BaseModel):
    fonts_allowed: List[str]
    font_sizes_allowed: List[str]
    colors_allowed: List[str]

    @field_validator("colors_allowed", mode="before")
    @classmethod
    def normalise_colors(cls, v):
        """Ensure all hex colors are uppercase."""
        return [c.upper() if c.startswith("#") else c for c in v]


class SmokeConfig(BaseModel):
    dashboard_url: str
    ui_standards: UIStandards


class FilterSetting(BaseModel):
    name: str               # Filter label as shown on the dashboard
    value: str              # Value to select / enter
    type: str = "dropdown"  # "dropdown" | "input" (covers date & text inputs)


class FilterScenario(BaseModel):
    label: str                      # Human-readable name, e.g. "Americas Q1"
    filters: List[FilterSetting]


class ComparisonConfig(BaseModel):
    dashboard_url_1: str
    dashboard_url_2: str
    label_1: str = "Dashboard 1"
    label_2: str = "Dashboard 2"
    ssim_threshold: float = 0.98
    include_all_pages: bool = True
    enforce_page_sequence: bool = True
    deprecated_pages: Optional[List[str]] = None
    filter_scenarios: Optional[List[FilterScenario]] = None


class PerformanceInteraction(BaseModel):
    type: str = "filter"                       # "filter" | "tab_switch"
    filter_name: Optional[str] = None
    filter_value: Optional[str] = None
    tab_index: Optional[int] = None            # for tab_switch


class PerformanceThresholds(BaseModel):
    first_render_ms: float = 15000             # max acceptable first-render time
    interaction_ms: float = 8000               # max acceptable interaction time


class PerformanceDashboard(BaseModel):
    url: str
    label: str = "Dashboard"
    test_all_views: bool = False           # discover & test every view in the workbook
    interaction: Optional[PerformanceInteraction] = None
    thresholds: PerformanceThresholds = PerformanceThresholds()


class PerformanceConfig(BaseModel):
    dashboards: List[PerformanceDashboard]
    iterations: int = 3


class BrowserConfig(BaseModel):
    # Dedicated automation profile — Playwright cannot attach to the managed
    # default Edge profile, so we keep a separate profile that persists the
    # Okta/Tableau session across runs (log in once, reused afterwards).
    user_data_dir: str = os.path.expanduser("~/.tableau_perf_edge_profile")
    profile_dir: str = "Default"
    headless: bool = False
    page_load_timeout: int = 90000
    render_wait_seconds: int = 6
    max_retries: int = 3
    viewport_width: int = 1920
    viewport_height: int = 1080


class OutputConfig(BaseModel):
    # Default: bi_regression/results (next to this package), independent of cwd
    base_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


class TestConfig(BaseModel):
    # Optional in YAML — auto-detected from which section exists
    test_type: Optional[str] = None
    browser: BrowserConfig = BrowserConfig()
    smoke: Optional[SmokeConfig] = None
    comparison: Optional[Union[ComparisonConfig, List[ComparisonConfig]]] = None
    performance: Optional[PerformanceConfig] = None
    output: OutputConfig = OutputConfig()

    @model_validator(mode="after")
    def auto_detect_and_validate(self) -> "TestConfig":
        # Auto-detect test_type if not specified
        if self.test_type is None:
            present = []
            if self.comparison is not None:
                present.append("comparison")
            if self.smoke is not None:
                present.append("smoke")
            if self.performance is not None:
                present.append("performance")

            if len(present) == 1:
                self.test_type = present[0]
            else:
                raise ValueError(
                    "Cannot auto-detect test_type. "
                    "Please add 'test_type: smoke', 'test_type: comparison', or "
                    "'test_type: performance' to your config, "
                    "or ensure only one test section is present."
                )

        # Validate required section exists for the chosen mode
        allowed = {"smoke", "comparison", "performance"}
        if self.test_type not in allowed:
            raise ValueError(f"test_type must be one of {allowed}, got '{self.test_type}'")

        if self.test_type == "smoke" and self.smoke is None:
            raise ValueError("test_type is 'smoke' but [smoke] section is missing in config.")
        if self.test_type == "comparison" and self.comparison is None:
            raise ValueError("test_type is 'comparison' but [comparison] section is missing in config.")
        if self.test_type == "performance" and self.performance is None:
            raise ValueError("test_type is 'performance' but [performance] section is missing in config.")

        return self


def load_config(file_path: str) -> TestConfig:
    """Parse YAML config file and return validated TestConfig."""
    with open(file_path, "r") as f:
        data = yaml.safe_load(f)
    return TestConfig(**data)
