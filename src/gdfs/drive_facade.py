from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import io
from googleapiclient.http import MediaIoBaseDownload

class driveFacade:
    def __init__(self):
        # If modifying these scopes, delete the file token.pickle.
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.service = None

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
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('drive', 'v3', credentials=creds)

    def get_files_metadata(self,no_files):
        results = self.service.files().list(
        pageSize=no_files, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        return items

    def get_file_content(self,file_id,filename = 'filename.zip',verbose = False):
        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(filename, mode='w')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if verbose:
                print("Download %d%%." % int(status.progress() * 100))
        return done

    def get_root_id(self):
        file_metadata = {
            'name': 'temporary folder',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        tempFolderId = self.service.files().create(body=file_metadata, fields='id').execute()["id"] # Create temporary folder
        myDriveId = self.service.files().get(fileId=tempFolderId, fields='parents').execute()["parents"][0] # Get parent ID
        self.service.files().delete(fileId=tempFolderId).execute() # Delete temporary folder
        return myDriveId


    def get_all_files(self,parent = 'root'):
        page_token = None
        items = []
        q = f"'{parent}' in parents"
        while True:
            response = self.service.files().list(q=q,
                                                spaces='drive',
                                                fields='nextPageToken, files(id, name)',
                                                pageToken=page_token).execute()
            for file in response.get('files', []):
                items.append(file)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        return items




def main():

    df = driveFacade()

    df.authenticate()
    # items = df.get_files_metadata(12)

    # if not items:
    #     print('No files found.')
    # else:
    #     print('Files:')
    #     for item in items:
    #         print(u'{0} ({1})'.format(item['name'], item['id']))

    # df.get_file_content(items[3]['id'],'img.jpg',True)
    print(df.get_all_files('1D-a62Ardu8gOnV_88LHtY0tBsC60y1P-'))
            

if __name__ == '__main__':
    main()