# !/usr/bin/env python
import sys
import io
import os
import re
import datetime
import logging
import argparse
import collections
from pyzotero import zotero
from config import ZOTERO_CONFIGS

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(message)s")


def get_zotero_instance():
    config = ZOTERO_CONFIGS.get("collectionNotes")
    if not config:
        logging.error("Missing 'collectionNotes' config.")
        sys.exit(1)
    userID = config.get("userID")
    secretKey = config.get("secretKey")
    if not userID or not secretKey:
        logging.error("Missing userID or secretKey in config.")
        sys.exit(1)
    try:
        zot = zotero.Zotero(userID, 'user', secretKey, 'preserve_json_order = true')
        logging.debug("Zotero instance created.")
        return zot
    except Exception as e:
        logging.error(f"Failed to create Zotero instance: {e}")
        sys.exit(1)


def build_collections_dict(zot):
    try:
        collections_info = zot.collections()
        collections_dict = {}
        for col in collections_info:
            data = col['data']
            collections_dict[data['key']] = {
                'Name': data['name'],
                'Parent': data['parentCollection'],
                'Key': data['key']
            }
        logging.debug(f"Collections loaded: {len(collections_dict)} found.")
        return collections_dict
    except Exception as e:
        logging.error(f"Error fetching collections: {e}")
        return {}


def find_collection_key(collections_dict, collection_name):
    for key, value in collections_dict.items():
        if value['Name'] == collection_name:
            return value['Key']
    logging.warning(f"Collection '{collection_name}' not found.")
    return None


def list_collections(zot):
    collections = zot.collections()
    # Build a dict: key -> {name, parent, children}
    tree = {}
    for col in collections:
        data = col['data']
        key = data['key']
        parent = data['parentCollection']
        tree[key] = {'name': data['name'], 'parent': parent, 'children': []}

    # Assign children
    for key, node in tree.items():
        parent = node['parent']
        if parent and parent in tree:
            tree[parent]['children'].append(key)

    # Find roots (no parent or empty parent)
    roots = [key for key, node in tree.items() if not node['parent']]
    # Sort roots by name (case-insensitive)
    roots = sorted(roots, key=lambda k: tree[k]['name'].lower())

    def print_tree(key, level=0):
        print("  " * level + f"- {tree[key]['name']} (Key: {key})")
        # Sort children by name (case-insensitive) before printing
        sorted_children = sorted(tree[key]['children'], key=lambda k: tree[k]['name'].lower())
        for child_key in sorted_children:
            print_tree(child_key, level + 1)

    print("Collections:")
    if not roots:
        print("No collections found or all collections have unknown parents.")
        # Print all collections as a fallback
        for key in sorted(tree.keys(), key=lambda k: tree[k]['name'].lower()):
            print(f"- {tree[key]['name']} (Key: {key}, Parent: {tree[key]['parent']})")
    else:
        for root in roots:
            print_tree(root)


def list_collections_with_notes(zot):
    collections_dict = build_collections_dict(zot)
    if not collections_dict:
        print("No collections found.")
        return

    note_counts = collections.defaultdict(int)
    for key, col in collections_dict.items():
        items = zot.everything(zot.collection_items(key))
        notes = [item for item in items if
                 item['data']['itemType'] == 'note' and not item['data']['note'].startswith('The following values')]
        note_counts[key] = len(notes)

    print("Collections with notes:")
    for key, count in sorted(note_counts.items(), key=lambda x: collections_dict[x[0]]['Name'].lower()):
        name = collections_dict[key]['Name']
        print(f"- {name}: {count} note{'s' if count != 1 else ''}")

def filter_note_items(search_result):
    return [item for item in search_result if item['data']['itemType'] != 'attachment']


def extract_notes(note_items):
    return [n['data'] for n in note_items if
            "note" in n['data']['itemType'] and not n['data']['note'].startswith('The following values')]


