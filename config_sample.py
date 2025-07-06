#!/usr/bin/env python

# Common configuration values
USER_ID = "#####"
GROUP_ID = "#####"
SECRET_KEY = "Get from Zotero"
FILE_PATH = "/Users/path/to//Notes/"

ZOTERO_CONFIGS = {
    "searchNotes": {
        "userID": USER_ID,
        "secretKey": SECRET_KEY,
        "filePath": FILE_PATH,
        "searchQuery": "innovation",
    },
    "groupNotes": {
        "userID": USER_ID,
        "groupID": GROUP_ID,
        "secretKey": SECRET_KEY,
        "filePath": FILE_PATH,
    },
    "collectionNotes": {
        "userID": USER_ID,
        "groupID": GROUP_ID,
        "secretKey": SECRET_KEY,
        "filePath": FILE_PATH,
       # "collectionQuery": "Mizzou News Deserts",  # Set your default collection name here
    },
}
