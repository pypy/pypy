
""" This module provides ctypes version of cpython's grp module
"""

from _pwdgrp_cffi import ffi, lib
import _structseq
import thread
_lock = thread.allocate_lock()

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


class struct_group:
    __metaclass__ = _structseq.structseqtype
    name = "grp.struct_group"

    gr_name   = _structseq.structseqfield(0)
    gr_passwd = _structseq.structseqfield(1)
    gr_gid    = _structseq.structseqfield(2)
    gr_mem    = _structseq.structseqfield(3)


def _group_from_gstruct(res):
    i = 0
    members = []
    while res.gr_mem[i]:
        members.append(ffi.string(res.gr_mem[i]))
        i += 1
    return struct_group([
        ffi.string(res.gr_name),
        ffi.string(res.gr_passwd),
        res.gr_gid,
        members])

@builtinify
def getgrgid(gid):
    with _lock:
        res = lib.getgrgid(gid)
        if not res:
            # XXX maybe check error eventually
            raise KeyError(gid)
        return _group_from_gstruct(res)

@builtinify
def getgrnam(name):
    name = str(name)
    with _lock:
        res = lib.getgrnam(name)
        if not res:
            raise KeyError("getgrnam(): name not found: %s" % name)
        return _group_from_gstruct(res)

@builtinify
def getgrall():
    lst = []
    with _lock:
        lib.setgrent()
        while 1:
            p = lib.getgrent()
            if not p:
                break
            lst.append(_group_from_gstruct(p))
        lib.endgrent()
    return lst

__all__ = ('struct_group', 'getgrgid', 'getgrnam', 'getgrall')

if __name__ == "__main__":
    from os import getgid
    gid = getgid()
    pw = getgrgid(gid)
    print("gid %s: %s" % (pw.gr_gid, pw))
    name = pw.gr_name
    print("name %r: %s" % (name, getgrnam(name)))
    print("All:")
    for pw in getgrall():
        print(pw)
