from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import io
import os
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import threading
import time

class driveFacade:
    def __init__(self):
        # If modifying these scopes, delete the file token.pickle.
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self.service = None
        self.creds = None
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
            'application/vnd.google-apps.spreadsheet': 'doc',
            'application/vnd.google-apps.folder': 'folder'
        }

    def authenticate(self):
        # creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('drive', 'v3', credentials=self.creds)

    def get_files_metadata(self,no_files):
        results = self.service.files().list(
        pageSize=no_files, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        return items

    def get_file_content(self,file_id = None,item = None,filename = 'filename.zip',verbose = False,path = './',service = None):
        if(item):
            file_id = item['id']
            filename = os.path.join(path,item['name'])# + '.' + item['extension'])
        request = service.files().get_media(fileId=file_id)
        if verbose:
            print(f"Downloading at {filename}")
        fh = io.FileIO(filename, mode='w')
        if item['extension'] == 'doc':
            return
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if verbose:
                print("Download %d%%." % int(status.progress() * 100))
        return done

    def create_meta_files(self,items,path): 
        for item in items:
            full_path = os.path.join(path,item['name'])
            if item['extension'] != 'folder':
                fh = io.FileIO(full_path,mode = 'w')
                fh.close()
            elif item['extension'] == 'folder' and not os.path.lexists(full_path):
                os.mkdir(full_path)

    def get_root_id(self):
        file_metadata = {
            'name': 'temporary folder',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        tempFolderId = self.service.files().create(body=file_metadata, fields='id').execute()["id"] # Create temporary folder
        myDriveId = self.service.files().get(fileId=tempFolderId, fields='parents').execute()["parents"][0] # Get parent ID
        self.service.files().delete(fileId=tempFolderId).execute() # Delete temporary folder
        return myDriveId

    def get_extension(self,mimeType):
        if mimeType in self.extensions:
            return self.extensions[mimeType]
        return ''
        

    def get_all_files(self,parent = 'root'):
        service = build('drive', 'v3', credentials=self.creds)
        page_token = None
        items = []
        q = f"'{parent}' in parents"
        while True:
            # try:
            response = service.files().list(q=q,
                                                    spaces='drive',
                                                    fields='nextPageToken, files(id, name, mimeType)',
                                                    pageToken=page_token).execute()
            # except:
            #     return []
            for file in response.get('files', []):
                mimeType = file.pop('mimeType')
                file['extension'] = self.get_extension(mimeType)
                items.append(file)
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break
        # print(f"Total items : {len(items)}")
        return items

    def downloader(self,path,items,verbose = False):
        threads = []
        for item in items:
            full_path = os.path.join(path,item['name'])
            # if os.path.lexists(full_path):
            #     continue 
            if item['extension'] == 'folder' and not os.path.lexists(full_path):
                    os.mkdir(full_path)
                    if verbose:
                        print('success')
            elif item['extension'] != 'folder':
                service = build('drive', 'v3', credentials=self.creds)
                threads.append(threading.Thread(target=self.get_file_content,kwargs={'item':item,'path':path,'service':service}))
                threads[-1].start()
                # self.get_file_content(item=item,path=path,service=self.service)
        for thread in threads:
            thread.join()

        if verbose:
            print('success123')
        
    

    def create_folder(self,name,parent_id):
        service = build('drive', 'v3', credentials=self.creds)
        file_metadata = {
            'name': name,
            'parents': [parent_id],
            'mimeType': 'application/vnd.google-apps.folder'
        }
        file = service.files().create(body=file_metadata,fields='id,name,mimeType').execute()
        file['extension'] = self.get_extension(file.pop('mimeType'))
        return file

    def create_file(self,name,parent_id,source):
        service = build('drive', 'v3', credentials=self.creds)
        file_metadata = {'name': name,'parents': [parent_id]}
        media = MediaFileUpload(source)
        file = service.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id,name,mimeType').execute()
        file['extension'] = self.get_extension(file.pop('mimeType'))
        return file

    def update_file(self,file_id,metadata = None,source = None):
        service = build('drive', 'v3', credentials=self.creds)
        if metadata:
            file_metadata = metadata
        else:
            file_metadata = service.files().get(fileId=file_id).execute()
        if source:
            media = MediaFileUpload(source)
            file = service.files().update(fileId = file_id,body=file_metadata,
                                        media_body=media).execute()
        else:
            file = service.files().update(fileId = file_id,body=file_metadata).execute()
        return file

    def delete_file(self,file_id):
        service = build('drive', 'v3', credentials=self.creds)
        service.files().delete(fileId = file_id).execute()
        print('deleted')

    def trash_file(self,file_id):
        service = build('drive', 'v3', credentials=self.creds)
        body = {'trashed': True}
        updated_file = service.files().update(fileId=file_id, body=body).execute()
        print('trashed')
        return updated_file
        




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
    # items = df.get_all_files('1OfrcYqyTHEzQ0jHVAIfYe5TCZHsbrIkH')
    # # print(df.create_folder('man','14eyVbUtI29O0224U9NCD7SOQ2-xLpVYn'))
    # start = time.time()
    # df.downloader(path = './root',items = items,verbose = True)
    # end = time.time()
    # print(end-start)
    # print(items)
    # df.downloader('./root',items)
    # id = df.create_file('root','a')
    # items = df.get_all_files('1N2Kyt8vIIlOiW8oZmAFAaX261SZ8kWKV')
    # print(items)
    # file = df.update_file('1ssIQSQSJq4dEMC_wgf67KvMJc1BVLL78',metadata={'name' : 'text.txt','mimetype':'text/plain'},source='root/testinoacm/ghsdlgjd.txt')
    # print(file)
    # df.delete_file('1sA37GZE_NeyJkv7_8GMfZcFPPfwm2YbP')
    
            

if __name__ == '__main__':
    main()