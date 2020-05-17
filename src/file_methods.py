import os
import io
import threading
from drive_facade import driveFacade

class fileMethods:
    def __init__(self):
        self.df = driveFacade()
        self.df.authenticate()
        self.items = self.df.get_all_files()
        self.create_meta_files(self.items,'src/root/')
        d_thread = threading.Thread(target = self.df.downloader,args=('src/root/',self.items))
        d_thread.start()
        self.history = {'/':self.items}
        self.threads = {}
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
        if parent_path == '':
            parent_path = '/'
        return self.get_item(self.history[parent_path],parents[-2])

    def check_hidden(self,path):
        parents = path.split('/')
        for parent in parents:
            if len(parent) and parent[0] == '.':
                return True
        return False

    def create_meta_files(self,items,path): 
        for item in items:
            full_path = os.path.join(path,item['name'])
            if item['extension'] != 'folder':
                fh = io.FileIO(full_path,mode = 'w')
                fh.close()
            elif item['extension'] == 'folder' and not os.path.lexists(full_path):
                os.mkdir(full_path)

    def get_diff(self,path,full_path):
        hist_list = [item['name'] for item in self.history[path]]
        hist_set = set(hist_list)
        root_set = set(os.listdir(full_path))
        return root_set - hist_set , hist_set - root_set #(create , delete)

    def access_helper(self,path,full_path,item):
        items = self.df.get_all_files(parent=item['id'])
        self.create_meta_files(items,full_path)
        d_thread = threading.Thread(target = self.df.downloader,args = (full_path,items))
        d_thread.start()
        self.history[path] = items

    def access_threaded(self,path,full_path,parent_path):
        if self.check_hidden(path):
            return

        item = self.get_item(self.history[parent_path],os.path.basename(path))
        if item and item['extension'] == 'folder' and not path in self.history:
            self.history[path] = []
            f_thread = threading.Thread(target=self.access_helper,args=(path,full_path,item))
            f_thread.start()
        elif path in self.history:
            self.items = self.history[path]

    def mkdir_helper(self,path,parent_path):
        if self.check_hidden(path):
            return
        parent = self.find_parent(path)
        item = self.df.create_folder(os.path.basename(path),parent['id'])
        self.history[parent_path].append(item)

    def mkdir_threaded(self,path,parent_path):
        thread = threading.Thread(target=self.mkdir_helper,args=(path,parent_path))
        thread.start()

    def create_helper(self,path,full_path,parent_path):
        if self.check_hidden(path):
            return
        parent = self.find_parent(path)
        item = self.df.create_file(os.path.basename(path),parent['id'],full_path)
        self.history[parent_path].append(item)

    def create_threaded(self,path,full_path,parent_path):
        thread = threading.Thread(target=self.create_helper,args=(path,full_path,parent_path))
        thread.start()

    def delete_helper(self,path,parent_path,mode = 'trash'):
        if self.check_hidden(path):
            return
        item = self.get_item(self.history[parent_path],os.path.basename(path))
        if mode == 'trash':
            self.df.trash_file(item['id'])
        elif mode == 'delete':
            self.df.delete_file(item['id'])
        self.history[parent_path].remove(item)

    def delete_threaded(self,path,parent_path,mode = 'trash'):
        thread = threading.Thread(target=self.delete_helper,args=(path,parent_path),kwargs={'mode' : mode})
        thread.start()