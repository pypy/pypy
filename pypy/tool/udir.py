#
# Common entry point to access a temporary directory (for testing, etc.)
# This uses the py lib's logic to create numbered directories.  The last
# three temporary directories are kept.
#

import autopath
import os

from py.path import local 

udir = local.make_numbered_dir(prefix='usession-', keep=3)

try:
    username = os.environ['USER']           #linux, et al
except:
    try:
        username = os.environ['USERNAME']   #windows
    except:
        username = 'current'

import os
src  = str(udir)
dest = src[:src.rfind('-')] + '-' + username
try:
    os.unlink(dest)
except:
    pass
try:
    os.symlink(src, dest)
except:
    pass
