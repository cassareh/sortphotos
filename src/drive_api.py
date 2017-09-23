
from __future__ import print_function
import argparse
import httplib2
import os
import pprint
import sys

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/drive-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/drive'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Drive API Python Quickstart'


def get_credentials(flags):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials

    
def get_file_id(service, filepath):
    # List all files with the same name, but not deleted ones.
    resp = service.files().list(
        q="title='%s' and trashed=false" % os.path.basename(filepath),
        #fields='items(id,title,parents,trashed)'
    ).execute()
    files = resp.get('items', [])
    if len(files) > 1:
        # Update filepath before we recurse.
        new_filepath = os.path.split(filepath)[0]
        file_id = dissambiguate_files(service, new_filepath, files)
    else:
        file_id = files[0].get('id')
      
    return file_id

    
def move(service, src_file, dest_file):
    file_id = get_file_id(service, src_file)
    dest_parent = os.path.split(dest_file)[0]
    folder_id = get_file_id(service, dest_parent)
    # Retrieve the existing parents to remove
    file = service.files().get(fileId=file_id,
                               fields='parents').execute();
    previous_parents = ",".join([parent['id'] for parent in file.get('parents')])
    # Move the file to the new folder
    file = service.files().update(fileId=file_id,
                                  addParents=folder_id,
                                  removeParents=previous_parents,
                                  fields='id, parents').execute()
    print('updated %s' % file)


def dissambiguate_files(service, filepath, files):
    """Given a list of files with the same name, find the right one.

    The search is done by recursively matching parent directories as far
    as necessary until there is only one match.

    Args:
      service: The API service object.
      filepath: The path to the file, without the filename, such that basename
        will contain the next parent dir that should be matched.
      files: A list of file JSON objects or a dictionary with the JSON file
        objects as keys and their parent JSON objects as values.
        
    Returns:
       The single JSON file object once a match is found.
    """
    files_parents_map = {}
    if type(files) == list:
        # first time, create the map to associate file with parents
        for file in files:
            parent = service.files().get(
                # Look up the parent by id.
                fileId=file.get('parents')[0].get('id'),
                fields='id,title,parents'
            ).execute()
            # We query by ID, so there should only be 1 hit.
            if parent.get('title') == os.path.basename(filepath):
                files_parents_map[file.get('id')] = parent.get('parents')[0]
    else:
        # Already a dict, so we've been here before
        for file_id in files:
            parent = service.files().get(
                # Look up the parent of the parent.
                fileId=files[file_id].get('id'),
                fields='id,title,parents'
            ).execute()
            # We query by ID, so there should only be 1 hit.
            if parent.get('title') == os.path.basename(filepath):
                files_parents_map[file_id] = parent.get('parents')[0]
                
    if len(files_parents_map) > 1:
        # Update filepath before we recurse.
        new_filepath = os.path.split(filepath)[0]
        return dissambiguate_files(service, new_filepath, files_parents_map)
    else:
        return files_parents_map.keys()[0]

        
def pretty_print(thing):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(thing)
     

def get_service():
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    flags = parser.parse_known_args()[0]

    credentials = get_credentials(flags)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v2', http=http)
    return service

    
def main():
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    service = get_service()

    results = service.files().list(maxResults=10).execute()
    items = results.get('items', [])
    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print('{0} ({1})'.format(item['title'], item['id']))

if __name__ == '__main__':
    main()