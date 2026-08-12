"""Dump the app's OpenAPI schema deterministically (sorted keys) for contract diffs."""

import json
import sys

from app.main import app

json.dump(app.openapi(), sys.stdout, sort_keys=True, ensure_ascii=False, indent=1)
sys.stdout.write("\n")
