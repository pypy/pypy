"""
Dummy low-level implementations for the external functions of the 'os.path' module.
"""

# see ll_os.py for comments

import os
from pypy.rpython.rstr import STR
from pypy.rpython.module.ll_os import from_rstr


# Does a path exist?
# This is false for dangling symbolic links.

def ll_os_path_exists(path):
    """Test whether a path exists"""
    try:
        st = os.stat(from_rstr(path))
    except os.error:
        return False
    return True
