#!/usr/bin/env python
import config as cfg
from pyzotero import zotero
import datetime
import io

userID = cfg.zotGroupNotes["userID"]
secretKey = cfg.zotGroupNotes["secretKey"]
filePath = cfg.zotGroupNotes["filePath"]

zot = zotero.Zotero(userID, 'user', secretKey, 'preserve_json_order=true')
# zot = zotero.Zotero('groupID', 'group', 'secretKey','preserve_json_order=true')
# We now have a Zotero object, zot, and access to all its methods. Uncomment one or the other. User takes your userID and 'group' takes a shared group ID.

collectionsListKeys = {}
collectionsInfo = zot.collections()
i = 0
for i in range(len(collectionsInfo)):
    collectionsListKeys[(collectionsInfo[i]['data']['key'])] = dict(
        {'Name': collectionsInfo[i]['data']['name'], 'Parent': collectionsInfo[i]['data']['parentCollection']})
'''
Collection List keys field then looks something like
u'55GCTGSE': {'Name': u'Innovation Theory', 'Parent': False}
u'789HEDID': {'Name': u'Memory', 'Parent': u'XCNYW8JH'}
'''

collection = zot.items(limit=100)
parentIDs = []
for key in collection:
    parentIDs.append(key['key'])

childItems = []
i = 0
for i in range(len(parentIDs)):
    '''print parentIDs[i]'''
    itemHold = zot.item(parentIDs[i])
    '''print 'itemHold data: ', itemHold['data']'''
    childItems.append(itemHold['data'])

notes = []
collectionParentID = []
i = 0
for i in range(len(childItems)):
    notesHold = (childItems[i])
    if 'note' in notesHold:
        notesRaw = notesHold['note']
        if notesRaw.startswith('<p><strong>Extracted Annotations') or notesRaw.startswith('<p><b>Extracted Annotations'):
            parentID = notesHold['parentItem']
            '''ID of Parent Document'''
            parentDoc = zot.item(parentID)
            '''Full data for Parent Document'''
            collectionID = parentDoc['data']['collections'][0]
            '''Get collectionID for Parent Document'''
            collectionParentID = collectionsListKeys[collectionID]['Parent']
            '''Get ID for Parent Collection'''
            if str(collectionParentID) != 'False':
                '''Minor error catching/branch if the collection is the parent'''
                parentCollectionName = collectionsListKeys[collectionParentID]['Name']
                breadCrumb = parentCollectionName + "/" + collectionsListKeys[collectionID]['Name']
            else:
                breadCrumb = collectionsListKeys[collectionID]['Name']
            collectionTitle = collectionsListKeys[collectionID]['Name']
            parentTitle = parentDoc['data']['title']
            parentCreators = parentDoc['meta']['creatorSummary']
            package = "\\i " + str(
                breadCrumb) + "\\i0 \\line " + "\\fs28 \\b " + parentTitle + " \\b0 \\fs22 \\line " + parentCreators + " \\line \\fs24 " + notesRaw
            notes.append(package)
            '''Some concatenation and appending to the overall file'''

output = "\\par".join(notes)
output = output.replace("(<a href=", "{\\field{\\*\\fldinst { HYPERLINK")
output = output.replace("\">", "}}{\\fldrslt {")
output = output.replace("</a>)", "}}}")
output = output.replace("<p>", "\\line")
output = output.replace("</p>", "\\line")
output = output.replace("<strong>", "\\b ")
output = output.replace("</strong>", " \\b0")

timestamp = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')

rtf = "{\\rtf1\\ansi\\ansicpg1252\\deff0\\deftab720{\\fonttbl{\\f0\\fswiss MS Sans Serif;}{\\f1\\froman\\fcharset2 Symbol;}{\\f2\\fmodern\\fprq1 Courier New;}{\\f3\\froman Times New Roman;}}{\\colortbl\\red0\\green0\\blue0;\\red0\\green0\\blue255;\\red255\\green0\\blue0;}\\deflang1033\\horzdoc{\\*\\fchars }{\\*\\lchars}"

f = io.open(filePath + collectionTitle + '_excerpts_' + timestamp + '.rtf', 'w', encoding="cp1252")
f.write(rtf)
f.write(output + "\par")
f.write("}")
f.close()