def format_note(zot, note, collections_dict, default="None"):
    notes_raw = note.get('note', '')
    if notes_raw.startswith('<p><strong>Extracted Annotations') or notes_raw.startswith('<p><b>Extracted Annotations'):
        parent_id = note.get('parentItem')
        try:
            parent_doc = zot.item(parent_id)
        except Exception as e:
            logging.error(f"Error fetching parent item {parent_id}: {e}")
            return None
        match = re.search(r"(?<!\d)\d{4,20}(?!\d)", parent_doc['data'].get('date', ''))
        parent_date = match.group(0) if match else "N.d."
        try:
            collection_id = parent_doc['data']['collections'][0]
            collection_parent_id = collections_dict[collection_id]['Parent']
            if not str(collection_parent_id):
                parent_collection_name = collections_dict[collection_parent_id][
                    'Name'] if collection_parent_id in collections_dict else default
                bread_crumb = f"{parent_collection_name}/{collections_dict[collection_id]['Name']}" if collection_id in collections_dict else default
            else:
                bread_crumb = collections_dict[collection_id]['Name'] if collection_id in collections_dict else default
        except Exception as e:
            logging.error(f"Error building breadcrumb for note: {e}")
            bread_crumb = default
        parent_title = parent_doc['data'].get('title', "No Title")
        parent_creators = parent_doc['meta'].get('creatorSummary', "No Author")
        if not notes_raw:
            return "\\i No Notes"
        return f"\\i {bread_crumb}\\i0 \\line \\fs28 \\b {parent_title} ({parent_date})  \\b0 \\fs22 \\line {parent_creators} \\line \\fs24 {notes_raw}"
    return None


def rtf_replacements(output):
    replacements = [
        ("(<a href=", "{\\field{\\*\\fldinst { HYPERLINK"),
        ("\">", "}}{\\fldrslt {"),
        ("</a>)", "}}}"),
        ("<p>", "\\line"),
        ("</p>", "\\line"),
        ("<br>", "\\line"),
        ("<strong>", "\\b "),
        ("</strong>", " \\b0"),
        ("<b>", "\\b "),
        ("</b>", " \\b0"),
        ("<i>", "\\i "),
        ("</i>", " \\i0"),
        ("\u02d8", "&#728;"),
        ("\u02C7", "&#728;"),
        ("\x8e", "&#x8E;"),
        ("\u2212", "&#8722;"),
        ("\u2715", "&#10005;"),
        ("\u03b5", "&#949;"),
        ("\u0301", "&#769;"),
        ("\u2192", "&#8594;"),
        ("\u25cf", "&#9679;"),
        ("\u2015", "&#8213;"),
    ]
    for old, new in replacements:
        output = output.replace(old, new)
    return output


def write_rtf_file(file_path, collection_query, output):
    """
    Write RTF file with comprehensive error checking and user notifications.

    Args:
        file_path (str): Directory path where the file should be written
        collection_query (str): Collection name for filename
        output (str): RTF content to write

    Returns:
        bool: True if file was written successfully, False otherwise
    """
    timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
    rtf_header = (
        "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deftab720{\\fonttbl{\\f0\\fswiss MS Sans Serif;}"
        "{\\f1\\froman\\fcharset2 Symbol;}{\\f2\\fmodern\\fprq1 Courier New;}"
        "{\\f3\\froman Times New Roman;}}{\\colortbl\\red0\\green0\\blue0;"
        "\\red0\\green0\\blue255;\\red255\\green0\\blue0;}\\deflang1033\\horzdoc{\\*\\fchars }{\\*\\lchars}"
    )

    # Sanitize collection_query for filename (remove invalid characters)
    safe_collection_name = "".join(c for c in collection_query if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{file_path}{safe_collection_name}_Zotero_notes_{timestamp}.rtf"

    print("🔍 Pre-flight checks:")
    print(f"   📝 Target file: {filename}")

    try:
        # Check if directory exists
        directory = os.path.dirname(filename) if os.path.dirname(filename) else file_path
        if not os.path.exists(directory):
            logging.error(f"Directory does not exist: {directory}")
            print(f"   ❌ Directory does not exist: {directory}")
            return False
        else:
            print(f"   ✅ Directory exists: {directory}")

        # Check if directory is writable
        if not os.access(directory, os.W_OK):
            logging.error(f"Directory is not writable: {directory}")
            print(f"   ❌ Directory is not writable. Check permissions.")
            return False
        else:
            print(f"   ✅ Directory is writable")

        # Check if file already exists and warn user
        if os.path.exists(filename):
            logging.warning(f"File already exists and will be overwritten: {filename}")
            print(f"   ⚠️  File exists and will be overwritten")

        # Check if output content is empty
        if not output or not output.strip():
            logging.warning("No content to write to file.")
            print("   ⚠️  No content to write")
        else:
            content_length = len(output)
            print(f"   ✅ Content ready: {content_length:,} characters")

        print("\n💾 Writing file...")

        # Write the file
        with io.open(filename, 'w+', encoding="utf-8") as f:
            f.write(rtf_header)
            f.write(output + "\\par")
            f.write("}")

        # Verify file was written and get size
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)

            # Quick content validation
            with open(filename, 'r', encoding="utf-8") as f:
                first_line = f.readline()
                if first_line.startswith("{\\rtf1"):
                    rtf_valid = "✅ RTF header verified"
                else:
                    rtf_valid = "⚠️  RTF header may be invalid"

            logging.info(f"RTF file written successfully: {filename} ({file_size} bytes)")
            print(f"\n✅ File written successfully!")
            print(f"   📁 Location: {filename}")
            print(f"   📏 Size: {file_size:,} bytes")
            print(f"   {rtf_valid}")
            return True
        else:
            logging.error(f"File was not created: {filename}")
            print(f"❌ File was not created: {filename}")
            return False

    except PermissionError as e:
        logging.error(f"Permission denied when writing file: {e}")
        print(f"❌ ERROR: Permission denied. Cannot write to '{filename}'.")
        print("   Check file permissions and ensure the file is not open in another program.")
        return False

    except UnicodeEncodeError as e:
        logging.error(f"Unicode encoding error: {e}")
        print(f"❌ ERROR: Unicode encoding error when writing file.")
        print("   Some characters in the content cannot be encoded in CP1252.")
        return False

    except OSError as e:
        logging.error(f"OS error when writing file: {e}")
        print(f"❌ ERROR: System error when writing file: {e}")
        return False

    except Exception as e:
        logging.error(f"Unexpected error writing RTF file: {e}")
        print(f"❌ ERROR: Unexpected error when writing file: {e}")
        return False


