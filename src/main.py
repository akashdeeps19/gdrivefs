#!/usr/bin/env python

import os
import sys
import errno

from fuse import FUSE, FuseOSError, Operations
from Passthrough import Passthrough

class dfs(Passthrough):
    def __init__(self, root, fallbackPath):
        self.root = root
        self.fallbackPath = fallbackPath
        
    # Helpers
    # =======
    def _full_path(self, partial, useFallBack=False):
        if partial.startswith("/"):
            partial = partial[1:]
        # Find out the real path. If has been requesetd for a fallback path,
        # use it
        path = primaryPath = os.path.join(
            self.fallbackPath if useFallBack else self.root, partial)
        # If the pah does not exists and we haven't been asked for the fallback path
        # try to look on the fallback filessytem
        if not os.path.exists(primaryPath) and not useFallBack:
            path = fallbackPath = os.path.join(self.fallbackPath, partial)
            # If the path does not exists neither in the fallback fielsysem
            # it's likely to be a write operation, so use the primary
            # filesystem... unless the path to get the file exists in the
            # fallbackFS!
            if not os.path.exists(fallbackPath):
                # This is probabily a write operation, so prefer to use the
                # primary path either if the directory of the path exists in the
                # primary FS or not exists in the fallback FS
                primaryDir = os.path.dirname(primaryPath)
                fallbackDir = os.path.dirname(fallbackPath)
                if os.path.exists(primaryDir) or not os.path.exists(fallbackDir):
                    path = primaryPath
        return path
      
    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                                                        'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid', 'st_blocks')) 

    def readdir(self, path, fh):
        dirents = ['.', '..']
        full_path = self._full_path(path)
        # print("listing " + full_path)
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        if self.fallbackPath not in full_path:
            full_path = self._full_path(path, useFallBack=True)
            # print("listing_ext " + full_path)
            if os.path.isdir(full_path):
                dirents.extend(os.listdir(full_path))
        for r in list(set(dirents)):
            yield r
            
def main(mountpoint, root, fallbackPath):
    FUSE(dfs(root, fallbackPath), mountpoint, nothreads=True,
         foreground=True, **{'allow_other': True})

if __name__ == '__main__':
    mountpoint = sys.argv[3]
    root = sys.argv[1]
    fallbackPath = sys.argv[2]
    main(mountpoint, root, fallbackPath)