import os
import re
import json
import chardet  # pip install chardet

# ---------------- Helpers ----------------

def read_file_with_encoding(file_path):
    with open(file_path, "rb") as f:
        raw = f.read()
    enc = chardet.detect(raw).get("encoding") or "utf-8"
    return raw.decode(enc, errors="ignore")

def strip_sql_comments(s: str) -> str:
    s = re.sub(r"/\*[\s\S]*?\*/", "", s)  # block comments
    s = re.sub(r"--.*?$", "", s, flags=re.MULTILINE)  # line comments
    return s

def find_as_split(text: str) -> str:
    m = re.search(r"\bAS\b", text, flags=re.IGNORECASE)
    return text[:m.start()] if m else text

def norm_name(name: str) -> str:
    return name.replace("[", "").replace("]", "").strip()

# ---------------- Core extractors ----------------

def extract_params(header_text: str):
    params = []
    m = re.search(r"\(([\s\S]*?)\)", header_text)
    if not m:
        return params
    param_text = m.group(1).strip()
    if not param_text:
        return params
    parts = re.split(r',\s*(?![^(]*\))', param_text)
    for p in parts:
        p = p.strip().rstrip(",;")
        if not p:
            continue
        pm = re.match(r'(@[\w]+)\s+([\w\(\)]+)', p)
        if not pm:
            continue
        name = pm.group(1)
        type_raw = pm.group(2).upper()

        # --- preserve exact SQL type ---
        if type_raw.startswith("DECIMAL"):
            typ = "DECIMAL"
        elif type_raw.startswith("NUMERIC"):
            typ = "NUMERIC"
        elif type_raw == "INT":
            typ = "INT"
        elif type_raw == "INTEGER":
            typ = "INTEGER"
        elif type_raw == "BIGINT":
            typ = "BIGINT"
        elif type_raw == "SMALLINT":
            typ = "SMALLINT"
        elif type_raw == "TINYINT":
            typ = "TINYINT"
        elif type_raw.startswith("CHAR"):
            typ = "CHAR"
        elif type_raw.startswith("NCHAR"):
            typ = "NCHAR"
        elif type_raw.startswith("VARCHAR"):
            typ = "VARCHAR"
        elif type_raw.startswith("NVARCHAR"):
            typ = "NVARCHAR"
        elif type_raw.startswith("TEXT"):
            typ = "TEXT"
        elif type_raw.startswith("BIT"):
            typ = "BIT"
        else:
            typ = type_raw.split("(")[0]

        params.append({"name": name, "type": typ})

    # ✅ sort params alphabetically by name
    params.sort(key=lambda x: x["name"].lower())
    return params

def extract_calls(body: str):
    calls = list(set(re.findall(r"\b(?:EXEC(?:UTE)?|CALL)\s+([\[\]\w\.]+)", body, re.IGNORECASE)))
    return sorted([norm_name(c) for c in calls], key=str.lower)

