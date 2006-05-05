"""
Dummy low-level implementations for the external functions of the 'os.path' module.
"""

# see ll_os.py for comments

import os
import stat
from pypy.rpython.module.support import to_rstr, from_rstr, ll_strcpy
from pypy.rpython.module.ll_os import ll_os_stat

# Does a path exist?
# This is false for dangling symbolic links.

def ll_os_path_exists(path):
    """Test whether a path exists"""
    try:
        st = ll_os_stat(path)
    except OSError:
        return False
    return True

def ll_os_path_isdir(path):
    try:
        st = ll_os_stat(path)
    except OSError:
        return False
    return stat.S_ISDIR(st.item0)

