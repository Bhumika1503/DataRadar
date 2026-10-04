#  Data Radar

> A lightweight data engineering platform for file ingestion, data profiling, quality validation, source-to-target mapping, and schema drift detection.

Data Radar is a Streamlit-based data engineering project that brings common data preparation and validation tasks into one simple interface.

The project focuses on five core capabilities:

-  Unstructured File → Database
-  Source-to-Target Mapper
-  Data Profiler
-  Data Quality Rule Generator
-  Schema Drift Detector

---

##  Features

###  1. Unstructured File → Database

Data Radar allows users to upload common business data files and extract their contents into structured data.

**Supported formats:**

- CSV
- Excel (`.xlsx`)
- PDF
- Word (`.docx`)
- Text (`.txt`)

The extracted data can be previewed and stored in PostgreSQL.

---

###  2. Source-to-Target Mapper

Automatically suggests mappings between source columns and a target PostgreSQL table.

For example:

| Source Column | Target Column |
|---|---|
| `cust_name` | `customer_name` |
| `email_id` | `email` |
| `phone_no` | `phone` |

The mapper uses:

- Column-name similarity
- Common naming patterns
- Data type comparison
- Confidence scoring

Users can review and approve the suggested mappings before generating the target-ready dataset.

---

###  3. Data Profiler

Provides a quick overview of the structure and quality of a dataset.

The profiler analyzes:

- Total rows
- Total columns
- Missing values
- Duplicate rows
- Data types
- Unique values
- Sample values
- Numeric statistics

Example:

```text
Rows              10,000
Columns                8
Missing Cells         342
Duplicate Rows         17
```

---

###  4. Data Quality Rule Generator

Generates basic data quality rules based on the dataset structure and column names.

Examples:

```text
customer_id  → NOT NULL
customer_id  → UNIQUE
email        → Valid Email
age          → 0–120
amount       → >= 0
date         → Valid Date
```

Users can review and approve the generated rules before execution.

The validation process identifies records that fail the selected quality rules.

---

###  5. Schema Drift Detector

Compares two versions of a dataset and identifies structural changes.

It detects:

- ➕ Added columns
- ➖ Removed columns
- 🔄 Changed data types

Example:

```text
Previous Dataset:

id
name
age


Current Dataset:

id
name
age
email
```

Result:

```text
Added Column:
email
```

---

#  Architecture

```text
                              ┌──────────────────────┐
                              │      DATA RADAR      │
                              │      Streamlit       │
                              └──────────┬───────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
             File Extraction       Data Analysis       Data Validation
                    │                    │                    │
                    │          ┌─────────┴─────────┐     ┌────┴─────┐
                    │          │                   │     │          │
                    ▼          ▼                   ▼     ▼          ▼
              CSV / XLSX   Data Profiler   Source-to-Target  Quality  Schema
              PDF / DOCX                      Mapper           Rules   Drift
              TXT
                    │
                    ▼
              PostgreSQL
```

---

#  Application Workflow

```text
                         ┌───────────────┐
                         │  Upload File  │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │ File Extraction│
                         └───────┬───────┘
                                 │
                                 ▼
                       ┌────────────────────┐
                       │ Structured Dataset │
                       └─────────┬──────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             │                   │                   │
             ▼                   ▼                   ▼
      ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
      │Data Profiler│    │Quality Rules│    │Source-Target│
      └─────────────┘    └─────────────┘    │   Mapper    │
                                             └──────┬──────┘
                                                    │
                                                    ▼
                                            Target-Ready Data

                                 +
                                 │
                                 ▼
                         ┌───────────────┐
                         │ Schema Drift  │
                         │ Old ↔ Current │
                         └───────────────┘

                                 │
                                 ▼
                           ┌───────────┐
                           │PostgreSQL │
                           └───────────┘
```

---

#  Tech Stack

| Technology | Purpose |
|---|---|
| **Python** | Core programming language |
| **Streamlit** | Web application interface |
| **Pandas** | Data processing and analysis |
| **PostgreSQL** | Database |
| **SQLAlchemy** | Database connectivity |
| **Psycopg** | PostgreSQL driver |
| **PyMuPDF** | PDF extraction |
| **python-docx** | Word document extraction |
| **OpenPyXL** | Excel processing |

---

#  Project Structure

```text
DataRadar/
│
├──  app.py
│
├──  agents/
│   ├── __init__.py
│   ├── profiler_agent.py
│   └── quality_agent.py
│
├──  core/
│   ├── __init__.py
│   ├── database.py
│   ├── file_extractor.py
│   ├── rule_executor.py
│   ├── schema_drift.py
│   └── source_target_mapper.py
│
├──  pages/
│   ├── File_Upload.py
│   ├── Data_Profiler.py
│   ├── Quality_Rules.py
│   ├── Schema_Drift.py
│   └── Source_Target_Mapper.py
│
├──  .streamlit/
│   └── secrets.toml
│
├──  requirements.txt
├──  .gitignore
└──  README.md
```

### Directory Responsibilities

