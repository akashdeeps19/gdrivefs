# !/usr/bin/env python

from __future__ import with_statement

import os
import threading
import sys
import errno
from drive_facade import driveFacade
from fuse import FUSE, FuseOSError, Operations


class Passthrough(Operations):
    def __init__(self, root):
        self.root = root
        self.df = driveFacade()
        self.df.authenticate()
        self.items = self.df.get_all_files()
        self.df.downloader('root/',self.items)
        self.history = {'/':self.items}
        self.root_dir = {'id' : 'root', 'name' : '', 'extension' : 'folder'}
        self.threads = []
        self.f_threads = []
        # self.dir_list = {'/' : self.root_dir}

    # Helpers
    # =======

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def find_parent(self,path):
        parents = path.split('/')
        if parents[-2] == '':
            return self.root_dir
        return self.df.get_item(self.history['/'+parents[-3]],parents[-2])

    def find_parent_path(self,path):
        parent = path[:-len(os.path.basename(path))-1]
        if parent == '':
            return '/'
        return parent

    def thread_it(self,path,full_path,item):
        items = self.df.get_all_files(parent=item['id'])
        self.df.create_meta_files(items,full_path)
        self.threads.append(threading.Thread(target = self.df.downloader,args = (full_path,items)))
        self.threads[-1].start()
        self.history[path] = items

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        # print('access_start',path)
        full_path = self._full_path(path)
        parent = self.find_parent_path(path)
        # item = self.df.get_item(self.items,os.path.basename(path))
        item = self.df.get_item(self.history[parent],os.path.basename(path))
        # print(item)
        if item and item['extension'] == 'folder' and not path in self.history:
            # print(item)
            # self.items = self.df.get_all_files(parent=item['id'])
            # self.df.create_meta_files(self.items,full_path)
            # self.threads.append(threading.Thread(target = self.df.downloader,args = (full_path,self.items)))
            # self.threads[-1].start()
            # # if len(self.items):
            # self.history[path] = self.items
            self.f_threads.append(threading.Thread(target=self.thread_it,args=(path,full_path,item)))
            self.f_threads[-1].start()

        elif path in self.history:
            # print(path)
            self.items = self.history[path]
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        # print('get_attr',path)
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
    if not os.path.exists('./root'):
        os.mkdir('./root')
    FUSE(Passthrough('root'), mountpoint,foreground=True)

if __name__ == '__main__':
    main(sys.argv[1])