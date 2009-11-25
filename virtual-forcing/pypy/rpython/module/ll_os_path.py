"""
Dummy low-level implementations for the external functions of the 'os.path' module.
"""

# see ll_os.py for comments

import stat
import os
from pypy.tool.staticmethods import ClassMethods

# Does a path exist?
# This is false for dangling symbolic links.

class BaseOsPath:
    __metaclass__ = ClassMethods

    def ll_os_path_exists(cls, path):
        """Test whether a path exists"""
        try:
            st = os.stat(cls.from_rstr_nonnull(path))
        except OSError:
            return False
        return True

    def ll_os_path_isdir(cls, path):
        try:
            st = os.stat(cls.from_rstr_nonnull(path))
        except OSError:
            return False
        return stat.S_ISDIR(st[0])

