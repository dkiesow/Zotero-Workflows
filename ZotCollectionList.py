#!/usr/bin/env python
from pyzotero import zotero
import json
from config import ZOTERO_CONFIGS

def safe_utf8(s):
    try:
        return str(s).encode('utf-8', errors='replace').decode('utf-8')
    except Exception:
        return ''

def main():
    zot_config = ZOTERO_CONFIGS["CollectionList"]
    user_id = zot_config["userID"]
    secret_key = zot_config["secretKey"]

    zot = zotero.Zotero(user_id, 'user', secret_key, preserve_json_order=True)
    collections_info = zot.collections()

    items = [
        {
            "uid": safe_utf8(col['data']['name']),
            "title": safe_utf8(col['data']['name']),
            "arg": safe_utf8(col['data']['name']),
            "subtitle": u'↩ or ⇥ to select',
            "autocomplete": safe_utf8(col['data']['name'])
        }
        for col in collections_info
    ]

    export = json.dumps({"items": items}, sort_keys=True, indent=4, ensure_ascii=False)
    print(export)

if __name__ == "__main__":
    main()