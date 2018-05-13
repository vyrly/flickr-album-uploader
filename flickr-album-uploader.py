#!/usr/bin/python

# Flickr album uploader
# Author: https://github.com/vyrly
# Based on https://github.com/alfem/synology-flickr-folder-uploader

# Get an api key and an api secret: https://www.flickr.com/services/apps/create/apply

# Start this script. First time it shows an URL. Open it with your browser and authorize the script.
# Once authorized, script will store a token in directory:
TOKEN_CACHE='./token'

import flickrapi
import yaml
import os
import sys
import argparse
import time
import random
from pathlib import Path

def GetDirList(dirPath):
    dirList = next(os.walk(dirPath))[1]
    dirList.sort()
    return dirList

def isInCorrectFormat(filename):
    filenameSplit = filename.split('.')
    if len(filenameSplit) == 2:
        ext = filenameSplit[1].lower()
    else:
        ext = ''
    if (ext in ['png', 'jpeg', 'jpg', 'avi', 'mp4', 'gif', 'tiff', 'mov', 'wmv', 'ogv', 'mpg', 'mp2', 'mpeg', 'mpe', 'mpv']):
        return True
    else:
        return False

def wasUploaded(path, photoIDs):
    if path in photoIDs:
        return True
    else:
        return False

def loadYAML(path):
    if path.is_file():
        with open(path, 'r') as stream:
            try:
                photoIDs = yaml.load(stream)
                print(str(path) + " file loaded")
                return photoIDs
            except yaml.YAMLError as exc:
                print(exc)
    else:
        print("Path not found: " + str(path))
        return {}

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
FlickrSecret = loadYAML(Path(os.path.join(__location__, 'FlickrSecret.yml')))
parser = argparse.ArgumentParser()
parser.add_argument("folder", help="Path to the folder you want to upload")
parser.add_argument("--dryrun", dest="dryrun", action='store_false', default=False, help="Run script without uploading")
params=parser.parse_args()

class FlickrManager:
    """docstring for FlickrManager."""

    flickr = flickrapi.FlickrAPI(FlickrSecret["API_KEY"], FlickrSecret["API_SECRET"], token_cache_location=TOKEN_CACHE)

    def __init__(self):
        # Init flickrapi
        print("Init")

    def Authenticate(self):
        if not self.flickr.token_valid(perms='write'):
            print("Authentication required")
            # Get request token
            self.flickr.get_request_token(oauth_callback='oob')
            # Show url. Copy and paste it in your browser
            authorize_url = flickr.auth_url(perms=u'write')
            print(authorize_url)
            # Prompt for verifier code from the user
            verifier = unicode(raw_input('Verifier code: '))
            print("Verifier: " + verifier)
            # Trade the request token for an access token
            print(flickr.get_access_token(verifier))
            #     return 0

    def UploadFile(self, fullFilename):
        try:
            print(" | Upload:", end = '')
            uploadResp = self.flickr.upload(filename=fullFilename, is_public=0, is_friend=0, is_family=0)
            photoID = uploadResp.findall('photoid')[0].text
            print(" OK", end = '')
            return photoID
        except:
            print("ERROR", end = '')
            return 0

    def CreateAlbum(self, albumName, photoID):
        try:
            print(" | Set: '" + albumName + "'" + " photoID: " + photoID, end = '')
            resp = self.flickr.photosets.create(title=albumName,primary_photo_id=photoID)
            photosetID = resp.findall('photoset')[0].attrib['id']
            print(" photosetID: '" + photosetID, end = '')
            return photosetID
        except:
            print ("ERROR", end = '')

    def AddToAlbum(self, photosetID, photoID):
        try:
            print(" | AddToAlbum:", end = '')
            resp = self.flickr.photosets.addPhoto(photoset_id=photosetID,photo_id=photoID)
            print(" OK", end = '')
            return True
        except:
            print ("ERROR", end = '')
            return False

rootDirPath=os.path.abspath(params.folder) + "/"

flickrManager = FlickrManager()
flickrManager.Authenticate()

# For each directory in root directory...
dirList = GetDirList(rootDirPath)
for directory in dirList:
    directoryPath = rootDirPath + directory
    print(directoryPath)

    # Load log files from previous uploads
    photoIDs = loadYAML(Path(directoryPath + '/photoIDs.yml'))
    failed = loadYAML(Path(directoryPath + '/failed.yml'))
    photosetID = loadYAML(Path(directoryPath + '/photoset.yml'))

    createAlbum = True
    if directory in photosetID:
        createAlbum = False

    uploadSuccess = False

    # ...find files recursively,...
    for subdir, dirnames, filenames in os.walk(directoryPath):
        filenames.sort()
        for filename in filenames:
            print(filename, end='')
            fullFilename = os.path.join(subdir, filename)
            # ...upload them...
            if isInCorrectFormat(filename) and not wasUploaded(fullFilename, photoIDs):
                photoID = flickrManager.UploadFile(fullFilename)
                counter = 1
                while (photoID == 0 and counter < 5):
                    counter = counter + 1
                    photoID = flickrManager.UploadFile(fullFilename)
                if (counter >= 3):
                    failed[directory] = fullFilename
                else:
                    photoIDs[fullFilename] = photoID
                    uploadSuccess = True;
                # ...and create an album
                if createAlbum and uploadSuccess: # TODO: add failsafe
                    ID = flickrManager.CreateAlbum(directory, photoID)
                    photosetID[directory] = ID
                    createAlbum = False
                elif uploadSuccess:
                    flickrManager.AddToAlbum(photosetID[directory], photoID)
                    failed.pop('directory', None)
                    print("")
            else:
                print(" | skipping")

    # Save successful uploads ids
    with open(directoryPath + '/photoIDs.yml', 'w') as outfile:
        yaml.dump(photoIDs, outfile, default_flow_style=False)
    # Save failed uploads ids
    with open(directoryPath + '/failed.yml', 'w') as outfile:
        yaml.dump(failed, outfile, default_flow_style=False)
    # Save photoset ids
    with open(directoryPath + '/photoset.yml', 'w') as outfile:
        yaml.dump(photosetID, outfile, default_flow_style=False)