| Directory / File | Responsibility |
|---|---|
| `app.py` | Main Streamlit application |
| `agents/` | Dataset profiling and quality-rule generation |
| `core/` | Core extraction, database, mapping, validation, and schema logic |
| `pages/` | Streamlit module interfaces |
| `.streamlit/` | Application secrets and configuration |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Files excluded from Git |
| `README.md` | Project documentation |

---

#  Installation

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/DataRadar.git
cd DataRadar
```

## 2. Create a Virtual Environment

### Windows

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

#  Requirements

The project uses:

```text
streamlit
pandas
openpyxl
pymupdf
python-docx
sqlalchemy
psycopg[binary]
```

---

#  PostgreSQL Setup

Create the database:

```sql
CREATE DATABASE data_radar;
```

Connect to the `data_radar` database and create the staging schema:

```sql
CREATE SCHEMA IF NOT EXISTS staging;
```

Create the upload tracking table:

```sql
CREATE TABLE IF NOT EXISTS staging.file_uploads (
    upload_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    column_count INTEGER NOT NULL DEFAULT 0,
    uploaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

Create the extracted records table:

```sql
CREATE TABLE IF NOT EXISTS staging.extracted_records (
    record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    upload_id BIGINT NOT NULL
        REFERENCES staging.file_uploads(upload_id)
        ON DELETE CASCADE,
    source_table INTEGER NOT NULL DEFAULT 0,
    row_number INTEGER NOT NULL,
    record_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

Create the upload index:

```sql
CREATE INDEX IF NOT EXISTS idx_records_upload
ON staging.extracted_records(upload_id);
```

---

# 🔐 Database Configuration

Create the following file:

```text
.streamlit/secrets.toml
```

Add:

```toml
DATABASE_URL = "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/data_radar"
```

Replace `YOUR_PASSWORD` with your PostgreSQL password.

### ⚠️ Important

Never commit your real database credentials to GitHub.

Add the following to `.gitignore`:

```text
.streamlit/secrets.toml
.venv/
__pycache__/
*.pyc
```

---

# ▶️ Run the Application

Start Data Radar using:

```bash
streamlit run app.py
```

The application will open in your browser.

---
#  Project Scope

Data Radar intentionally focuses on five practical data-engineering tasks:

1. **Unstructured File → Database**
2. **Source-to-Target Mapper**
3. **Data Profiler**
4. **Data Quality Rule Generator**
5. **Schema Drift Detector**

The project does not currently attempt to provide:

- OCR pipelines
- PII discovery
- Entity resolution
- Advanced duplicate detection
- Data cataloging
- Authentication systems
- Workflow orchestration
- Complex ML-based data quality systems

Keeping the scope focused makes the project:

- Lightweight
- Easy to understand
- Easy to demonstrate
- Easy to maintain
- Suitable for a data-engineering portfolio

---

#  Testing

Test the core modules individually.

### File Extractor

```bash
python -c "from core.file_extractor import extract_file; print('File extractor OK')"
```

### Data Profiler

```bash
python -c "from agents.profiler_agent import profile_dataset; print('Profiler OK')"
```

### Quality Agent

```bash
python -c "from agents.quality_agent import generate_rules; print('Quality agent OK')"
```

### Rule Executor

```bash
python -c "from core.rule_executor import execute_rules; print('Rule executor OK')"
```

### Source-to-Target Mapper

```bash
python -c "from core.source_target_mapper import generate_mappings; print('Mapper OK')"
```

### Schema Drift Detector

```bash
python -c "from core.schema_drift import compare_schemas; print('Schema drift OK')"
```

### Database Connection

```bash
python -c "from core.database import test_connection; print('Database:', test_connection())"
```

---

#  Deployment

Data Radar can be deployed using Streamlit Community Cloud or another Python-compatible hosting platform.

Recommended architecture:

```text
                 GitHub
                    │
                    ▼
          Streamlit Community Cloud
                    │
                    ▼
               Data Radar
                    │
                    ▼
            Cloud PostgreSQL
```

For cloud deployment, the PostgreSQL connection string should be provided through deployment secrets rather than hard-coded into the application.

---

#  Security

The project uses Streamlit secrets for database credentials.

Sensitive files should never be committed:

```text
.streamlit/secrets.toml
```

For production deployment, use environment-specific credentials and a managed PostgreSQL database.

---

#  Future Improvements

Possible future improvements include:

- Additional file formats
- More data quality rules
- Improved mapping suggestions
- Additional database connectors
- Automated schema comparison
- Cloud deployment
- Improved reporting and visualization

These improvements can be added independently without changing the core architecture.

---

#  Why Data Radar?

Data engineering workflows often involve repetitive steps:

```text
Raw Files
    ↓
Extraction
    ↓
Profiling
    ↓
Quality Checks
    ↓
Mapping
    ↓
Database
```

Data Radar brings these tasks into one lightweight interface, allowing users to inspect, validate, map, and prepare data before it reaches downstream systems.

The goal is not to replace a complete enterprise data platform, but to provide a simple and explainable solution for common data-engineering tasks.

---

#  Author

**Bhumika Chauhan**

Data Engineering Project

---

#  License

This project is intended for educational and portfolio purposes.