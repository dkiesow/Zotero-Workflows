#!/usr/bin/env python
import config as cfg
from pyzotero import zotero
import json

userID = cfg.zotCollectionNotes["userID"]
secretKey = cfg.zotCollectionNotes["secretKey"]
filePath = cfg.zotCollectionNotes["filePath"]

zot = zotero.Zotero(userID, 'user', secretKey, 'preserve_json_order = true')
# we now have a Zotero object, zot, and access to all its methods

# create a list of collection keys
collectionsInfo = zot.collections()
items = []

res = [sub['data']['name'] for sub in collectionsInfo]

i = 0
for i in range(len(res)):
    items.append({"uid": res[i], "title": res[i], "arg": res[i], "subtitle": u'↩ or ⇥ to select',
                  "autocomplete": res[i]})
out = json.dumps(items, sort_keys=True, indent=4)
export = "{\"items\":" + out + "}"
print(export)
