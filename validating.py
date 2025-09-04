import json
import fastjsonschema
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
schema_path = os.path.join(BASE_DIR, "index_Schema.json")
output_path = os.path.join(BASE_DIR, "index.json")

# Load schema
with open(schema_path, "r", encoding="utf-8") as f:
    schema = json.load(f)

# Compile validator
validate = fastjsonschema.compile(schema)

# Load output
with open(output_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Validate
try:
    validate(data)
    print("✅ Output matches the schema")
except Exception as e:
    print("❌ Schema validation failed:")
    print(e)
