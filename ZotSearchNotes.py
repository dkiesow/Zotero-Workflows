#!/usr/bin/env python
import sys
import io
import re
import datetime
from pyzotero import zotero
from config import ZOTERO_CONFIGS
from charset_normalizer import from_bytes
import unicodedata

def get_config():
    config = ZOTERO_CONFIGS["SearchNotes"]
    user_id = config["userID"]
    secret_key = config["secretKey"]
    file_path = config["filePath"]
    search_query = config["searchQuery"]
    # Allow override from command line
    if len(sys.argv) > 1:
        search_query = sys.argv[1]
    return user_id, secret_key, file_path, search_query

def detect_and_normalize(text):
    import unicodedata
    # Only detect encoding if input is bytes
    if isinstance(text, bytes):
        from charset_normalizer import from_bytes
        result = from_bytes(text).best()
        if result is not None:
            decoded = str(result)
        else:
            decoded = text.decode('utf-8', errors='replace')
        normalized = unicodedata.normalize('NFC', decoded)
        return normalized
    # If already str, just normalize
    return unicodedata.normalize('NFC', text)

def clean_note_text(text):
    # Remove BOM if present
    if text.startswith('\ufeff'):
        text = text[1:]
    text = detect_and_normalize(text)
    replacements = {
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-",
        "\u2026": "...", "\u00a0": " ",
        "\u02d8": "^", "\u02c7": "ˇ",
        "\u2010": "-", "\u00b7": ".",
        "\u2212": "-", "\u00e9": "e",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text

def rtf_replace(text):
    return (text.replace("(<a href=", "{\\field{\\*\\fldinst { HYPERLINK")
                .replace("\">", "}}{\\fldrslt {")
                .replace("</a>)", "}}}")
                .replace("<p>", "\\line")
                .replace("</p>", "\\line")
                .replace("<strong>", "\\b ")
                .replace("</strong>", " \\b0")
                .replace("\u02d8", "&#728;")
                .replace("&amp;", "&")
                .replace("\u02C7", "&#728;"))

def main():
    user_id, secret_key, file_path, search_query = get_config()
    zot = zotero.Zotero(user_id, 'user', secret_key, preserve_json_order=True)

    # Fetch collections and build lookup
    collections_info = zot.collections()
    collections_lookup = {
        col['data']['key']: {
            'Name': col['data']['name'],
            'Parent': col['data']['parentCollection']
        }
        for col in collections_info
    }

    # Search for top-level items (excluding attachments)
    search_result = [
        item for item in zot.top(q=search_query, qmode="everything")
        if item['data']['itemType'] != 'attachment'
    ]

    # Gather annotation notes from children
    annotation_notes = []
    for item in search_result:
        children = zot.children(item['key'])
        for child in children:
            note_data = child['data']
            if (
                    note_data['itemType'] == 'note' and (
                    note_data['note'].startswith('<p><strong>Extracted Annotations') or
                    note_data['note'].startswith('<p><b>Extracted Annotations') or
                    note_data['note'].startswith('<p><b>Annotations') or
                    note_data['note'].startswith('<p>Annotations')
            )
            ):
                annotation_notes.append(note_data)

    notes = []
    for note in annotation_notes:
        notes_raw = clean_note_text(note['note'])
        parent_id = note['parentItem']
        parent_doc = zot.item(parent_id)
        parent_data = parent_doc['data']
        parent_title = parent_data.get('title', '[No Title]')
        parent_creators = parent_doc['meta'].get('creatorSummary', '')
        # Extract year or date
        match = re.search(r"(?<!\d)\d{4,20}(?!\d)", parent_data.get('date', ''))
        parent_date = match.group(0) if match else ""
        # Collection breadcrumb
        collections = parent_data.get('collections', [])
        if collections:
            collection_id = collections[0]
            collection_info = collections_lookup.get(collection_id, {})
            parent_collection_id = collection_info.get('Parent')
            if parent_collection_id and parent_collection_id in collections_lookup:
                parent_collection_name = collections_lookup[parent_collection_id]['Name']
                bread_crumb = parent_collection_name + "/" + collection_info['Name']
            else:
                bread_crumb = collection_info.get('Name', '')
        else:
            bread_crumb = ''
        # Compose RTF package
        package = (
            "\\i " + bread_crumb + "\\i0 \\line " +
            "\\fs28 \\b " + parent_title + " (" + parent_date + ") \\b0 \\fs22 \\line " +
            parent_creators + " \\line \\fs24 " + notes_raw
        ) if notes_raw else "\\i No Notes"
        notes.append(package)

    output = "\\par".join(notes)
    output = rtf_replace(output)

    timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
    out_path = f"{file_path}{search_query}_Zotero_notes_{timestamp}.rtf"
    rtf_header = (
        "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deftab720{\\fonttbl{\\f0\\fswiss MS Sans Serif;}"
        "{\\f1\\froman\\fcharset2 Symbol;}{\\f2\\fmodern\\fprq1 Courier New;}"
        "{\\f3\\froman Times New Roman;}}{\\colortbl\\red0\\green0\\blue0;"
        "\\red0\\green0\\blue255;\\red255\\green0\\blue0;}\\deflang1033\\horzdoc{\\*\\fchars }{\\*\\lchars}"
    )
    with io.open(out_path, 'w+', encoding="utf-8", errors="replace") as f:
        f.write(rtf_header)
        f.write(output + "\\par")
        f.write("}")

    print(f"Output file written successfully: {out_path}")

if __name__ == "__main__":
    main()