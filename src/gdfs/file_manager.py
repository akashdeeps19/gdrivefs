# !/usr/bin/env python

from __future__ import with_statement

import os
import sys
import config
import errno
from datetime import datetime
from drive_facade import driveFacade
from fuse import FUSE, FuseOSError, Operations

#Manages files locally and uses a DriveFacade in order to communicate with Google Drive and to ensure consistency between the local and remote state.
class file_manager():

    def find_parent(self,path):
        parents = path.split('/')
        if parents[-2] == '':
            return self.root_dir
        return self.df.get_item(self.history['/'+parents[-3]],parents[-2])
        
    def sync(self):
        if (datetime.now() - self.last_sync) < self.sync_interval:
            print("Not enough time has passed since last sync, will do nothing")
            return
        
        print("Checking for changes...")
        self.last_sync = datetime.now()

        full_path = self._full_path(self.root)
        item = self.df.get_item(self.items,os.path.basename(self.root))

        for change in self.df.get_changes():
            file_id = change.file_id

            if not self.history.__contains__(file_id):
                print("New file found from drive, creating locally...")
                self.items = self.df.get_all_files(parent=item['id'])
                self.df.downloader(full_path, self.items)
                self.history[self.root] = self.items




