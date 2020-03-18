import os
import threading
from drive_facade import driveFacade

class fileMethods:
    def __init__(self):
        self.df = driveFacade()
        self.df.authenticate()
        self.items = self.df.get_all_files()
        self.df.create_meta_files(self.items,'root/')
        d_thread = threading.Thread(target = self.df.downloader,args=('root/',self.items))
        d_thread.start()
        self.history = {'/':self.items}
        self.root_dir = {'id' : 'root', 'name' : '', 'extension' : 'folder'}
    
    def get_item(self,items,name):
        for item in items:
            if item['name'] == name:
                return item
        return False

    def find_parent(self,path):
        parents = path.split('/')
        if parents[-2] == '':
            return self.root_dir
        parent_path = '/'.join(parents[:-2])
        return self.get_item(self.history[parent_path],parents[-2])

    def access_helper(self,path,full_path,item):
        items = self.df.get_all_files(parent=item['id'])
        self.df.create_meta_files(items,full_path)
        d_thread = threading.Thread(target = self.df.downloader,args = (full_path,items))
        d_thread.start()
        self.history[path] = items

    def access_threaded(self,path,full_path,parent_path):
        item = self.get_item(self.history[parent_path],os.path.basename(path))
        if item and item['extension'] == 'folder' and not path in self.history:
            self.history[path] = []
            f_thread = threading.Thread(target=self.access_helper,args=(path,full_path,item))
            f_thread.start()

        elif path in self.history:
            self.items = self.history[path]

    def mkdir_helper(self,path,parent_path):
        parent = self.find_parent(path)
        item = self.df.create_folder(os.path.basename(path),parent['id'])
        self.history[parent_path].append(item)

    def mkdir_threaded(self,path,parent_path):
        thread = threading.Thread(target=self.mkdir_helper,args=(path,parent_path))
        thread.start()