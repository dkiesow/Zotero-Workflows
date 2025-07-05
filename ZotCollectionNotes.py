#!/usr/bin/env python
"""
Optimized Zotero Notes Extractor
Extracts and formats notes from a Zotero collection to RTF format.
"""

import config as cfg
from pyzotero import zotero
import datetime
import io
import sys
import re
from typing import Dict, List, Optional, Any


class ZoteroNotesExtractor:
    """Handles extraction and formatting of Zotero notes."""
    
    def __init__(self, user_id: str, secret_key: str, file_path: str):
        self.user_id = user_id
        self.secret_key = secret_key
        self.file_path = file_path
        self.zot = zotero.Zotero(user_id, 'user', secret_key, 'preserve_json_order = true')
        self.collections_map = {}
        
        # Pre-compiled regex for date extraction
        self.date_pattern = re.compile(r"(?<!\d)\d{4,20}(?!\d)")
        
        # RTF conversion mappings
        self.rtf_replacements = [
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
    
    def build_collections_map(self) -> None:
        """Build a mapping of collection keys to their metadata."""
        collections_info = self.zot.collections()
        
        self.collections_map = {
            collection['data']['key']: {
                'name': collection['data']['name'],
                'parent': collection['data']['parentCollection'],
                'key': collection['data']['key']
            }
            for collection in collections_info
        }
    
    def find_collection_key(self, collection_name: str) -> Optional[str]:
        """Find collection key by name."""
        for key, data in self.collections_map.items():
            if data['name'] == collection_name:
                return key
        return None
    
    def get_collection_items(self, collection_key: str) -> List[Dict[str, Any]]:
        """Get all items from a collection, excluding attachments."""
        search_result = self.zot.everything(self.zot.collection_items(collection_key))
        
        # Filter out attachments in one pass
        return [item for item in search_result 
                if item['data']['itemType'] != 'attachment']
    
    def extract_note_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract note items and filter out unwanted ones."""
        note_items = [
            item['data'] for item in items 
            if "note" in item['data']['itemType']
        ]
        
        # Filter out notes with 'The following values'
        return [
            note for note in note_items 
            if not note['note'].startswith('The following values')
        ]
    
    def extract_parent_date(self, date_str: str) -> str:
        """Extract publication date from parent document."""
        match = self.date_pattern.search(date_str)
        return match.group(0) if match else "N.d."
    
    def build_breadcrumb(self, collection_id: str) -> str:
        """Build breadcrumb path for collection."""
        collection = self.collections_map.get(collection_id, {})
        parent_id = collection.get('parent')
        
        if parent_id:
            parent_collection = self.collections_map.get(parent_id, {})
            parent_name = parent_collection.get('name', 'Unknown')
            current_name = collection.get('name', 'Unknown')
            return f"{parent_name}/{current_name}"
        else:
            return collection.get('name', 'Unknown')
    
    def format_note(self, note_item: Dict[str, Any]) -> str:
        """Format a single note item."""
        notes_raw = note_item['note']
        
        # Check if this is an extracted annotation
        if not (notes_raw.startswith('<p><strong>Extracted Annotations') or 
                notes_raw.startswith('<p><b>Extracted Annotations')):
            return ""
        
        parent_id = note_item['parentItem']
        parent_doc = self.zot.item(parent_id)
        parent_data = parent_doc['data']
        parent_meta = parent_doc['meta']
        
        # Extract parent document information
        parent_date = self.extract_parent_date(parent_data.get('date', ''))
        parent_title = parent_data.get('title', 'No Title')
        parent_creators = parent_meta.get('creatorSummary', 'No Author')
        
        # Build breadcrumb
        collection_id = parent_data['collections'][0] if parent_data['collections'] else ''
        breadcrumb = self.build_breadcrumb(collection_id)
        
        if not notes_raw:
            return f"\\i No Notes"
        
        # Format the note package
        return (f"\\i {breadcrumb}\\i0 \\line "
                f"\\fs28 \\b {parent_title} ({parent_date}) \\b0 \\fs22 \\line "
                f"{parent_creators} \\line \\fs24 {notes_raw}")
    
    def convert_to_rtf(self, text: str) -> str:
        """Convert HTML-like text to RTF format."""
        for old, new in self.rtf_replacements:
            text = text.replace(old, new)
        return text
    
    def generate_rtf_file(self, notes: List[str], collection_name: str) -> None:
        """Generate the final RTF file."""
        output = "\\par".join(notes)
        output = self.convert_to_rtf(output)
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d')
        filename = f"{collection_name}_Zotero_notes_{timestamp}.rtf"
        
        rtf_header = ("{\\rtf1\\ansi\\ansicpg1252\\deff0\\deftab720"
                     "{\\fonttbl{\\f0\\fswiss MS Sans Serif;}{\\f1\\froman\\fcharset2 "
                     "Symbol;}{\\f2\\fmodern\\fprq1 Courier New;}{\\f3\\froman Times New Roman;}}"
                     "{\\colortbl\\red0\\green0\\blue0;\\red0\\green0\\blue255;\\red255\\green0\\blue0;}"
                     "\\deflang1033\\horzdoc{\\*\\fchars }{\\*\\lchars}")
        
        try:
            with io.open(self.file_path + filename, 'w+', encoding="cp1252") as f:
                f.write(rtf_header)
                f.write(output + "\\par")
                f.write("}")
            print(f"Successfully generated: {filename}")
        except Exception as e:
            print(f"Error writing file: {e}")
    
    def extract_notes(self, collection_name: str) -> None:
        """Main method to extract notes from a collection."""
        try:
            # Build collections mapping
            self.build_collections_map()
            
            # Find collection key
            collection_key = self.find_collection_key(collection_name)
            if not collection_key:
                print(f"Collection '{collection_name}' not found!")
                return
            
            # Get items and extract notes
            items = self.get_collection_items(collection_key)
            note_items = self.extract_note_items(items)
            
            if not note_items:
                print(f"No notes found in collection '{collection_name}'")
                return
            
            # Format notes
            notes = []
            for note_item in note_items:
                formatted_note = self.format_note(note_item)
                if formatted_note:
                    notes.append(formatted_note)
            
            if notes:
                self.generate_rtf_file(notes, collection_name)
                print(f"Processed {len(notes)} notes from '{collection_name}'")
            else:
                print(f"No valid notes found in collection '{collection_name}'")
                
        except Exception as e:
            print(f"Error processing collection: {e}")


def main():
    """Main function to run the script."""
    if len(sys.argv) != 2:
        print("Usage: python script.py <collection_name>")
        sys.exit(1)
    
    collection_name = sys.argv[1]
    
    try:
        # Get configuration
        user_id = cfg.zotCollectionNotes["userID"]
        secret_key = cfg.zotCollectionNotes["secretKey"]
        file_path = cfg.zotCollectionNotes["filePath"]
        
        # Create extractor and run
        extractor = ZoteroNotesExtractor(user_id, secret_key, file_path)
        extractor.extract_notes(collection_name)
        
    except KeyError as e:
        print(f"Missing configuration key: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
