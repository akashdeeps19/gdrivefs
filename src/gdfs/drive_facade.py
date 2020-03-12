from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import io
import os
from googleapiclient.http import MediaIoBaseDownload

import threading 

class driveFacade:
    def __init__(self):
        self.time=0
        # If modifying these scopes, delete the file token.pickle.
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.service = None
        self.extensions = {
            'application/vnd.ms-excel': 'xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx', 
            'text/xml': 'xml', 
            'application/vnd.oasis.opendocument.spreadsheet': 'ods', 
            'text/plain': 'txt', 
            'application/pdf': 'pdf', 
            'application/x-httpd-php': 'php', 
            'image/jpeg': 'jpg', 
            'image/png': 'png', 
            'image/gif': 'gif', 
            'image/bmp': 'bmp', 
            'application/msword': 'doc', 
            'text/js': 'js', 
            'application/x-shockwave-flash': 'swf', 
            'audio/mpeg': 'mp3', 
            'application/zip': 'zip', 
            'application/rar': 'rar', 
            'application/tar': 'tar', 
            'application/arj': 'arj', 
            'application/cab': 'cab', 
            'text/html': 'htm', 
            'application/octet-stream': 'default', 
            'application/vnd.google-apps.document': 'doc',
            'application/vnd.google-apps.folder': 'folder'
        }
        self.changes_token = None

    def authenticate(self):
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Creds expired")
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('drive', 'v3', credentials=creds)
        print("Authenticated")

    def get_files_metadata(self,no_files):
        results = self.service.files().list(
        pageSize=no_files, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])
        print("Got metadata")

        return items

    def get_file_content(self,file_id = None,item = None,filename = 'filename.zip',verbose = False,path = './',threadNumber=0):
        print("Thread number ",threadNumber)
        if(item):
            file_id = item['id']
            filename = os.path.join(path,item['name'] + '.' + item['extension'])
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(filename, mode='w')
        if item['extension'] == 'doc':
            return
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if verbose:
                print("Download %d%%." % int(status.progress() * 100))
        print("Getting file contentS")
        return done


    def get_root_id(self):
        file_metadata = {
            'name': 'temporary folder',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        tempFolderId = self.service.files().create(body=file_metadata, fields='id').execute()["id"] # Create temporary folder
        myDriveId = self.service.files().get(fileId=tempFolderId, fields='parents').execute()["parents"][0] # Get parent ID
        self.service.files().delete(fileId=tempFolderId).execute() # Delete temporary folder
        print("get root id")
        return myDriveId

    def get_extension(self,mimeType):
        print("get extension")
        return self.extensions[mimeType]
        

    def get_all_files(self,parent = 'root'):
        page_token = None
        items = []
        q = f"'{parent}' in parents"
        while True:
            # try:
            response = self.service.files().list(q=q,
                                                    spaces='drive',
                                                    fields='nextPageToken, files(id, name, mimeType)',
                                                    pageToken=page_token).execute()
            # except:
            #     return []
            for file in response.get('files', []):
                file['extension'] = self.get_extension(file.pop('mimeType'))
                items.append(file)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        print("get all files")
        return items

    def downloader(self,path,items,verbose = True):
        print("Downloading...")
        i=0
        for item in items:
            full_path = os.path.join(path,item['name'])
            if os.path.lexists(full_path):
                continue 
            if item['extension'] == 'folder':
                    #just creating the directory if it is not a file
                    os.mkdir(full_path)
                    if verbose:
                        print('success')
            else:
                try:
                    threading.Thread(target=(self.get_file_content),kwargs=dict(item=item,path=path,threadNumber=i,))
                except:
                    print("Error while downling using threads")
                if verbose:
                    print('success')
            i+=1
        
    def get_item(self,items,name):
        print("getting item    ",self.time)
        self.time+=1
        for item in items:
            if item['name'] == name:
                return item
        return False

    def create_folder(self,name,parent_id):
        print("create folder")
        file_metadata = {
            'name': name,
            'parents': [parent_id],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        file = self.service.files().create(body=file_metadata,fields='id,name,mimeType').execute()
        file['extension'] = self.get_extension(file.pop('mimeType'))
        return file

    def get_start_page_token(self):
        print("get_start_page_token")
        response = self.service.changes().getStartPageToken().execute()
        start_page_token = response.get('startPagetoken')
        return start_page_token

    def changes_token_func(self):
        print("changes_token_func")
        if self.changes_token == None:
            self.changes_token = self.get_start_page_token()

        return self.changes_token

    def get_changes(self):
        print("get changes")
        token = self.changes_token_func()
        changes = []

        while token is not None:
            response = self.service.changes().list(pageToken=token,spaces='drive').execute()
            for change in response.get('changes'):
                # Process change
                print ('Change found for file: ' , change.get('fileId'))
                changes.append(change.get('fileId'))
            if 'newStartPageToken' in response:
                # Last page, save this token for the next polling interval
                self.changes_token = response.get('newStartPageToken')
            token = response.get('nextPageToken')

        return changes



def main():

    df = driveFacade()
    df.authenticate()
    items = df.get_all_files()
    print(items)
 
            

if __name__ == '__main__':
    main()