#!/usr/bin/env python
import config as cfg
from pyzotero import zotero
import datetime
import io
import sys
import re

userID = cfg.zotCollectionNotes["userID"]
secretKey = cfg.zotCollectionNotes["secretKey"]
filePath = cfg.zotCollectionNotes["filePath"]
#collectionQuery = cfg.zotCollectionNotes["collectionQuery"]

# Comment out the next line to test using the searchterm in config.py
collectionQuery = sys.argv[1]
searchQuery=""

zot = zotero.Zotero(userID, 'user', secretKey, 'preserve_json_order = true')
# we now have a Zotero object, zot, and access to all its methods

# create a list of collection keys
collectionsInfo = zot.collections()
collectionsListKeys = {}
i = 0
for i in range(len(collectionsInfo)):
    collectionsListKeys[(collectionsInfo[i]['data']['key'])] = dict(
        {'Name': collectionsInfo[i]['data']['name'], 'Parent': collectionsInfo[i]['data']['parentCollection'], 'Key' : collectionsInfo[i]['data']['key']})
'''
CollectionsListKeys dict then looks something like
u'55GCTGSE': {'Name': u'Innovation Theory', 'Parent': False}
u'789HEDID': {'Name': u'Memory', 'Parent': u'XCNYW8JH'}
'''

for name, key in collectionsListKeys.items():
    if key['Name'] == collectionQuery:
        searchQuery = key['Key']

searchResult = zot.collection_items(searchQuery)

indices = [i for i, n in enumerate(searchResult) if n['data']['itemType'] == 'attachment']
searchResult[:] = [j for i, j in enumerate(searchResult)
                   if i not in indices]
noteItems = []
i = 0
for i in range(len(searchResult)):
    childHold = searchResult[i]
    if "note" in childHold['data']['itemType']:
        noteItems.append(childHold['data'])

# remove notes with 'the following values have no...'
indices = [i for i, n in enumerate(noteItems) if n['note'].startswith('The following values')]
noteItems[:] = [j for i, j in enumerate(noteItems)
                if i not in indices]

# build the body of the file
notes = []
notesHold = []
collectionParentID = []
parentID = {}
i = 0
for i in range(len(noteItems)):
    notesHold = (noteItems[i])
    notesRaw = notesHold['note']
    if notesRaw.startswith('<p><strong>Extracted Annotations') or notesRaw.startswith('<p><b>Extracted Annotations'):
        parentID = notesHold['parentItem']
        '''ID of Parent Document'''
        parentDoc = zot.item(parentID)
        '''Full data for Parent Document'''
        match = re.search(r"(?<!\d)\d{4,20}(?!\d)", parentDoc['data']['date'])
        parentDate = match.group(0) if match else None
        '''Get publication date for Parent Document'''
        collectionID = parentDoc['data']['collections'][0]
        '''Get collectionID for Parent Document'''
        collectionParentID = collectionsListKeys[collectionID]['Parent']
        '''Get ID for Parent Collection'''
        if not str(collectionParentID):
            '''Minor error catching/branch if the collection is the parent'''
            parentCollectionName = collectionsListKeys[collectionParentID]['Name']
            breadCrumb = parentCollectionName + "/" + collectionsListKeys[collectionID]['Name']
            collectionTitle = parentCollectionName
        else:
            breadCrumb = collectionsListKeys[collectionID]['Name']
            collectionName = breadCrumb
            collectionTitle = collectionName
            parentTitle = parentDoc['data']['title']
            parentCreators = parentDoc['meta']['creatorSummary']
        if not notesRaw:
            package = "\\i " + "No Notes"
            notes.append(package)
        else:
            package = "\\i " + str(
                breadCrumb) + "\\i0 \\line " + "\\fs28 \\b " + parentTitle + " (" + parentDate + ") " + " \\b0 \\fs22 \\line " + parentCreators + " \\line \\fs24 " + notesRaw
            notes.append(package)
            '''Some concatenation and appending to the overall file'''

output = "\\par".join(notes)
# various translations for RTF and quick replacement for characters that don't encode correctly
output = output.replace("(<a href=", "{\\field{\\*\\fldinst { HYPERLINK")
output = output.replace("\">", "}}{\\fldrslt {")
output = output.replace("</a>)", "}}}")
output = output.replace("<p>", "\\line")
output = output.replace("</p>", "\\line")
output = output.replace("<strong>", "\\b ")
output = output.replace("</strong>", " \\b0")
output = output.replace("\u02d8", "&#728;")
output = output.replace("\u02C7", "&#728;")
output = output.replace("\x8e", "&#x8E;")
output = output.replace("\u2212", "&#8722;")
output = output.replace("\u2715", "&#10005;")
output = output.replace("\u03b5", "&#949;")



timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')
rtf = "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deftab720{\\fonttbl{\\f0\\fswiss MS Sans Serif;}{\\f1\\froman\\fcharset2 Symbol;}{\\f2\\fmodern\\fprq1 Courier New;}{\\f3\\froman Times New Roman;}}{\\colortbl\\red0\\green0\\blue0;\\red0\\green0\\blue255;\\red255\\green0\\blue0;}\\deflang1033\\horzdoc{\\*\\fchars }{\\*\\lchars}"
f = io.open(filePath + collectionQuery + '_Zotero_notes_' + timestamp + '.rtf',
            'w+', encoding="cp1252", )
f.write(rtf)
f.write(output + "\par")
f.write("}")
f.close()
