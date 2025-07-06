import os
import datetime
import io
import sys
import re
from pyzotero import zotero, zotero_errors
from config import ZOTERO_CONFIGS

def rtf_replace(text):
    return (text.replace("(<a href=", "{\\field{\\*\\fldinst { HYPERLINK")
                .replace("\">", "}}{\\fldrslt {")
                .replace("</a>)", "}}}")
                .replace("<p>", "\\line")
                .replace("</p>", "\\line")
                .replace("<strong>", "\\b ")
                .replace("</strong>", " \\b0")
                .replace("\u02d8", "&#728;")
                .replace("\u02C7", "&#728;"))

def main():
    try:
        zot_config = ZOTERO_CONFIGS["SearchNotes"]
        user_id = zot_config["userID"]
        secret_key = zot_config["secretKey"]
        file_path = zot_config["filePath"]
        default_query = zot_config["searchQuery"]
        search_query = sys.argv[1] if len(sys.argv) > 1 else default_query

        zot = zotero.Zotero(user_id, 'user', secret_key, preserve_json_order=True)
        try:
            search_result = [item for item in zot.top(q=search_query, qmode="everything")
                             if item['data']['itemType'] != 'attachment']
        except zotero_errors.PyZoteroError as e:
            print(f"Error fetching top-level items: {e}")
            return

        note_items = []
        parent_ids = set()
        for item in search_result:
            try:
                for child in zot.children(item['key']):
                    if "note" in child['data']['itemType']:
                        note_items.append(child['data'])
                        parent_ids.add(child['data']['parentItem'])
            except zotero_errors.PyZoteroError as e:
                print(f"Error fetching children for item {item['key']}: {e}")

        note_items = [n for n in note_items if not n['note'].startswith('The following values')]

        try:
            parent_items = zot.items(itemKeys=list(parent_ids))
        except zotero_errors.PyZoteroError as e:
            print(f"Error fetching parent items: {e}")
            return
        parent_lookup = {item['key']: item for item in parent_items}

        try:
            collections_info = zot.collections()
        except zotero_errors.PyZoteroError as e:
            print(f"Error fetching collections: {e}")
            return
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
                parent_doc = parent_lookup.get(note['parentItem'])
                if not parent_doc:
                    continue
                match = re.search(r"(?<!\d)\d{4,20}(?!\d)", parent_doc['data']['date'])
                parent_date = match.group(0) if match else ""
                collection_id = parent_doc['data']['collections'][0]
                collection_parent_id = collections_list_keys[collection_id]['Parent']
                if collection_parent_id and str(collection_parent_id) in collections_list_keys:
                    parent_collection_name = collections_list_keys[collection_parent_id]['Name']
                    bread_crumb = parent_collection_name + "/" + collections_list_keys[collection_id]['Name']
                else:
                    bread_crumb = collections_list_keys[collection_id]['Name']
                parent_title = parent_doc['data']['title']
                parent_creators = parent_doc['meta']['creatorSummary']
                package = (
                    "\\i " + bread_crumb + "\\i0 \\line " +
                    "\\fs28 \\b " + parent_title + " (" + parent_date + ") \\b0 \\fs22 \\line " +
                    parent_creators + " \\line \\fs24 " + notes_raw
                ) if notes_raw else "\\i No Notes"
                notes.append(package)

        output = "\\par".join(notes)
        output = rtf_replace(output)

        timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
        out_path = os.path.join(file_path, f"{search_query}_Zotero_notes_{timestamp}.rtf")
        rtf = (
            "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deftab720{\\fonttbl{\\f0\\fswiss MS Sans Serif;}"
            "{\\f1\\froman\\fcharset2 Symbol;}{\\f2\\fmodern\\fprq1 Courier New;}"
            "{\\f3\\froman Times New Roman;}}{\\colortbl\\red0\\green0\\blue0;"
            "\\red0\\green0\\blue255;\\red255\\green0\\blue0;}\\deflang1033\\horzdoc{\\*\\fchars }{\\*\\lchars}"
        )
        try:
            with io.open(out_path, 'w+', encoding="utf-8", errors="replace") as f:
                f.write(rtf)
                f.write(output + "\\par")
                f.write("}")
            print(f"Output file written successfully: {out_path}")
        except (IOError, OSError) as e:
            print(f"Error writing output file: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()