def list_groups(zot):
    groups = zot.groups()
    print("Groups:")
    for group in groups:
        data = group['data']
        print(f"- {data['name']} (ID: {data['id']})")


def main():
    parser = argparse.ArgumentParser(description="Zotero Collection Notes Utility")
    parser.add_argument('--list-collections', action='store_true', help='List all collections and exit')
    parser.add_argument('--list-groups', action='store_true', help='List all groups and exit')
    parser.add_argument('--collections-with-notes', action='store_true',
                        help='List collections with note counts and exit')
    parser.add_argument('collection_query', nargs='?', default=None, help='Collection name to process')
    args = parser.parse_args()

    config = ZOTERO_CONFIGS.get("collectionNotes")
    if not config:
        logging.error("Missing 'collectionNotes' config.")
        sys.exit(1)
    file_path = config.get("filePath")
    if not file_path:
        logging.error("Missing filePath in config.")
        sys.exit(1)
    zot = get_zotero_instance()

    if args.list_collections:
        list_collections(zot)
        sys.exit(0)
    if args.list_groups:
        list_groups(zot)
        sys.exit(0)
    if args.collections_with_notes:
        list_collections_with_notes(zot)
        sys.exit(0)

    config = ZOTERO_CONFIGS.get("collectionNotes")
    if not config:
        logging.error("Missing 'collectionNotes' config.")
        sys.exit(1)
    file_path = config.get("filePath")
    if not file_path:
        logging.error("Missing filePath in config.")
        sys.exit(1)
    zot = get_zotero_instance()

    if args.list_collections:
        list_collections(zot)
        sys.exit(0)
    if args.list_groups:
        list_groups(zot)
        sys.exit(0)
    if args.collections_with_notes:
        list_collections_with_notes(zot)
        sys.exit(0)

    collection_query = args.collection_query or config.get("collectionQuery", "")
    if not collection_query:
        logging.error("No collection query provided.")
        sys.exit(1)

    print(f"🔍 Processing collection: {collection_query}")

    collections_dict = build_collections_dict(zot)
    if not collections_dict:
        logging.error("No collections found.")
        sys.exit(1)

    search_key = find_collection_key(collections_dict, collection_query)
    if not search_key:
        logging.error("Collection not found.")
        print(f"❌ Collection '{collection_query}' not found.")
        sys.exit(1)

    print(f"✅ Collection found: {search_key}")
    print("📚 Fetching items from collection...")

    search_result = zot.everything(zot.collection_items(search_key))
    note_items = filter_note_items(search_result)

    print(f"📝 Processing {len(note_items)} items for notes...")

    notes = []
    for note in extract_notes(note_items):
        formatted = format_note(zot, note, collections_dict)
        if formatted:
            notes.append(formatted)

    if not notes:
        logging.warning("No notes found for the collection.")
        print("⚠️  No notes found for the collection.")
    else:
        print(f"✅ Found {len(notes)} notes to process")

    output = "\\par".join(notes)
    output = rtf_replacements(output)

    # Write the RTF file with enhanced error checking
    success = write_rtf_file(file_path, collection_query, output)

    if success:
        print(f"\n🎉 Process completed successfully!")
        print(f"   📚 Collection: {collection_query}")
        print(f"   📝 Notes processed: {len(notes)}")
    else:
        print(f"\n💥 Process failed!")
        print(f"   The RTF file could not be written.")
        sys.exit(1)


if __name__ == "__main__":
    main()