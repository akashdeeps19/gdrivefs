from __future__ import print_function, absolute_import, division

import logging

from collections import defaultdict
from errno import ENOENT
import stat
from sys import argv, exit
from time import time


#from fuse import FUSE, FuseOSError, Operations

#Manages files locally and uses a DriveFacade in order to communicate with Google Drive and to ensure consistency between the local and remote state.