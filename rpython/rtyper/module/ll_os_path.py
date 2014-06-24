"""
Dummy low-level implementations for the external functions of the 'os.path' module.
"""

# see ll_os.py for comments

import stat
import os

# Does a path exist?
# This is false for dangling symbolic links.

class BaseOsPath(object):
    @classmethod
    def ll_os_path_exists(cls, path):
        """Test whether a path exists"""
        try:
            os.stat(cls.from_rstr_nonnull(path))
        except OSError:
            return False
        return True

    @classmethod
    def ll_os_path_isdir(cls, path):
        try:
            st = os.stat(cls.from_rstr_nonnull(path))
        except OSError:
            return False
        return stat.S_ISDIR(st[0])
