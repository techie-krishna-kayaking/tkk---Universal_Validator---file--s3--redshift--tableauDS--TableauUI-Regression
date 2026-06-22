"""
Great Expectations Integration for Rule-Based Data Quality Validation

This module provides a pluggable rule-based validation engine that runs
Great Expectations on pandas DataFrames. Results are normalized into the
framework's standard validation result format for seamless integration with
CSV, HTML, and Excel reporting.

Design:
- Accepts a DataFrame and YAML-defined expectations
- Executes validations against specified columns
- Returns normalized result dicts compatible with core/reporter.py
- Supports running on source, target, or both datasets
- Integrates with the existing Comparator result schema

Result Schema (compatible with existing framework):
{
    "validation": "great_expectations",
    "result": "PASS|FAIL|SKIP|ERROR",
    "column": "column_name",  # empty for dataset-level expectations
    "pk": "",  # not applicable for GX
    "detail": "Expectation result summary",
    "source_value": "expectation_type",
    "target_value": "status|detailed_result"
}
"""

from typing import List, Dict, Any, Optional, Union
import pandas as pd
import logging


class GXValidator:
    """
    Great Expectations validator that runs rule-based checks on DataFrames.
    
    Usage:
        gx_val = GXValidator(df, expectations_config, logger=logger)
        results = gx_val.validate()  # Returns list of normalized result dicts
    """
    
    def __init__(
        self,
        dataframe: pd.DataFrame,
        expectations: List[Dict[str, Any]],
        dataframe_label: str = "data",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the GX validator.
        
        Args:
            dataframe: pandas DataFrame to validate
            expectations: List of expectation dicts from YAML config
            dataframe_label: Label for this dataset (e.g., "source", "target")
            logger: Optional logger instance
        """
        self.df = dataframe
        self.expectations = expectations or []
        self.label = dataframe_label
        self.logger = logger or logging.getLogger(__name__)
        self.results: List[Dict[str, Any]] = []
    
    def validate(self) -> List[Dict[str, Any]]:
        """
        Run all configured expectations and return normalized results.
        
        Returns:
            List of result dicts in framework standard format
        """
        if not self.expectations:
            self.logger.debug(f"No Great Expectations rules configured for {self.label}")
            return []
        
        self.logger.info(f"Running {len(self.expectations)} Great Expectations on {self.label}")
        
        for expectation in self.expectations:
            try:
                result = self._run_expectation(expectation)
                if result:
                    self.results.append(result)
            except Exception as e:
                self.logger.error(f"Error running expectation {expectation.get('type', 'unknown')}: {e}")
                self.results.append(self._error_result(expectation, str(e)))
        
        return self.results
    
    def _run_expectation(self, expectation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a single expectation and return a normalized result.
        
        Args:
            expectation: Dict with 'type' and type-specific parameters
        
        Returns:
            Normalized result dict or None
        """
        exp_type = expectation.get("type", "").lower()
        
        if exp_type == "expect_column_values_to_not_be_null":
            return self._expect_column_values_to_not_be_null(expectation)
        elif exp_type == "expect_column_values_to_be_unique":
            return self._expect_column_values_to_be_unique(expectation)
        elif exp_type == "expect_column_values_to_be_between":
            return self._expect_column_values_to_be_between(expectation)
        elif exp_type == "expect_column_values_to_match_regex":
            return self._expect_column_values_to_match_regex(expectation)
        elif exp_type == "expect_column_values_to_be_in_set":
            return self._expect_column_values_to_be_in_set(expectation)
        elif exp_type == "expect_column_to_exist":
            return self._expect_column_to_exist(expectation)
        elif exp_type == "expect_table_row_count_to_be_between":
            return self._expect_table_row_count_to_be_between(expectation)
        elif exp_type == "expect_column_values_to_be_of_type":
            return self._expect_column_values_to_be_of_type(expectation)
        else:
            self.logger.warning(f"Unsupported expectation type: {exp_type}")
            return None
    
    def _expect_column_values_to_not_be_null(self, exp: Dict) -> Dict[str, Any]:
        """Check that column has no NULL values."""
        column = exp.get("column")
        if not column:
            return self._error_result(exp, "Missing 'column' parameter")
        
        if column not in self.df.columns:
            return self._fail_result(
                exp, column, f"Column '{column}' does not exist"
            )
        
        null_count = self.df[column].isna().sum()
        passed = null_count == 0
        
        return {
            "validation": "great_expectations",
            "result": "PASS" if passed else "FAIL",
            "column": column,
            "pk": "",
            "detail": f"Column '{column}': {null_count} NULL value(s) found" if null_count > 0 else f"Column '{column}': No NULLs (✓)",
            "source_value": exp.get("type"),
            "target_value": f"NULL_count={null_count}"
        }
    
    def _expect_column_values_to_be_unique(self, exp: Dict) -> Dict[str, Any]:
        """Check that column values are unique (no duplicates)."""
        column = exp.get("column")
        if not column:
            return self._error_result(exp, "Missing 'column' parameter")
        
        if column not in self.df.columns:
            return self._fail_result(
                exp, column, f"Column '{column}' does not exist"
            )
        
        total_rows = len(self.df)
        unique_rows = self.df[column].nunique()
        passed = total_rows == unique_rows
        
        return {
            "validation": "great_expectations",
            "result": "PASS" if passed else "FAIL",
            "column": column,
            "pk": "",
            "detail": f"Column '{column}': {total_rows - unique_rows} duplicate(s)" if not passed else f"Column '{column}': All {unique_rows} values unique (✓)",
            "source_value": exp.get("type"),
            "target_value": f"unique={unique_rows},total={total_rows}"
        }
    
    def _expect_column_values_to_be_between(self, exp: Dict) -> Dict[str, Any]:
        """Check that column values fall within min/max range."""
        column = exp.get("column")
        min_val = exp.get("min_value")
        max_val = exp.get("max_value")
        
        if not column:
            return self._error_result(exp, "Missing 'column' parameter")
        
        if column not in self.df.columns:
            return self._fail_result(
                exp, column, f"Column '{column}' does not exist"
            )
        
        try:
            violations = self.df[
                (self.df[column].notna()) & 
                ((self.df[column] < min_val) | (self.df[column] > max_val))
            ]
            passed = len(violations) == 0
            
            return {
                "validation": "great_expectations",
                "result": "PASS" if passed else "FAIL",
                "column": column,
                "pk": "",
                "detail": f"Column '{column}': {len(violations)} value(s) outside [{min_val}, {max_val}]" if violations.__len__() > 0 else f"Column '{column}': All values in range [{min_val}, {max_val}] (✓)",
                "source_value": exp.get("type"),
                "target_value": f"min={min_val},max={max_val},violations={len(violations)}"
            }
        except Exception as e:
            return self._error_result(exp, str(e))
    
    def _expect_column_values_to_match_regex(self, exp: Dict) -> Dict[str, Any]:
        """Check that column values match regex pattern."""
        column = exp.get("column")
        regex = exp.get("regex")
        
        if not column or not regex:
            return self._error_result(exp, "Missing 'column' or 'regex' parameter")
        
        if column not in self.df.columns:
            return self._fail_result(
                exp, column, f"Column '{column}' does not exist"
            )
        
        try:
            violations = self.df[
                self.df[column].astype(str).str.match(regex, na=False) == False
            ]
            passed = len(violations) == 0
            
            return {
                "validation": "great_expectations",
                "result": "PASS" if passed else "FAIL",
                "column": column,
                "pk": "",
                "detail": f"Column '{column}': {len(violations)} value(s) not matching pattern" if not passed else f"Column '{column}': All values match regex (✓)",
                "source_value": exp.get("type"),
                "target_value": f"pattern={regex},violations={len(violations)}"
            }
        except Exception as e:
            return self._error_result(exp, str(e))
    
    def _expect_column_values_to_be_in_set(self, exp: Dict) -> Dict[str, Any]:
        """Check that column values are in allowed set."""
        column = exp.get("column")
        value_set = exp.get("value_set", [])
        
        if not column or not value_set:
            return self._error_result(exp, "Missing 'column' or 'value_set' parameter")
        
        if column not in self.df.columns:
            return self._fail_result(
                exp, column, f"Column '{column}' does not exist"
            )
        
        violations = self.df[~self.df[column].isin(value_set) & self.df[column].notna()]
        passed = len(violations) == 0
        
        return {
            "validation": "great_expectations",
            "result": "PASS" if passed else "FAIL",
            "column": column,
            "pk": "",
            "detail": f"Column '{column}': {len(violations)} value(s) not in allowed set {value_set}" if not passed else f"Column '{column}': All values in allowed set (✓)",
            "source_value": exp.get("type"),
            "target_value": f"set_size={len(value_set)},violations={len(violations)}"
        }
    
    def _expect_column_to_exist(self, exp: Dict) -> Dict[str, Any]:
        """Check that column exists in DataFrame."""
        column = exp.get("column")
        if not column:
            return self._error_result(exp, "Missing 'column' parameter")
        
        exists = column in self.df.columns
        
        return {
            "validation": "great_expectations",
            "result": "PASS" if exists else "FAIL",
            "column": column,
            "pk": "",
            "detail": f"Column '{column}' exists (✓)" if exists else f"Column '{column}' not found",
            "source_value": exp.get("type"),
            "target_value": f"exists={exists}"
        }
    
    def _expect_table_row_count_to_be_between(self, exp: Dict) -> Dict[str, Any]:
        """Check that row count is within bounds."""
        min_rows = exp.get("min_value", 0)
        max_rows = exp.get("max_value")
        
        row_count = len(self.df)
        in_bounds = (row_count >= min_rows) and (max_rows is None or row_count <= max_rows)
        
        return {
            "validation": "great_expectations",
            "result": "PASS" if in_bounds else "FAIL",
            "column": "",
            "pk": "",
            "detail": f"Row count: {row_count} (in bounds [{min_rows}, {max_rows or '∞'}])" if in_bounds else f"Row count: {row_count} (out of bounds [{min_rows}, {max_rows or '∞'}])",
            "source_value": exp.get("type"),
            "target_value": f"rows={row_count},min={min_rows},max={max_rows}"
        }
    
    def _expect_column_values_to_be_of_type(self, exp: Dict) -> Dict[str, Any]:
        """Check that column has expected data type."""
        column = exp.get("column")
        expected_type = exp.get("type_name", "object").lower()
        
        if not column:
            return self._error_result(exp, "Missing 'column' parameter")
        
        if column not in self.df.columns:
            return self._fail_result(
                exp, column, f"Column '{column}' does not exist"
            )
        
        actual_dtype = str(self.df[column].dtype).lower()
        # Map common dtype aliases
        dtype_map = {
            "int64": ["int", "integer", "int64"],
            "float64": ["float", "float64", "double"],
            "object": ["object", "string", "str"],
            "bool": ["bool", "boolean"],
        }
        
        expected_matches = dtype_map.get(actual_dtype, [actual_dtype])
        passed = expected_type in expected_matches or expected_type == actual_dtype
        
        return {
            "validation": "great_expectations",
            "result": "PASS" if passed else "FAIL",
            "column": column,
            "pk": "",
            "detail": f"Column '{column}' type: {actual_dtype} (expected {expected_type})" + (" (✓)" if passed else ""),
            "source_value": exp.get("type"),
            "target_value": f"actual={actual_dtype},expected={expected_type}"
        }
    
    def _fail_result(self, exp: Dict, column: str, detail: str) -> Dict[str, Any]:
        """Create a FAIL result dict."""
        return {
            "validation": "great_expectations",
            "result": "FAIL",
            "column": column,
            "pk": "",
            "detail": detail,
            "source_value": exp.get("type"),
            "target_value": "FAIL"
        }
    
    def _error_result(self, exp: Dict, error_msg: str) -> Dict[str, Any]:
        """Create an ERROR result dict."""
        return {
            "validation": "great_expectations",
            "result": "ERROR",
            "column": exp.get("column", ""),
            "pk": "",
            "detail": f"Error: {error_msg}",
            "source_value": exp.get("type"),
            "target_value": "ERROR"
        }


def run_great_expectations(
    source_df: Optional[pd.DataFrame] = None,
    target_df: Optional[pd.DataFrame] = None,
    expectations: List[Dict[str, Any]] = None,
    run_on: str = "both",
    logger: Optional[logging.Logger] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to run Great Expectations on source/target DataFrames.
    
    Args:
        source_df: Source DataFrame (or None)
        target_df: Target DataFrame (or None)
        expectations: List of expectation configs from YAML
        run_on: "source", "target", or "both"
        logger: Optional logger
    
    Returns:
        List of normalized result dicts
    """
    all_results = []
    
    if expectations and run_on in ("source", "both") and source_df is not None:
        gx_source = GXValidator(source_df, expectations, "source", logger)
        all_results.extend(gx_source.validate())
    
    if expectations and run_on in ("target", "both") and target_df is not None:
        gx_target = GXValidator(target_df, expectations, "target", logger)
        all_results.extend(gx_target.validate())
    
    return all_results
