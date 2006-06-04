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
            st = os.stat(cls.from_rstr(path))
        except OSError:
            return False
        return True

    def ll_os_path_isdir(cls, path):
        try:
            (stat0, stat1, stat2, stat3, stat4,
             stat5, stat6, stat7, stat8, stat9) = os.stat(cls.from_rstr(path))
        except OSError:
            return False
        return stat.S_ISDIR(stat0)

