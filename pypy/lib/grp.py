
""" This module provides ctypes version of cpython's grp module
"""

import sys
if sys.platform == 'win32':
    raise ImportError("No grp module on Windows")

from ctypes import Structure, c_char_p, c_int, POINTER
from ctypes_support import standard_c_lib as libc

gid_t = c_int

class GroupStruct(Structure):
    _fields_ = (
        ('gr_name', c_char_p),
        ('gr_passwd', c_char_p),
        ('gr_gid', gid_t),
        ('gr_mem', POINTER(c_char_p)),
        )

class Group(object):
    def __init__(self, gr_name, gr_passwd, gr_gid, gr_mem):
        self.gr_name = gr_name
        self.gr_passwd = gr_passwd
        self.gr_gid = gr_gid
        self.gr_mem = gr_mem

    def __getitem__(self, item):
        if item == 0:
            return self.gr_name
        elif item == 1:
            return self.gr_passwd
        elif item == 2:
            return self.gr_gid
        elif item == 3:
            return self.gr_mem
        else:
            raise IndexError(item)

    def __len__(self):
        return 4

    def __repr__(self):
        return str((self.gr_name, self.gr_passwd, self.gr_gid, self.gr_mem))

    # whatever else...

libc.getgrgid.argtypes = [gid_t]
libc.getgrgid.restype = POINTER(GroupStruct)

libc.getgrnam.argtypes = [c_char_p]
libc.getgrnam.restype = POINTER(GroupStruct)

libc.getgrent.argtypes = []
libc.getgrent.restype = POINTER(GroupStruct)

def _group_from_gstruct(res):
    i = 0
    mem = []
    while res.contents.gr_mem[i]:
        mem.append(res.contents.gr_mem[i])
        i += 1
    return Group(res.contents.gr_name, res.contents.gr_passwd,
                 res.contents.gr_gid, mem)

def getgrgid(gid):
    res = libc.getgrgid(gid)
    if not res:
        # XXX maybe check error eventually
        raise KeyError(gid)
    return _group_from_gstruct(res)

def getgrnam(name):
    if not isinstance(name, str):
        raise TypeError("expected string")
    res = libc.getgrnam(name)
    if not res:
        raise KeyError(name)
    return _group_from_gstruct(res)

def getgrall():
    libc.setgrent()
    lst = []
    while 1:
        p = libc.getgrent()
        if not p:
            libc.endgrent()
            return lst
        lst.append(_group_from_gstruct(p))
