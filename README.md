
---

# 📘 Tool 1: Sybase Stored Procedure Indexer

## 📌 Objectives

* Automate extraction of metadata from Sybase SQL scripts.
* Identify **procedures, functions, triggers, views, and tables**.
* Generate a **structured JSON (index.json)** for lineage and dependency analysis.

---

## 🛠️ Technology Involved

* **Python 3.13**
* **Regex parsing** for SQL pattern detection
* **Chardet** for encoding detection
* **FastJSONSchema** for schema validation
* **JSON** for structured output

---

## ⚙️ Tools Used

* **Visual Studio Code** – Development & debugging
* **GitHub** – Version control & repo management
* **Python Libraries**:

  * `re` – regex parsing
  * `json` – output handling
  * `chardet` – file encoding detection
  * `fastjsonschema` – schema validation

---

## 🚀 How to Run

### 1. Clone Repo

```bash
git clone <your-repo-link>
cd sybase-sp-indexer
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Indexer

```bash
python indexer.py
```

### 4. Validate Output

```bash
python validating.py
```

---

## 📂 Input

* SQL scripts (procedures, functions, triggers, views, tables).
* Example folder: `SqlScripts/`.

---

## 📜 Output

* `index.json` generated with schema:

```json
{
  "procedures": { ... },
  "functions": { ... },
  "triggers": { ... },
  "views": { ... },
  "tables": { ... }
}
```

---

## ✅ Benefits

* Saves time by automating manual SQL documentation.
* Standardized JSON for integration with other tools.
* Easy schema validation ensures accuracy.
* Helps in **data lineage, impact analysis, and migration projects**.

---

## ⚡ Challenges & Learnings

* Handling multiple encodings in SQL files → solved using `chardet`.
* Extracting parameters, return types, and tables using regex.
* Ensuring schema compliance with `fastjsonschema`.
* Iterative debugging to support **procedures, functions, triggers, and views**.

---

## 🤖 AI / LLM Leverage

* Used LLM support for **regex refinement, schema design, and debugging**.
* Helped speed up **pattern recognition** and ensured **consistent documentation**.

---
