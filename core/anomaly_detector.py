"""
Anomaly Detection Integration using Isolation Forest

This module provides anomaly detection capabilities on numeric columns in DataFrames
using scikit-learn's Isolation Forest algorithm. Results are normalized into the
framework's standard validation result format for seamless integration with
CSV, HTML, and Excel reporting.

Design:
- Accepts a DataFrame and configuration for anomaly detection
- Runs Isolation Forest on selected numeric columns
- Returns normalized result dicts compatible with core/reporter.py
- Supports running on source, target, or both datasets
- Provides summary metrics and sample anomalous rows for investigation

Isolation Forest Algorithm:
- Detects anomalies by isolating outliers in a randomized decision tree forest
- Anomalies require fewer splits to isolate (have shorter paths in the forest)
- Efficient for high-dimensional data
- Does not assume any particular data distribution

Result Schema (compatible with existing framework):
{
    "validation": "anomaly_detection",
    "result": "PASS|WARN|INFO",
    "column": "column_name",  # or empty for dataset-level summary
    "pk": "",  # not typically used
    "detail": "Anomaly detection summary",
    "source_value": "method",
    "target_value": "anomaly_count"
}
"""

from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
import logging

try:
    from sklearn.ensemble import IsolationForest
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class AnomalyDetector:
    """
    Isolation Forest-based anomaly detector for numeric columns.
    
    Usage:
        detector = AnomalyDetector(df, columns=['revenue', 'discount'], logger=logger)
        results, anomalies_df = detector.detect(contamination=0.02)
    """
    
    def __init__(
        self,
        dataframe: pd.DataFrame,
        columns: List[str],
        contamination: float = 0.02,
        random_state: int = 42,
        max_samples: str = "auto",
        dataframe_label: str = "data",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the anomaly detector.
        
        Args:
            dataframe: pandas DataFrame to analyze
            columns: List of numeric column names to analyze
            contamination: Expected proportion of outliers (0 < contamination <= 1)
            random_state: Random seed for reproducibility
            max_samples: Number of samples to draw (int or "auto")
            dataframe_label: Label for this dataset (e.g., "source", "target")
            logger: Optional logger instance
        """
        if not HAS_SKLEARN:
            raise ImportError(
                "scikit-learn is required for anomaly detection. "
                "Install it with: pip install scikit-learn"
            )
        
        self.df = dataframe.copy()
        self.columns = columns or []
        self.contamination = contamination
        self.random_state = random_state
        self.max_samples = max_samples
        self.label = dataframe_label
        self.logger = logger or logging.getLogger(__name__)
        self.anomaly_scores = None
        self.anomalies = None
        self.results: List[Dict[str, Any]] = []
    
    def detect(self) -> Tuple[List[Dict[str, Any]], Optional[pd.DataFrame]]:
        """
        Run Isolation Forest and detect anomalies.
        
        Returns:
            Tuple of (normalized_results, anomalies_dataframe)
            - anomalies_dataframe: DataFrame with anomalous rows (or None if no anomalies)
        """
        if not self.columns:
            self.logger.warning(f"No columns specified for anomaly detection on {self.label}")
            return [], None
        
        # Validate columns exist and are numeric
        invalid_cols = [c for c in self.columns if c not in self.df.columns]
        if invalid_cols:
            self.logger.error(f"Columns not found in {self.label}: {invalid_cols}")
            self.results.append(self._error_result(f"Missing columns: {invalid_cols}"))
            return self.results, None
        
        non_numeric_cols = [
            c for c in self.columns 
            if not pd.api.types.is_numeric_dtype(self.df[c])
        ]
        if non_numeric_cols:
            self.logger.warning(f"Non-numeric columns skipped: {non_numeric_cols}")
            self.columns = [c for c in self.columns if c not in non_numeric_cols]
        
        if not self.columns:
            self.logger.error(f"No numeric columns available after filtering")
            self.results.append(self._error_result("No numeric columns to analyze"))
            return self.results, None
        
        try:
            self._run_isolation_forest()
            self._generate_results()
        except Exception as e:
            self.logger.error(f"Anomaly detection failed: {e}")
            self.results.append(self._error_result(str(e)))
            return self.results, None
        
        return self.results, self.anomalies
    
    def _run_isolation_forest(self):
        """Execute Isolation Forest algorithm."""
        self.logger.info(
            f"Running Isolation Forest on {self.label} "
            f"({len(self.columns)} columns, contamination={self.contamination})"
        )
        
        # Prepare data: drop NaN values in selected columns
        df_clean = self.df[self.columns].dropna()
        
        if len(df_clean) == 0:
            raise ValueError(f"No valid data after removing NaNs")
        
        # Run Isolation Forest
        iso_forest = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            max_samples=self.max_samples
        )
        
        predictions = iso_forest.fit_predict(df_clean)  # -1 = anomaly, 1 = normal
        anomaly_scores = iso_forest.score_samples(df_clean)  # negative = anomalies
        
        # Map predictions back to original dataframe indices
        self.df.loc[df_clean.index, '_anomaly_pred'] = predictions
        self.df.loc[df_clean.index, '_anomaly_score'] = anomaly_scores
        
        # Fill NaN rows with normal (1) to keep full dataset
        self.df['_anomaly_pred'] = self.df['_anomaly_pred'].fillna(1)
        self.df['_anomaly_score'] = self.df['_anomaly_score'].fillna(0)
        
        # Extract anomalies
        self.anomalies = self.df[self.df['_anomaly_pred'] == -1].copy()
        self.anomaly_scores = self.df['_anomaly_score']
    
    def _generate_results(self):
        """Generate normalized result dicts."""
        total_rows = len(self.df)
        anomaly_count = len(self.anomalies) if self.anomalies is not None else 0
        anomaly_pct = (anomaly_count / total_rows * 100) if total_rows > 0 else 0
        
        # Dataset-level summary
        result_status = "PASS" if anomaly_count == 0 else ("WARN" if anomaly_pct <= (self.contamination * 100 * 1.5) else "WARN")
        
        summary = {
            "validation": "anomaly_detection",
            "result": result_status,
            "column": "",
            "pk": "",
            "detail": f"Anomaly Detection on {self.label} ({len(self.columns)} columns): "
                     f"{anomaly_count}/{total_rows} anomalies ({anomaly_pct:.2f}%)",
            "source_value": "isolation_forest",
            "target_value": f"anomalies={anomaly_count},rate={anomaly_pct:.2f}%"
        }
        self.results.append(summary)
        
        # Per-column breakdown (if useful)
        for col in self.columns:
            col_anomalies = self.anomalies[self.columns] if self.anomalies is not None else pd.DataFrame()
            if len(col_anomalies) > 0:
                col_min = col_anomalies[col].min()
                col_max = col_anomalies[col].max()
                normal_min = self.df[self.df['_anomaly_pred'] == 1][col].min()
                normal_max = self.df[self.df['_anomaly_pred'] == 1][col].max()
                
                detail = f"Column '{col}': anomaly range [{col_min:.2f}, {col_max:.2f}] vs normal [{normal_min:.2f}, {normal_max:.2f}]"
            else:
                detail = f"Column '{col}': No anomalies detected"
            
            self.results.append({
                "validation": "anomaly_detection_detail",
                "result": "PASS" if len(col_anomalies) == 0 else "INFO",
                "column": col,
                "pk": "",
                "detail": detail,
                "source_value": "isolation_forest",
                "target_value": f"anomalies={len(col_anomalies)}"
            })
    
    def get_anomalies_sample(self, n_rows: int = 20) -> pd.DataFrame:
        """
        Get a sample of anomalous rows for reporting.
        
        Args:
            n_rows: Maximum number of anomalies to return
        
        Returns:
            DataFrame of anomalous rows (sorted by anomaly score)
        """
        if self.anomalies is None or len(self.anomalies) == 0:
            return pd.DataFrame()
        
        # Sort by anomaly score (most anomalous first)
        sorted_anomalies = self.anomalies.sort_values('_anomaly_score')
        
        # Drop internal columns
        sample = sorted_anomalies.head(n_rows).drop(
            columns=['_anomaly_pred', '_anomaly_score'],
            errors='ignore'
        )
        
        return sample
    
    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """Create an ERROR result dict."""
        return {
            "validation": "anomaly_detection",
            "result": "ERROR",
            "column": "",
            "pk": "",
            "detail": f"Anomaly Detection Error: {error_msg}",
            "source_value": "isolation_forest",
            "target_value": "ERROR"
        }


def run_anomaly_detection(
    source_df: Optional[pd.DataFrame] = None,
    target_df: Optional[pd.DataFrame] = None,
    columns: List[str] = None,
    contamination: float = 0.02,
    random_state: int = 42,
    max_samples: str = "auto",
    run_on: str = "both",
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function to run anomaly detection on source/target DataFrames.
    
    Args:
        source_df: Source DataFrame (or None)
        target_df: Target DataFrame (or None)
        columns: List of numeric column names to analyze
        contamination: Expected proportion of outliers
        random_state: Random seed for reproducibility
        max_samples: Number of samples to draw
        run_on: "source", "target", or "both"
        logger: Optional logger
    
    Returns:
        Tuple of (normalized_results, anomalies_dict)
        where anomalies_dict = {"source": df, "target": df}
    """
    all_results = []
    anomalies_dict = {}
    
    if columns and run_on in ("source", "both") and source_df is not None:
        detector_source = AnomalyDetector(
            source_df, columns, contamination, random_state, 
            max_samples, "source", logger
        )
        results, anomalies = detector_source.detect()
        all_results.extend(results)
        anomalies_dict["source"] = anomalies
    
    if columns and run_on in ("target", "both") and target_df is not None:
        detector_target = AnomalyDetector(
            target_df, columns, contamination, random_state,
            max_samples, "target", logger
        )
        results, anomalies = detector_target.detect()
        all_results.extend(results)
        anomalies_dict["target"] = anomalies
    
    return all_results, anomalies_dict
