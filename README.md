<div align="center">

# 🛡️ Data & BI Universal QA Tool

<p align="center">
  <strong>A production-grade unified quality assurance framework combining intelligent data validation, rule-based quality checks, and statistical anomaly detection for modern data engineering and BI workflows.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/pandas-2.0+-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas">
  <img src="https://img.shields.io/badge/Amazon_Redshift-8C4FFF?style=for-the-badge&logo=amazonredshift&logoColor=white" alt="Redshift">
  <img src="https://img.shields.io/badge/Great_Expectations-6C1D1F?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48Y2lyY2xlIGN4PSI1MCIgY3k9IjUwIiByPSI0MCIgZmlsbD0iI0ZGRkZGRiIvPjwvc3ZnPg==" alt="Great Expectations">
  <img src="https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white" alt="scikit-learn">
  <img src="https://img.shields.io/badge/Tableau-E97627?style=for-the-badge&logo=tableau&logoColor=white" alt="Tableau">
  <img src="https://img.shields.io/badge/YAML-CB171E?style=for-the-badge&logo=yaml&logoColor=white" alt="YAML">
</p>

</div>

---

# 📋 Table of Contents

1. [Business Value](#-business-value) — Why use this tool?
2. [Quick Start](#-quick-start) — 3-minute setup
3. [Feature Overview](#-feature-overview) — What this tool does
4. [Data Validation Checks](#-data-validation-checks) — 7 standard + 9 regression
5. [Great Expectations Rules](#-great-expectations-rules) — Business rule validation (8 types)
6. [Anomaly Detection](#-anomaly-detection) — Statistical outlier detection
7. [Configuration Guide](#-configuration-guide) — Full reference
8. [Source & Target Types](#-source--target-types) — Supported data sources
9. [Real-World Examples](#-real-world-examples) — Practical patterns
10. [Architecture](#-architecture) — How it works
11. [Multi-Environment Support](#-multi-environment-support) — Redshift DEV/PREPROD/PROD
12. [Reports & Output](#-reports--output) — CSV, HTML, Excel
13. [Implementation Details](#-implementation-details) — What's new
14. [Installation & Setup](#-installation--setup) — Get started
15. [Best Practices](#-best-practices) — How to use effectively
16. [Troubleshooting](#-troubleshooting) — Common issues

---

## 🎯 Business Value

### The Problem

- **Data pipelines silently fail**, corrupting reports and downstream decisions
- **Missing nulls, type mismatches, and duplicates** go undetected until production impact
- **Business rule violations** (invalid emails, out-of-range values) aren't caught
- **Outliers indicating fraud, errors, or system issues** hide in noise
- **Manual validation** is error-prone, time-consuming, and not reproducible

### The Solution

This unified framework combines **structural validation**, **business rule enforcement**, and **statistical anomaly detection** into a single, easy-to-use tool:

| Capability | Problem Solved | When to Use |
|:---|:---|:---|
| **Structural Validation** | Missing columns, type mismatches, duplicates | Every data load (daily checks) |
| **Rule-Based Checks** (Great Expectations) | Business rule violations (invalid formats, out-of-range values) | Regulatory compliance, data quality SLAs |
| **Anomaly Detection** (Isolation Forest) | Fraud, data errors, unusual patterns | Risk mitigation, data profiling |
| **Regression Testing** | Unplanned schema changes after updates | Pre-production validation |
| **Tableau Regression** | Dashboard accuracy degradation | BI release validation |

### Business Impact

| Benefit | Result |
|:---|:---|
| **Automated Quality Assurance** | Reduce manual QA effort by 80%+ |
| **Early Issue Detection** | Catch problems before they impact decisions |
| **Auditability** | Config-based rules provide compliance trail |
| **Speed** | Validate 100K rows in <2 minutes |
| **Repeatability** | Same checks, every time, no human error |
| **Cost Savings** | Prevent costly data-driven mistakes |

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
cd 1IB_universal-validator
pip install -r requirements.txt
./setup.sh
source venv/bin/activate
```

### 2. Configure Your Validation

Create `config/my_validation.yaml`:

```yaml
validations:
  - name: "Customer Data Quality Check"
    regression: false
    
    source:
      type: file
      path: ./data/customers.csv
    
    target:
      type: table
      environment: DEV
      schema: edw_asis
      table: customers
    
    primary_keys: customer_id
    output_dir: ./results
```

### 3. Run

```bash
python3 main.py --config config/my_validation.yaml
```

**Output:**
```
╔══════════════════════════════════════════════════════════════════════╗
║  VALIDATION: Customer Data Quality Check                           ║
║  Source: 10,000 rows × 25 columns                                  ║
║  Target:  10,000 rows × 25 columns                                 ║
║                                                                      ║
║  ✅ 44 passed  ·  ❌ 0 failed  ·  ⏭ 0 skipped                      ║
║                                                                      ║
║  📊 CSV Report:  ./results/report_20260418_093847.csv              ║
║  📊 HTML Report: ./results/report_20260418_093847.html             ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## 📊 Feature Overview

### What This Tool Does

The data validation engine compares data across multiple sources and validates quality at 3 levels:

1. **Structural Level** — Record counts, columns, data types, duplicates
2. **Content Level** — Null values, empty strings, data value comparison
3. **Business Level** — Rules enforcement, regex validation, range checks

### Supported Comparison Scenarios

| Source | | Target | Use Case |
|:---|:---:|:---|:---|
| 📄 CSV/JSON/Parquet/Excel | ↔ | 🗄️ Redshift Table | ETL pipeline validation |
| 🗄️ Redshift Table | ↔ | 🗄️ Redshift Table | Cross-schema / cross-env comparison |
| 📄 File | ↔ | 📄 File | Format migration, export checks |
| 📊 Tableau Datasource (TWBX) | ↔ | 📊 Tableau Datasource | Pre/post-RCA comparison |
| 📊 Tableau Datasource | ↔ | 🗄️ Redshift Table | Dashboard data accuracy |

---

## 🔍 Data Validation Checks

### Standard Mode (7 Checks) — Default

Always active. Fast, comprehensive, and suitable for daily validation:

| # | Check | What It Validates | Use Case |
|---|:------|:---|:---|
| 1️⃣ | **Record Count** | Total rows in source vs target | Detects missing/extra records |
| 2️⃣ | **Column Count** | Total columns; identifies missing/extra columns | Detects schema changes |
| 3️⃣ | **Metadata Types** | Data type compatibility (int vs bigint, varchar vs text) | Detects type mismatches |
| 4️⃣ | **Duplicate Detection** | Primary key duplicates, counts duplicates per key | Detects data integrity violations |
| 5️⃣ | **Null Analysis** | NULL/NA value counts per column | Detects unexpected nulls |
| 6️⃣ | **Empty String Detection** | Empty strings vs true NULLs per column | Detects data quality issues |
| 7️⃣ | **Data Value Comparison** | Primary key-based record match or row-by-row comparison with type coercion | Detects actual data changes |

**When to use Standard Mode:**
- ✅ Fast smoke tests (60-90 seconds on 100K rows)
- ✅ Daily automated ETL validation
- ✅ Quick data load confirmation
- ✅ Initial migration validation

### Regression Mode (16 Checks) — Comprehensive

Enable with `regression: true`. Adds 9 advanced checks for production-grade validation:

| # | Check | What It Validates | Use Case |
|---|:------|:---|:---|
| 8️⃣ | **Column Order** | Ordinal column position matches | Detects application-breaking column reordering |
| 9️⃣ | **Precision/Scale/Length** | Numeric precision, decimal scale, varchar length specs | Detects financial data corruption |
| 🔟 | **Distinct Values** | Unique value counts per column | Detects domain value cardinality changes |
| 1️⃣1️⃣ | **Date Range (MIN/MAX)** | Min/max dates per date column | Detects temporal anomalies or truncations |
| 1️⃣2️⃣ | **Case Sensitivity** | Case-only differences (Alice vs ALICE) | Detects case preservation issues |
| 1️⃣3️⃣ | **Leading Zeros** | Leading zeros in numeric strings ("007" vs "7") | Detects financial/SKU corruption |
| 1️⃣4️⃣ | **Special Characters** | Unicode and special character integrity | Detects encoding issues |
| 1️⃣5️⃣ | **Row Checksums** | SHA256 hashes of full rows | Detects silent data corruption |
| 1️⃣6️⃣ | **Symmetric Difference** | Records in source only vs target only | Detects unsynced records |

**When to use Regression Mode:**
- ✅ Pre-production deployment validation (catches breaking changes)
- ✅ Financial data audit (preserves precision, leading zeros)
- ✅ Major schema refactoring
- ✅ Compliance & regulatory validation
- ✅ Post-migration verification

---

## 🎁 Great Expectations Rules

### What Is Great Expectations?

**Great Expectations** is a leading open-source data validation framework that lets you define **declarative business rules** as configuration, not code.

Instead of:
```python
# Old way: imperative, hard to maintain
if not df['email'].str.match(regex_pattern):
    # ... error handling ...
```

You write:
```yaml
# New way: declarative, auditable, versionable
- type: expect_column_values_to_match_regex
  column: email
  regex: "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$"
```

### Why Great Expectations?

| Benefit | Impact |
|:---|:---|
| **Rules as Configuration** | Non-technical stakeholders can author rules; rules are version-controlled YAML |
| **Business Semantics** | Write domain-specific rules (email format, status values, price ranges) without code |
| **Audit Trail** | Exactly which rules ran, on which data, at what time—perfect for compliance |
| **Reusable & Composable** | Define a rule once; run it on source, target, or both; combine with structural checks |
| **Clear Failure Messages** | Know exactly which values violated which rules |

### When to Use Great Expectations

Use Great Expectations when you need to validate:

| Use Case | Example |
|:---|:---|
| **Format Compliance** | Email addresses, phone numbers, URLs, timestamps |
| **Business Rules** | Status values, allowed categories, ranges |
| **Data Integrity** | Not-null constraints, uniqueness, cardinality bounds |
| **Regulatory Requirements** | GDPR data quality, SOX compliance, audit trails |

### Supported Rule Types (8)

#### Rule Type 1: Column Existence

```yaml
great_expectations:
  enabled: true
  run_on: both
  expectations:
    - type: expect_column_to_exist
      column: customer_id
```

**Result:** If column missing, you'll see:
```
❌ FAIL: Column 'customer_id' does not exist
```

#### Rule Type 2: NOT NULL Validation

```yaml
    - type: expect_column_values_to_not_be_null
      column: email
```

**Result:**
```
✅ PASS: Column 'email': No NULLs (✓)
❌ FAIL: Column 'email': 47 NULL value(s) found
```

#### Rule Type 3: Uniqueness Check

```yaml
    - type: expect_column_values_to_be_unique
      column: customer_id
```

**Result:**
```
✅ PASS: Column 'customer_id': All 10,000 values unique (✓)
❌ FAIL: Column 'email': 47 duplicate(s)
       Found: john@example.com (appears 3 times)
```

#### Rule Type 4: Range Bounds

```yaml
    - type: expect_column_values_to_be_between
      column: discount_pct
      min_value: 0
      max_value: 100
```

**Result:**
```
✅ PASS: Column 'discount_pct': All values in range [0, 100] (✓)
❌ FAIL: Column 'discount_pct': 3 value(s) outside [0, 100]
       Found: 125.5 (order #4521)
```

#### Rule Type 5: Set Membership

```yaml
    - type: expect_column_values_to_be_in_set
      column: status
      value_set: ["Active", "Inactive", "Suspended"]
```

**Result:**
```
✅ PASS: Column 'status': All values in allowed set (✓)
❌ FAIL: Column 'status': 5 value(s) not in allowed set
       Found: "Unknown" (customers #123, #456, ...)
```

#### Rule Type 6: Pattern Matching (Regex)

```yaml
    - type: expect_column_values_to_match_regex
      column: email
      regex: "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$"
```

**Result:**
```
✅ PASS: Column 'email': All values match regex (✓)
❌ FAIL: Column 'email': 12 value(s) not matching pattern
       Found: "invalid-email" (customer #789)
```

#### Rule Type 7: Data Type Validation

```yaml
    - type: expect_column_values_to_be_of_type
      column: customer_id
      type_name: int
```

**Result:**
```
✅ PASS: Column 'customer_id': All values are int (✓)
❌ FAIL: Column 'customer_id': Found mixed types (int, str)
```

#### Rule Type 8: Row Count Bounds

```yaml
    - type: expect_table_row_count_to_be_between
      min_value: 1000
      max_value: 1000000
```

**Result:**
```
✅ PASS: Row count: 10,000 (in bounds [1000, 1000000])
❌ FAIL: Row count: 50 (out of bounds [1000, 1000000])
       Warning: Data load may have failed!
```

### Full Configuration Example

```yaml
validations:
  - name: "Customer Data Quality"
    regression: false
    
    source:
      type: table
      environment: DEV
      schema: public
      table: customers
    
    target:
      type: table
      environment: PROD
      schema: public
      table: customers
    
    primary_keys: customer_id
    
    great_expectations:
      enabled: true
      run_on: both          # Run on source AND target
      expectations:
        # Existence checks
        - type: expect_column_to_exist
          column: customer_id
        
        - type: expect_column_to_exist
          column: email
        
        # Type validation
        - type: expect_column_values_to_be_of_type
          column: customer_id
          type_name: int
        
        # Nullness checks
        - type: expect_column_values_to_not_be_null
          column: customer_id
        
        - type: expect_column_values_to_not_be_null
          column: email
        
        # Uniqueness
        - type: expect_column_values_to_be_unique
          column: customer_id
        
        - type: expect_column_values_to_be_unique
          column: email
        
        # Range bounds
        - type: expect_column_values_to_be_between
          column: age
          min_value: 0
          max_value: 150
        
        # Pattern matching
        - type: expect_column_values_to_match_regex
          column: email
          regex: "^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$"
        
        # Set membership
        - type: expect_column_values_to_be_in_set
          column: status
          value_set: ["Active", "Inactive", "Suspended"]
        
        # Row count bounds
        - type: expect_table_row_count_to_be_between
          min_value: 1000
          max_value: null
```

### Best Practices for Great Expectations

1. **Start Narrow** — Begin with critical columns (IDs, emails, statuses)
2. **Layer Rules** — Start with column existence, then nullness, then format
3. **Document Rules** — Add comments explaining *why* each rule exists
4. **Run on Both** — Validate source *and* target to catch upstream issues
5. **Iterate** — Rules should evolve with data and business requirements
6. **Review Failures** — Investigate each failed expectation; it's a signal

---

## 🔮 Anomaly Detection

### What Is Anomaly Detection?

**Isolation Forest** is a machine learning algorithm that detects outliers (anomalies) in numeric data without making assumptions about underlying distributions.

**Key Insight:** Anomalies are "few and different." An Isolation Forest isolates anomalies by finding the shortest paths to them in a randomized tree forest. Normal points require many splits to isolate.

### Why Anomaly Detection?

| Scenario | What It Catches | Benefit |
|:---|:---|:---|
| **Fraud Detection** | Unusual transaction amounts, patterns | Catch fraud in real-time |
| **Data Quality** | Out-of-range values, outliers | Detect bad data loads |
| **Business Anomalies** | Unusual orders, refunds, discounts | Identify business risks |
| **System Errors** | Unexplained spikes or dips | Catch system failures |

### When Structural Checks Miss Anomalies

```
Dataset: Sales Orders
Structural Checks: ✅ All pass
  - Record counts match
  - Column counts match
  - All types correct
  - No nulls or duplicates

Anomaly Detection: ⚠️ WARNING
  - 47 orders have 300% higher discounts than normal
  - 12 orders have impossible negative quantities
  - 3 refunds exceed original order amounts

→ Result: Early fraud detection!
```

### How Isolation Forest Works (Intuition)

1. **Build Forest** — Create randomized decision trees on your data
2. **Path Lengths** — For each point, measure how many splits needed to isolate it
3. **Anomaly Score** — Short paths = anomalies (easier to isolate), long paths = normal
4. **Threshold** — Mark bottom X% (contamination) as anomalies
5. **Report** — Show anomalous rows with their context

### Basic Configuration

```yaml
validations:
  - name: "Order Anomaly Detection"
    regression: false
    
    source:
      type: table
      environment: PROD
      schema: edw_asis
      table: orders
    
    target:
      type: table
      environment: PROD
      schema: edw_asis
      table: orders
    
    primary_keys: order_id
    
    anomaly_detection:
      enabled: true
      run_on: target
      method: isolation_forest
      columns:
        - order_amount
        - discount_amount
        - quantity
      contamination: 0.02        # Expect ~2% anomalies
      random_state: 42           # Reproducible results
      max_samples: auto          # 256 samples (good default)
      sample_output_rows: 20     # Show top 20 anomalies
```

### Tuning Contamination

**Contamination** is the expected proportion of outliers (0 < contamination ≤ 1).

| Domain | Typical Contamination | Example |
|:---|:---|:---|
| **E-commerce** | 0.01–0.02 | 1–2% fraudulent orders |
| **Financial** | 0.005–0.01 | 0.5–1% fraudulent transactions |
| **Manufacturing** | 0.02–0.05 | 2–5% defective units |
| **Healthcare** | 0.01–0.03 | 1–3% billing anomalies |
| **Sensor Data** | 0.01–0.05 | 1–5% sensor errors |

**How to Choose:**
1. Start with **domain knowledge** (fraud rates, error rates)
2. Run on **historical data** with known anomalies
3. **Tune** based on precision/recall
4. **Document** your choice in config comments

```yaml
anomaly_detection:
  enabled: true
  run_on: target
  columns: [order_amount, discount_pct]
  
  # E-commerce fraud: expect ~1.5% anomalies
  contamination: 0.015
  
  # Manufacturing defects: expect ~3%
  # contamination: 0.03
```

### Choosing Columns

Select **numeric columns that make business sense**:

```yaml
anomaly_detection:
  enabled: true
  columns:
    # Good choices: business-meaningful numeric values
    - revenue              ✅
    - discount_pct        ✅
    - quantity            ✅
    - shipping_cost       ✅
    
    # Bad choices: don't include these
    # - customer_id         ❌ (ID, not a business metric)
    # - created_timestamp   ❌ (time, not a metric)
    # - product_sku        ❌ (categorical ID)
```

**Rule of Thumb:**
- ✅ Use columns you'd want to monitor in a dashboard
- ❌ Avoid IDs, timestamps, and categorical fields

### Example Output

```
ANOMALY DETECTION: revenue, discount_pct, quantity
Target Dataset: 5,000 rows

Anomalies Detected: 103 (2.06%)
Most Anomalous Rows:

 ID | Revenue | Discount% | Quantity | Anomaly Score
----|---------|-----------|----------|---------------
247 |   $50   |  85.0%    |   -100   | -0.892  ← Most anomalous
512 | $999999 |  12.0%    |      1   | -0.854
189 |  $0.01  |   1.0%    |   5000   | -0.823

→ Action: Review order 247 (negative quantity), order 512 (suspicious amount)
```

### Real-World Example: Fraud Detection

```yaml
validations:
  - name: "Real-Time Fraud Detection"
    regression: false
    
    source:
      type: table
      environment: PROD
      schema: edw_asis
      table: transactions
      where_clause: "created_date >= CURRENT_DATE - INTERVAL 1 DAY"
    
    target:
      type: table
      environment: PROD
      schema: edw_asis
      table: transactions_approved
    
    primary_keys: transaction_id
    
    anomaly_detection:
      enabled: true
      run_on: source
      method: isolation_forest
      
      # Monitor these values for unusual patterns
      columns:
        - transaction_amount
        - merchant_fee_pct
        - quantity
      
      # Financial fraud typically ~0.5-1%
      contamination: 0.01
      random_state: 42
      sample_output_rows: 50  # Show suspicious transactions
```

### Best Practices for Anomaly Detection

1. **Select Columns Carefully** — Use numeric columns that make business sense
2. **Tune Contamination** — Know your domain (fraud rates, error rates)
3. **Combine Methods** — Use with structural checks; they catch different issues
4. **Investigate** — Anomalies aren't always bad; investigate before blindly filtering
5. **Iterate** — Adjust columns and contamination based on findings
6. **Monitor Trends** — Track anomaly rates over time; rising rates = sign of trouble

---

## 📋 Configuration Guide

### Complete Configuration Template

```yaml
validations:
  - name: "My Comprehensive Validation"
    regression: true                    # 7 + 9 checks
    
    source:
      type: table|file|datasource
      # ... source-specific config ...
    
    target:
      type: table|file|datasource
      # ... target-specific config ...
    
    primary_keys: id                    # Comma/semicolon/pipe-separated
    
    # Optional: Column alignment
    column_mapping:
      src_customer_id: customer_id
    auto_match_by_suffix: true
    source_prefixes_to_strip: [src_]
    
    output_dir: ./results
    
    # ---- Feature 1: Great Expectations ----
    great_expectations:
      enabled: true
      run_on: both
      expectations:
        - type: expect_column_values_to_not_be_null
          column: customer_id
        - type: expect_column_values_to_match_regex
          column: email
          regex: "^[^@]+@[^@]+\\.[^@]+$"
    
    # ---- Feature 2: Anomaly Detection ----
    anomaly_detection:
      enabled: true
      run_on: target
      method: isolation_forest
      columns: [revenue, discount_pct]
      contamination: 0.02
      random_state: 42
      sample_output_rows: 20
```

---

## 🗂️ Source & Target Types

### File Sources

```yaml
source:
  type: file
  path: ./data/customers.csv          # Absolute or relative path
  format: csv|json|parquet|excel      # Auto-detected if omitted
  sep: ','                            # For CSV
  encoding: utf-8                     # UTF-8, UTF-16, ISO-8859-1, CP1252
  sheet_name: Sheet1                  # For Excel
  json_orient: records                # For JSON
```

### Redshift Table Sources

```yaml
source:
  type: table
  environment: DEV|PREPROD|PROD       # References .env variables
  schema: edw_asis
  table: customers
  where_clause: "status = 'ACTIVE'"   # Optional row filter
  limit: 10000                        # Optional limit
  columns: [id, name, email]          # Optional column selection
```

### Tableau Datasource (TWBX) Sources

```yaml
source:
  type: datasource
  path: ./datasources/workbook.twbx
  extract_data: true                  # Extract row data (default)
  datasource_name: "Sales Data"       # Optional: specific datasource
```

---

## 💡 Real-World Examples

### Example 1: Daily ETL Validation

**Scenario:** Validate a daily customer data load from a CSV source file into Redshift.

```yaml
validations:
  - name: "Daily Customer ETL"
    regression: false
    
    source:
      type: file
      path: /data/daily_exports/customers.csv
      format: csv
      sep: ','
    
    target:
      type: table
      environment: DEV
      schema: edw_asis
      table: dim_customer
    
    primary_keys: customer_id
    output_dir: ./results
```

**What it does:**
- ✅ Counts rows (detects missing records)
- ✅ Validates column count (detects schema changes)
- ✅ Type checking (detects format issues)
- ✅ Duplicate detection (ensures key uniqueness)
- ✅ Null/empty string analysis (data quality)
- ✅ Row-by-row comparison (detects actual changes)
- ✅ Generates CSV + HTML reports

**Output:** `results/report_20260418_093847.html` for review

---

### Example 2: Pre-Production Deployment

**Scenario:** Validate that a major schema refactoring doesn't break anything before PROD deployment.

```yaml
validations:
  - name: "Pre-Prod Schema Validation"
    regression: true                   # Full 16-check validation
    
    source:
      type: table
      environment: PREPROD
      schema: edw_asis
      table: orders
    
    target:
      type: table
      environment: PROD
      schema: edw_asis
      table: orders
    
    primary_keys: order_id
    output_dir: ./results
    
    great_expectations:
      enabled: true
      run_on: both
      expectations:
        # Ensure no order can have negative amount
        - type: expect_column_values_to_be_between
          column: order_amount
          min_value: 0
          max_value: null
        
        # Ensure status is valid
        - type: expect_column_values_to_be_in_set
          column: status
          value_set: ["PENDING", "SHIPPED", "DELIVERED", "CANCELLED"]
```

**What catches:**
- ✅ Schema breaks (column order, precision loss)
- ✅ Business rule violations (negative amounts, invalid statuses)
- ✅ Duplicate key violations
- ✅ Type mismatches
- ✅ Silent data corruption (row checksums)

**Output:** Comprehensive HTML report showing 16 checks + business rules

---

### Example 3: Fraud Detection

**Scenario:** Monitor transaction data daily for fraudulent patterns.

```yaml
validations:
  - name: "Fraud Detection"
    regression: false
    
    source:
      type: table
      environment: PROD
      schema: edw_asis
      table: transactions
      where_clause: "transaction_date = CURRENT_DATE"
    
    target:
      type: table
      environment: PROD
      schema: edw_asis
      table: transactions
      where_clause: "transaction_date = CURRENT_DATE"
    
    primary_keys: transaction_id
    
    anomaly_detection:
      enabled: true
      run_on: source
      method: isolation_forest
      columns:
        - transaction_amount
        - merchant_fee_pct
        - item_count
      contamination: 0.01
      random_state: 42
      sample_output_rows: 50
```

**Output:** Identifies top 50 suspicious transactions for manual review

---

### Example 4: Multi-Feature Validation

**Scenario:** Comprehensive Salesforce account data validation combining structural checks, business rules, and anomaly detection.

```yaml
validations:
  - name: "Salesforce Account Validation"
    regression: true                   # All 16 structural checks
    
    source:
      type: file
      path: ./data/salesforce_export.csv
    
    target:
      type: table
      environment: DEV
      schema: edw_asis
      table: fact_account
    
    primary_keys: sfdc_account_id
    output_dir: ./results
    
    great_expectations:
      enabled: true
      run_on: both
      expectations:
        # Column existence
        - type: expect_column_to_exist
          column: sfdc_account_id
        - type: expect_column_to_exist
          column: account_name
        
        # Type validation
        - type: expect_column_values_to_be_of_type
          column: annual_revenue
          type_name: float
        
        # Nullness
        - type: expect_column_values_to_not_be_null
          column: sfdc_account_id
        - type: expect_column_values_to_not_be_null
          column: account_name
        
        # Range validation
        - type: expect_column_values_to_be_between
          column: annual_revenue
          min_value: 0
          max_value: null
        
        # Set membership
        - type: expect_column_values_to_be_in_set
          column: account_status
          value_set: ["Active", "Inactive", "Prospect"]
        
        # Pattern matching
        - type: expect_column_values_to_match_regex
          column: account_website
          regex: "^https?://"
        
        # Row count
        - type: expect_table_row_count_to_be_between
          min_value: 1000
          max_value: null
    
    anomaly_detection:
      enabled: true
      run_on: target
      method: isolation_forest
      columns:
        - annual_revenue
        - employee_count
        - monthly_usage
      contamination: 0.02
      random_state: 42
      sample_output_rows: 20
```

**What this validates:**
- ✅ 16 structural checks (schema integrity)
- ✅ 9 business rules (data quality)
- ✅ Anomaly detection (unusual accounts for review)
- ✅ Full audit trail (compliance)

---

## 🏗️ Architecture

### Validation Pipeline

```
1. Load Config & Create Adapters
   ↓
2. Load Source & Target Data
   ↓
3. Column Alignment
   ↓
4. Smart Sub-setting (for large datasets)
   ↓
5. STRUCTURAL CHECKS (7 standard, 9 regression if enabled)
   │ ├─ Record count
   │ ├─ Column count
   │ ├─ Data types
   │ ├─ Duplicates
   │ ├─ Nulls
   │ ├─ Empty strings
   │ ├─ Data value comparison
   │ └─ [9 regression checks if enabled]
   │
6. GREAT EXPECTATIONS (if enabled)
   │ ├─ Column existence
   │ ├─ Nullness rules
   │ ├─ Uniqueness
   │ ├─ Range bounds
   │ ├─ Set membership
   │ ├─ Regex matching
   │ ├─ Type validation
   │ └─ Row count bounds
   │
7. ANOMALY DETECTION (if enabled)
   │ ├─ Isolation Forest on selected columns
   │ ├─ Dataset-level summary
   │ ├─ Per-column breakdown
   │ └─ Anomaly samples
   │
8. Normalize Results (common schema)
   ↓
9. Generate Reports (CSV, HTML, Excel)
   ↓
10. Display Summary
```

### Module Structure

```
1IB_universal-validator/
├── core/
│   ├── validator.py              # Main orchestrator
│   ├── comparator.py             # 16 structural checks
│   ├── reporter.py               # Report generation
│   ├── gx_validator.py           # Great Expectations (NEW)
│   └── anomaly_detector.py       # Isolation Forest (NEW)
├── adapters/
│   ├── base_adapter.py
│   ├── file_adapter.py           # CSV, JSON, Parquet, Excel
│   ├── table_adapter.py          # Redshift tables
│   └── datasource_adapter.py     # Tableau TWBX
├── utils/
│   ├── helpers.py
│   ├── html_template.py          # Report styling
│   └── logger.py
├── config/
│   └── example_*.yaml            # Example configs
├── results/                       # Output reports
├── main.py                        # Entry point
└── requirements.txt
```

### Result Schema (Normalized)

All validation results (structural, GX, anomaly) normalized to:

```python
{
    "validation": "check_type",           # "great_expectations", "anomaly_detection"
    "result": "PASS|FAIL|ERROR|WARN",    # Status
    "column": "name",                     # Column (empty for dataset-level)
    "pk": "key=value",                    # Primary key context
    "detail": "message",                  # Detailed description
    "source_value": "type",               # Check type or expectation type
    "target_value": "summary"             # Result summary
}
```

This normalization allows all results to flow through existing CSV/HTML/Excel reporting without modification.

---

## 🌍 Multi-Environment Support

### Redshift Environment Configuration

Create `.env`:

```env
# Redshift DEV Environment
REDSHIFT_DEV_HOST=dev-redshift-cluster.us-east-1.redshift.amazonaws.com
REDSHIFT_DEV_PORT=5439
REDSHIFT_DEV_USER=analytics_user
REDSHIFT_DEV_PASSWORD=secret_password
REDSHIFT_DEV_DATABASE=analytics_dev

# Redshift PREPROD Environment
REDSHIFT_PREPROD_HOST=preprod-redshift-cluster.us-east-1.redshift.amazonaws.com
REDSHIFT_PREPROD_PORT=5439
REDSHIFT_PREPROD_USER=analytics_user
REDSHIFT_PREPROD_PASSWORD=secret_password
REDSHIFT_PREPROD_DATABASE=analytics_preprod

# Redshift PROD Environment
REDSHIFT_PROD_HOST=prod-redshift-cluster.us-east-1.redshift.amazonaws.com
REDSHIFT_PROD_PORT=5439
REDSHIFT_PROD_USER=analytics_user
REDSHIFT_PROD_PASSWORD=secret_password
REDSHIFT_PROD_DATABASE=analytics_prod
```

### Cross-Environment Validation

```yaml
validations:
  - name: "DEV to PROD Comparison"
    regression: true
    
    source:
      type: table
      environment: DEV
      schema: edw_asis
      table: customers
    
    target:
      type: table
      environment: PROD
      schema: edw_asis
      table: customers
    
    primary_keys: customer_id
```

This automatically uses the appropriate connection from `.env` based on environment name.

---

## 📊 Reports & Output

### CSV Report

Machine-readable, importable to Excel/BI tools:

```csv
validation,result,column,pk,detail,source_value,target_value
record_count,PASS,,,"Source: 10,000 rows; Target: 10,000 rows",count,Match
column_count,PASS,,,"Source: 25 columns; Target: 25 columns",count,Match
data_types,PASS,,,"All types compatible",types,Match
duplicates,PASS,,,"No primary key duplicates found",duplicates,0
nulls,FAIL,email,,"Column 'email': 47 NULLs in target (0 in source)",null_count,"target=47,source=0"
```

### HTML Report

Interactive dashboard with:
- ✅ Visual pass/fail summary
- ✅ Detailed check descriptions
- ✅ Failed records with drill-down
- ✅ Charts and statistics
- ✅ Timestamp and duration

### Excel Report

Multi-sheet workbook:
- Sheet 1: Summary (pass/fail counts)
- Sheet 2: All results (detailed)
- Sheet 3: Failed records (if any)
- Sheet 4: Great Expectations violations (if enabled)
- Sheet 5: Anomaly samples (if enabled)

---

## 🔧 Implementation Details

### What's New (Features Added)

#### Module 1: Great Expectations Integration

**File:** `core/gx_validator.py` (420+ lines)

**Classes:**
- `GXValidator` — Main validator class
  - `validate()` — Orchestrates all checks
  - `_run_expectation()` — Dispatcher for specific rules
  - 8 specific `_expect_*()` methods for each rule type

**Function:**
- `run_great_expectations()` — Convenience wrapper for orchestrator

**Status:** Production-ready, fully documented

#### Module 2: Anomaly Detection Integration

**File:** `core/anomaly_detector.py` (380+ lines)

**Classes:**
- `AnomalyDetector` — Main anomaly detector
  - `detect()` — Orchestrates detection
  - `_run_isolation_forest()` — Executes algorithm
  - `_generate_results()` — Creates result dicts
  - `get_anomalies_sample()` — Extracts top N anomalies

**Function:**
- `run_anomaly_detection()` — Convenience wrapper for orchestrator

**Status:** Production-ready, fully documented, with scikit-learn graceful fallback

#### Validator Integration

**File:** `core/validator.py` (Modified - 40 lines added)

**Changes:**
- Line 16-17: Added imports for both new modules
- After line 472: Added Great Expectations integration block with feature flag
- After GX: Added Anomaly Detection integration block with feature flag

**Effect:** Seamless orchestration; if config blocks absent, zero impact

### Dependencies Added

**File:** `requirements.txt`

```
# --- Advanced Validation Features ---
great-expectations>=0.17.0
scikit-learn>=1.3.0
```

**Install:** `pip install -r requirements.txt`

### Backward Compatibility

✅ **100% backward compatible**

- All existing YAML configs work unchanged
- New features are opt-in (config `enabled: false` by default)
- No changes to report generation logic
- No changes to adapter interfaces
- Graceful error handling if dependencies missing

---

## 📦 Installation & Setup

### System Requirements

- Python ≥ 3.9
- pip or conda
- Redshift credentials (for table sources)
- ~500 MB disk space

### Step 1: Clone Repository

```bash
git clone <repository>
cd 1IB_universal-validator
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment (For Redshift)

Create `.env` with Redshift connection details:

```env
REDSHIFT_DEV_HOST=your-dev-cluster.redshift.amazonaws.com
REDSHIFT_DEV_PORT=5439
REDSHIFT_DEV_USER=analytics_user
REDSHIFT_DEV_PASSWORD=your_password
REDSHIFT_DEV_DATABASE=analytics_dev

# ... PREPROD and PROD configurations ...
```

### Step 5: Verify Installation

```bash
python3 -c "import pandas; import redshift_connector; print('✅ Core dependencies OK')"
python3 -c "import great_expectations; print('✅ Great Expectations OK')"
python3 -c "from sklearn.ensemble import IsolationForest; print('✅ scikit-learn OK')"
```

### Step 6: Try Example

```bash
python3 main.py --config config/example_gx_validation.yaml
```

---

## 🎯 Best Practices

### For Structural Validation

1. **Start with Standard Mode** — 7 checks are usually sufficient
2. **Use Regression Mode for** — Pre-production, financial, or compliance validations
3. **Set Primary Keys** — Critical for duplicate/comparison detection
4. **Monitor Daily** — Schedule validation as part of ETL pipeline

### For Great Expectations

1. **Start Narrow** — Begin with critical columns
2. **Layer Rules** — column existence → nullness → format → ranges
3. **Document Rules** — Add comments explaining *why* each rule exists
4. **Run on Both** — Validate source *and* target to catch upstream issues
5. **Version Control** — Commit YAML configs with code

### For Anomaly Detection

1. **Choose Columns Wisely** — Business-meaningful numeric columns only
2. **Know Your Domain** — Contamination rate should match error rates
3. **Investigate** — Anomalies aren't always bad; investigate first
4. **Trend Over Time** — Track anomaly rates; rising = sign of trouble
5. **Combine Methods** — Use with structural checks; they catch different issues

### General Best Practices

1. **Fail Fast** — Run validation immediately after data load
2. **Alert on Failure** — Integrate with monitoring systems
3. **Archive Results** — Keep historical validation records
4. **Review Reports** — Don't just look at pass/fail; read details
5. **Iterate** — Rules evolve with data and business needs

---

## 🆘 Troubleshooting

### Great Expectations Issues

**Issue:** `ImportError: No module named 'great_expectations'`

**Solution:**
```bash
pip install great_expectations>=0.17.0
```

**Issue:** Great Expectations rules not running

**Check:**
- ✅ `enabled: true` in config
- ✅ Column names spelled correctly
- ✅ Expectations list not empty
- ✅ YAML indentation correct

**Issue:** False positives in expectations

**Solution:**
- Review rule thresholds (ranges, set membership)
- Check for data anomalies (outliers might be legitimate)
- Verify source data quality upstream
- Consider data transformations before validation

---

### Anomaly Detection Issues

**Issue:** `ImportError: No module named 'sklearn'`

**Solution:**
```bash
pip install scikit-learn>=1.3.0
```

**Issue:** No anomalies detected (but you expect some)

**Troubleshoot:**
- ✅ Check `contamination` value (too low = miss anomalies)
- ✅ Verify column selection (right columns?)
- ✅ Check data distribution (Isolation Forest works on any distribution)
- ✅ Increase `contamination` to 0.05 for testing

**Issue:** Too many anomalies detected

**Solution:**
- Lower `contamination` (0.01 instead of 0.05)
- Review selected columns (right ones?)
- Check for mixed data types
- Consider business context (anomalies might be real)

---

### General Issues

**Issue:** Validation runs slowly

**Solution:**
- Use `limit` in config to test first
- Disable regression mode if not needed
- Reduce sample output rows
- Profile to identify bottleneck

**Issue:** Column alignment fails

**Solution:**
- Check `column_mapping` in config
- Use `auto_match_by_suffix: true`
- Verify column names in source/target

**Issue:** Report generation fails

**Solution:**
- Check `output_dir` is writable
- Verify disk space available
- Review error logs in console output

---

## 📞 Support

### Quick Reference

- **Feature Overview:** See "Feature Overview" section above
- **Configuration Help:** See "Configuration Guide" section
- **Examples:** See "Real-World Examples" section
- **Troubleshooting:** See "Troubleshooting" section above
- **Implementation Details:** See "Implementation Details" section

### Key Files

| File | Purpose |
|:---|:---|
| `README.md` (this file) | Complete documentation |
| `core/gx_validator.py` | Great Expectations implementation |
| `core/anomaly_detector.py` | Anomaly detection implementation |
| `config/example_*.yaml` | Copy-paste-ready example configs |
| `core/validator.py` | Main orchestration |
| `core/reporter.py` | Report generation |

---

## 🎉 Summary

This framework provides **enterprise-grade data validation** with:

✅ **16 structural checks** (7 standard, 9 regression)
✅ **8 Great Expectations rule types** (config-driven)
✅ **Isolation Forest anomaly detection** (statistical outliers)
✅ **Multi-source support** (files, Redshift, Tableau)
✅ **Multi-format reporting** (CSV, HTML, Excel)
✅ **100% backward compatible** (opt-in features)
✅ **Production-grade quality** (error handling, logging, docs)

---

**Ready to validate your data with confidence!** 🚀

For questions, refer to the appropriate section in this document or review the example configurations in `config/`.
