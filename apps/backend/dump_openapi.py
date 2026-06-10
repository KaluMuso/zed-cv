import yaml, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.main import app
schema = app.openapi()
with open("../../docs/openapi.yaml", "w", encoding="utf-8") as f:
    yaml.dump(schema, f, sort_keys=False, allow_unicode=True)
