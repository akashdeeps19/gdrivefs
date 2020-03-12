from __future__ import with_statement

import os
import sys
import config
from drive_facade import driveFacade
from threading import *
import errno
from datetime import datetime
from fuse import FUSE, FuseOSError, Operations

from file_manager import file_manager 


# An empty FUSE file system. It can be used in a mounting test aimed to determine whether or
# not the real file system can be mounted as well. If the test fails, the application can fail
# early instead of wasting time constructing the real file system.

class file_system(Operations):

    def __init__(self, root):
        self.time=0
        self.root = root
        self.last_sync = datetime.now()
        self.sync_interval = config.SYNC_INTERVAL
        self.df = driveFacade()
        self.df.authenticate()

        self.files = self.df.get_all_files()
        self.df.downloader('root/',self.files)
        self.history = {'/':self.files}
        self.root_dir = {'id' : 'root', 'name' : '', 'extension' : 'folder'}

    def _full_path(self,partial):
        if(partial.startswith("/")):
            partial=partial[1:]
        path=os.path.join(self.root,partial)
        return path

    
    def find_parent(self,path):
        parents = path.split('/')
        if parents[-2] == '':
            return self.root_dir
        return self.df.get_item(self.history['/'+parents[-3]],parents[-2])


    # Filesystem methods
    # ==================

    def access(self, path, mode):
        print("access called ",self.time)
        self.time+=1
        full_path = self._full_path(path)
        item = self.df.get_item(self.files,os.path.basename(path))
        if item and item['extension'] == 'folder' and not path in self.history:
            self.files = self.df.get_all_files(parent=item['id'])
            self.df.downloader(full_path,self.files)
            self.history[path] = self.files
        elif path in self.history:
            self.files = self.history[path]
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        full_path = self._full_path(path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
        parent = self.find_parent(path)
        item = self.df.create_folder(os.path.basename(path),parent['id'])
        self.history['/'+parent['name']].append(item)
        return os.mkdir(self._full_path(path), mode)

    def statfs(self, path):
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def unlink(self, path):
        return os.unlink(self._full_path(path))

    def symlink(self, name, target):
        return os.symlink(name, self._full_path(target))

    def rename(self, old, new):
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name):
        return os.link(self._full_path(target), self._full_path(name))

    def utimens(self, path, times=None):
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        full_path = self._full_path(path)
        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        return os.fsync(fh)

    def release(self, path, fh):
        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        return self.flush(path, fh)


def main(mountpoint):
    FUSE(file_system('root'), mountpoint, nothreads=True, foreground=True)

if __name__ == '__main__':
    main(sys.argv[1])