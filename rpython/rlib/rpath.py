"""
Minimal (and limited) RPython version of some functions contained in os.path.
"""

import os
from rpython.rlib import rposix


def _posix_risabs(s):
    """Test whether a path is absolute"""
    return s.startswith('/')

def _posix_rabspath(path):
    """Return an absolute, **non-normalized** path.
      **This version does not let exceptions propagate.**"""
    try:
        if not _posix_risabs(path):
            cwd = os.getcwd()
            path = _posix_rjoin(cwd, path)
        return path
    except OSError:
        return path

def _posix_rjoin(a, b):
    """Join two pathname components, inserting '/' as needed.
    If the second component is an absolute path, the first one
    will be discarded.  An empty last part will result in a path that
    ends with a separator."""
    path = a
    if b.startswith('/'):
        path = b
    elif path == '' or path.endswith('/'):
        path +=  b
    else:
        path += '/' + b
    return path


def _nt_risabs(s):
    """Test whether a path is absolute"""
    s = _nt_rsplitdrive(s)[1]
    return s.startswith('/') or s.startswith('\\')

def _nt_rabspath(path):
    try:
        if path == '':
            path = os.getcwd()
        return rposix._getfullpathname(path)
    except OSError:
        return path

def _nt_rsplitdrive(p):
    """Split a pathname into drive/UNC sharepoint and relative path
    specifiers.
    Returns a 2-tuple (drive_or_unc, path); either part may be empty.
    """
    if len(p) > 1:
        normp = p.replace(altsep, sep)
        if normp.startswith('\\\\') and not normp.startswith('\\\\\\'):
            # is a UNC path:
            # vvvvvvvvvvvvvvvvvvvv drive letter or UNC path
            # \\machine\mountpoint\directory\etc\...
            #           directory ^^^^^^^^^^^^^^^
            index = normp.find('\\', 2)
            if index < 0:
                return '', p
            index2 = normp.find('\\', index + 1)
            # a UNC path can't have two slashes in a row
            # (after the initial two)
            if index2 == index + 1:
                return '', p
            if index2 < 0:
                index2 = len(p)
            return p[:index2], p[index2:]
        if normp[1] == ':':
            return p[:2], p[2:]
    return '', p

def _nt_rjoin(path, p):
    """Join two or more pathname components, inserting "\\" as needed."""
    result_drive, result_path = _nt_rsplitdrive(path)
    p_drive, p_path = _nt_rsplitdrive(p)
    p_is_rel = True
    if p_path and p_path[0] in '\\/':
        # Second path is absolute
        if p_drive or not result_drive:
            result_drive = p_drive
        result_path = p_path
        p_is_rel = False
    elif p_drive and p_drive != result_drive:
        if p_drive.lower() != result_drive.lower():
            # Different drives => ignore the first path entirely
            result_drive = p_drive
            result_path = p_path
            p_is_rel = False
        else:
            # Same drive in different case
            result_drive = p_drive
    if p_is_rel:
        # Second path is relative to the first
        if result_path and result_path[-1] not in '\\/':
            result_path = result_path + '\\'
        result_path = result_path + p_path
    ## add separator between UNC and non-absolute path
    if (result_path and result_path[0] not in '\\/' and
        result_drive and result_drive[-1] != ':'):
        return result_drive + '\\' + result_path
    return result_drive + result_path


if os.name == 'posix':
    sep = altsep = '/'
    risabs      = _posix_risabs
    rabspath    = _posix_rabspath
    rjoin       = _posix_rjoin
elif os.name == 'nt':
    sep, altsep = '\\', '/'
    risabs      = _nt_risabs
    rabspath    = _nt_rabspath
    rsplitdrive = _nt_rsplitdrive
    rjoin       = _nt_rjoin
else:
    raise ImportError('Unsupported os: %s' % os.name)
