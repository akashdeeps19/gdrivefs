import os
import io
import threading
from drive_facade import driveFacade
from datetime import datetime

class fileMethods:
    def __init__(self):
        self.df = driveFacade()
        self.df.authenticate()
        self.items = self.df.get_all_files()
        self.create_meta_files(self.items,'src/root/')
        d_thread = threading.Thread(target = self.df.downloader,args=('src/root/',self.items))
        d_thread.start()
        self.history = {'/':self.items}
        self.download_threads = {'/' : d_thread}
        self.sync_threads = {}
        self.access_threads = {}
        self.root_dir = {'id' : 'root', 'name' : '', 'extension' : 'folder'}
    
    def get_item(self,items,name):
        if not items:
            return False
        for item in items:
            if item and item['name'] == name:
                return item
        return False

    def remove_item(self,items,name):
        if not items:
            return False
        for item in items:
            if item and item['name'] == name:
                items.remove(item)
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
        if type(items) != list:
            return
        for item in items:
            if not item:
                continue
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

    def sync_helper(self, path, full_path, item):
        if item:
            items = self.df.get_all_files(parent=item['id'])
        else: 
            items = self.df.get_all_files()
        if type(items) != list:
            return

        new_items = dict([(item['id'], item) for item in items])
        old_items = dict([(item['id'], item) for item in self.history.get(path, []) if item])

        diff = new_items.keys() - old_items.keys()
        diff = [new_items[item_id] for item_id in list(diff)]
        d_thread = threading.Thread(target = self.df.downloader,args = (full_path,diff))
        d_thread.start()

        diff = old_items.keys() - new_items.keys()
        diff = [old_items[item_id] for item_id in list(diff)]
        for item in list(diff):
            if item['extension'] == 'folder':
                os.rmdir(os.path.join(full_path, item['name']))
            else:
                os.remove(os.path.join(full_path, item['name']))

        same = set(old_items.keys()).intersection(new_items.keys())
        modified_files = []
        for item_id in same:
            new_mod_time = datetime.strptime(new_items[item_id]['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            old_mod_time = datetime.strptime(old_items[item_id]['modifiedTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
            if new_mod_time > old_mod_time:
                modified_files.append(new_items[item_id])
        d_thread = threading.Thread(target = self.df.downloader,args = (full_path,modified_files))
        d_thread.start()

        self.history[path] = items
    
    def sync_threaded(self, path, full_path, parent_path):
        if self.check_hidden(path):
            return

        item = self.get_item(self.history[parent_path],os.path.basename(path))
        if (item and item['extension'] == 'folder') or path == '/':
            if path in self.sync_threads and self.sync_threads[path].isAlive():
                return
            s_thread = threading.Thread(target=self.sync_helper,args=(path,full_path,item))
            s_thread.start()


    def access_helper(self,path,full_path,item):
        items = self.df.get_all_files(parent=item['id'])
        self.create_meta_files(items,full_path)
        if not path in self.download_threads or not self.download_threads[path].isAlive():
            d_thread = threading.Thread(target = self.df.downloader,args = (full_path,items))
            d_thread.start()
            self.download_threads[path] = d_thread
        self.history[path] = items

    def access_threaded(self,path,full_path,parent_path):
        if self.check_hidden(path):
            return

        item = self.get_item(self.history[parent_path],os.path.basename(path))
        if item and item['extension'] == 'folder' and not path in self.history:
            self.history[path] = []
            f_thread = threading.Thread(target=self.access_helper,args=(path,full_path,item))
            f_thread.start()
            # self.access_helper(path,full_path,item)
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

    def update_helper(self,path,full_path,parent_path):
        if self.check_hidden(path):
            return
        item = self.get_item(self.history[parent_path],os.path.basename(path))
        if not item:
            return
        self.df.update_file(file_id=item['id'], source=full_path)

    def update_threaded(self,path,full_path,parent_path):
        thread = threading.Thread(target=self.update_helper,args=(path,full_path,parent_path))
        thread.start()

    def rename_helper(self, path, new_path, parent_path):
        item = self.get_item(self.history[parent_path],os.path.basename(path))
        new_name = os.path.basename(new_path)
        if not item:
            return
        if item['extension'] == 'folder':
            self.history[new_name] = self.history[path][:]
            self.history.pop(path)

        item['name'] = new_name
        self.df.update_file(file_id=item['id'], metadata={'name' : new_name})

    def move_helper(self,old,new):
        item = self.remove_item(self.history[old['parent_path']], os.path.basename(old['path']))
        self.history[new['parent_path']].append(item)
        parent = self.find_parent(new['path'])
        self.df.move(item['id'], parent['id'])

    def move_threaded(self,old,new):
        if self.check_hidden(old['path']) or self.check_hidden(new['path']):
            return

        if old['parent_path'] == new['parent_path']:
            thread = threading.Thread(target=self.rename_helper, args=(old['path'], new['path'], old['parent_path']))
            thread.start()
        else:
            thread = threading.Thread(target=self.move_helper, args=(old, new))
            thread.start()
        

    def delete_helper(self,path,parent_path,mode = 'trash'):
        if self.check_hidden(path):
            return
        item = self.get_item(self.history[parent_path],os.path.basename(path))
        if not item:
            return
        if mode == 'trash':
            self.df.trash_file(item['id'])
        elif mode == 'delete':
            self.df.delete_file(item['id'])
        self.history[parent_path].remove(item)

    def delete_threaded(self,path,parent_path,mode = 'trash'):
        thread = threading.Thread(target=self.delete_helper,args=(path,parent_path),kwargs={'mode' : mode})
        thread.start()