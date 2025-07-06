#!/usr/bin/env python
from pyzotero import zotero
import datetime
import io
import sys
import re
from config import ZOTERO_CONFIGS

def main():
    zot_config = ZOTERO_CONFIGS["SearchNotes"]
    user_id = zot_config["userID"]
    secret_key = zot_config["secretKey"]
    file_path = zot_config["filePath"]
    default_query = zot_config["searchQuery"]

    # Use CLI argument if provided, else fallback to config
    search_query = sys.argv[1] if len(sys.argv) > 1 else default_query

    zot = zotero.Zotero(user_id, 'user', secret_key, preserve_json_order=True)

    search_result = zot.top(q=search_query, qmode="everything")
    # Remove stray itemtypes 'attachment'
    search_result = [item for item in search_result if item['data']['itemType'] != 'attachment']

    note_items = []
    for item in search_result:
        for child in zot.children(item['key']):
            if "note" in child['data']['itemType']:
                note_items.append(child['data'])

    # Remove notes with 'the following values have no...'
    note_items = [n for n in note_items if not n['note'].startswith('The following values')]

    # Build collection keys
    collections_info = zot.collections()
    collections_list_keys = {
        col['data']['key']: {
            'Name': col['data']['name'],
            'Parent': col['data']['parentCollection']
        }
        for col in collections_info
    }

    notes = []
    for note in note_items:
        notes_raw = note['note']
        if notes_raw.startswith('<p><strong>Extracted Annotations') or notes_raw.startswith('<p><b>Extracted Annotations'):
            parent_id = note['parentItem']
            parent_doc = zot.item(parent_id)
            match = re.search(r"(?<!\d)\d{4,20}(?!\d)", parent_doc['data']['date'])
            parent_date = match.group(0) if match else ""
            collection_id = parent_doc['data']['collections'][0]
            collection_parent_id = collections_list_keys[collection_id]['Parent']
            if collection_parent_id and str(collection_parent_id) in collections_list_keys:
                parent_collection_name = collections_list_keys[collection_parent_id]['Name']
                bread_crumb = parent_collection_name + "/" + collections_list_keys[collection_id]['Name']
                collection_title = parent_collection_name
            else:
                bread_crumb = collections_list_keys[collection_id]['Name']
                collection_title = bread_crumb
            parent_title = parent_doc['data']['title']
            parent_creators = parent_doc['meta']['creatorSummary']
            if not notes_raw:
                package = "\\i No Notes"
            else:
                package = (
                    "\\i " + bread_crumb + "\\i0 \\line " +
                    "\\fs28 \\b " + parent_title + " (" + parent_date + ") \\b0 \\fs22 \\line " +
                    parent_creators + " \\line \\fs24 " + notes_raw
                )
            notes.append(package)

    output = "\\par".join(notes)
    # RTF and character replacements
    output = output.replace("(<a href=", "{\\field{\\*\\fldinst { HYPERLINK")
    output = output.replace("\">", "}}{\\fldrslt {")
    output = output.replace("</a>)", "}}}")
    output = output.replace("<p>", "\\line")
    output = output.replace("</p>", "\\line")
    output = output.replace("<strong>", "\\b ")
    output = output.replace("</strong>", " \\b0")
    output = output.replace("\u02d8", "&#728;")
    output = output.replace("\u02C7", "&#728;")

    timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
    rtf = (
        "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deftab720{\\fonttbl{\\f0\\fswiss MS Sans Serif;}"
        "{\\f1\\froman\\fcharset2 Symbol;}{\\f2\\fmodern\\fprq1 Courier New;}"
        "{\\f3\\froman Times New Roman;}}{\\colortbl\\red0\\green0\\blue0;"
        "\\red0\\green0\\blue255;\\red255\\green0\\blue0;}\\deflang1033\\horzdoc{\\*\\fchars }{\\*\\lchars}"
    )
    with io.open(f"{file_path}{search_query}_Zotero_notes_{timestamp}.rtf", 'w+', encoding="cp1252") as f:
        f.write(rtf)
        f.write(output + "\\par")
        f.write("}")

if __name__ == "__main__":
    main()