def extract_tables(body: str):
    table_pattern = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE|DELETE\s+FROM)\s+([\[\]\w\.#]+)", re.IGNORECASE)
    raw_tables = table_pattern.findall(body)
    cleaned, seen = [], set()
    skip = {"log", "the", "select", "set", "values", "where", "if", "begin", "end",
            "as", "inserted", "deleted", "output", "with", "top"}
    for t in raw_tables:
        t = norm_name(t)
        if t and t.lower() not in skip and not re.search(r"(cursor$|^cur_)", t, re.IGNORECASE):
            if t not in seen:
                cleaned.append(t)
                seen.add(t)
    return sorted(cleaned, key=str.lower)

def extract_return_type(body: str):
    m = re.search(r"\bRETURNS\s+([\w@]+(?:\s+TABLE)?)", body, re.IGNORECASE)
    if not m:
        return None
    return m.group(1).upper()

def extract_metadata(block: str):
    objects = {"procedures": {}, "functions": {}, "triggers": {}, "views": {}, "tables": {}}
    original = block
    body = strip_sql_comments(block)

    # Procedures
    for m in re.finditer(r"\bCREATE\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\s+([\[\]\w\.]+)", body, re.IGNORECASE):
        name = norm_name(m.group(1))
        header = find_as_split(original[m.start():])
        params = extract_params(header)
        calls = extract_calls(body)
        tables = extract_tables(body)
        objects["procedures"][name] = {"params": params, "calls": calls, "tables": tables}

    # Functions
    for m in re.finditer(r"\bCREATE\s+(?:OR\s+ALTER\s+)?FUNCTION\s+([\[\]\w\.]+)", body, re.IGNORECASE):
        name = norm_name(m.group(1))
        header = find_as_split(original[m.start():])
        params = extract_params(header)
        returns = extract_return_type(body)
        calls = extract_calls(body)
        tables = extract_tables(body)
        objects["functions"][name] = {"params": params, "returns": returns, "calls": calls, "tables": tables}

    # Triggers
    for m in re.finditer(r"\bCREATE\s+(?:OR\s+ALTER\s+)?TRIGGER\s+([\[\]\w\.]+)", body, re.IGNORECASE):
        name = norm_name(m.group(1))
        onm = re.search(r"\bON\s+([\[\]\w\.]+)", body[m.end():], re.IGNORECASE)
        table_on = norm_name(onm.group(1)) if onm else None
        events = sorted(set(e.upper() for e in re.findall(r"\b(INSERT|UPDATE|DELETE)\b", body[m.end():], re.IGNORECASE)))
        calls = extract_calls(body)
        tables = extract_tables(body)
        objects["triggers"][name] = {
            "on_table": table_on,
            "event": ", ".join(events),
            "calls": calls,
            "tables": tables
        }

    # Views
    for m in re.finditer(r"\bCREATE\s+(?:OR\s+ALTER\s+)?VIEW\s+([\[\]\w\.]+)", body, re.IGNORECASE):
        name = norm_name(m.group(1))
        tables = extract_tables(body)
        objects["views"][name] = {"tables": tables}

    # Tables
    for m in re.finditer(r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([\[\]\w\.]+)", body, re.IGNORECASE):
        name = norm_name(m.group(1))
        objects["tables"][name] = {}

    return objects

# ---------------- Processing ----------------

def merge_dicts(main, new):
    for key in main:
        main[key].update(new.get(key, {}))
    return main

def process_sql_file(path: str):
    idx = {"procedures": {}, "functions": {}, "triggers": {}, "views": {}, "tables": {}}
    content = read_file_with_encoding(path)
    blocks = re.split(r"^\s*GO\s*;?\s*$", content, flags=re.IGNORECASE | re.MULTILINE)
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        meta = extract_metadata(b)
        idx = merge_dicts(idx, meta)
    return idx

def process_sql_folder(folder: str):
    index = {"procedures": {}, "functions": {}, "triggers": {}, "views": {}, "tables": {}}
    for root, _, files in os.walk(folder):
        for fn in files:
            if not fn.lower().endswith(".sql"):
                continue
            fp = os.path.join(root, fn)
            try:
                found = process_sql_file(fp)
                if found:
                    print(f"• {fn}: objects found")
                    index = merge_dicts(index, found)
                else:
                    print(f"• {fn}: no objects found")
            except Exception as e:
                print(f"!! Failed {fp}: {e}")
    return index

# ---------------- Main ----------------

if __name__ == "__main__":
    path = r"C:\Users\OmPrakashJha\OneDrive - McLaren Strategic Solutions US Inc\Documents\BlogPlatformDB-main\SqlScripts"

    index = process_sql_folder(path)

    # ✅ Sort alphabetically inside each section
    sorted_index = {k: dict(sorted(v.items())) for k, v in index.items()}

    with open("index.json", "w", encoding="utf-8") as f:
        json.dump(sorted_index, f, indent=2)

    print("\n✅ index.json generated successfully.")
    print(f"- Procedures: {len(index['procedures'])}")
    print(f"- Functions: {len(index['functions'])}")
    print(f"- Triggers: {len(index['triggers'])}")
    print(f"- Views: {len(index['views'])}")
    print(f"- Tables: {len(index['tables'])}")
