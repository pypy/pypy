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


import os
from os.path import isabs, islink, abspath, normpath

def join(a, p):
    """Join two or more pathname components, inserting '/' as needed.
    If any component is an absolute path, all previous path components
    will be discarded.  An empty last part will result in a path that
    ends with a separator."""
    path = a
    for b in p:
        if b.startswith('/'):
            path = b
        elif path == '' or path.endswith('/'):
            path +=  b
        else:
            path += '/' + b
    return path

def realpath(filename):
    """Return the canonical path of the specified filename, eliminating any
symbolic links encountered in the path."""
    if isabs(filename):
        bits = ['/'] + filename.split('/')[1:]
    else:
        bits = [''] + filename.split('/')

    for i in range(2, len(bits)+1):
        component = join(bits[0], bits[1:i])
        # Resolve symbolic links.
        if islink(component):
            resolved = _resolve_link(component)
            if resolved is None:
                # Infinite loop -- return original component + rest of the path
                return abspath(join(component, bits[i:]))
            else:
                newpath = join(resolved, bits[i:])
                return realpath(newpath)

    return abspath(filename)


def _resolve_link(path):
    """Internal helper function.  Takes a path and follows symlinks
    until we either arrive at something that isn't a symlink, or
    encounter a path we've seen before (meaning that there's a loop).
    """
    paths_seen = {}
    while islink(path):
        if path in paths_seen:
            # Already seen this path, so we must have a symlink loop
            return None
        paths_seen[path] = None
        # Resolve where the link points to
        resolved = os.readlink(path)
        if not isabs(resolved):
            dir = dirname(path)
            path = normpath(join(dir, [resolved]))
        else:
            path = normpath(resolved)
    return path
