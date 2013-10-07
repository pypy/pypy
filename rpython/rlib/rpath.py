"""
Minimal (and limited) RPython version of some functions contained in os.path.
"""

import os.path
from rpython.rlib import rposix

if os.name == 'posix':
    # the posix version is already RPython, just use it
    # (but catch exceptions)
    def rabspath(path):
        try:
            return os.path.abspath(path)
        except OSError:
            return path
elif os.name == 'nt':
    def rabspath(path):
        if path == '':
            path = os.getcwd()
        try:
            return rposix._getfullpathname(path)
        except OSError:
            return path
else:
    raise ImportError('Unsupported os: %s' % os.name)


def dirname(p):
    """Returns the directory component of a pathname"""
    i = p.rfind('/') + 1
    assert i >= 0
    head = p[:i]
    if head and head != '/' * len(head):
        head = head.rstrip('/')
    return head


def basename(p):
    """Returns the final component of a pathname"""
    i = p.rfind('/') + 1
    assert i >= 0
    return p[i:]


def split(p):
    """Split a pathname.  Returns tuple "(head, tail)" where "tail" is
    everything after the final slash.  Either part may be empty."""
    i = p.rfind('/') + 1
    assert i >= 0
    head, tail = p[:i], p[i:]
    if head and head != '/' * len(head):
        head = head.rstrip('/')
    return head, tail


def exists(path):
    """Test whether a path exists.  Returns False for broken symbolic links"""
    try:
        assert path is not None
        os.stat(path)
    except os.error:
        return False
    return True
