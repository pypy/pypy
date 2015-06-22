# ctypes implementation: Victor Stinner, 2008-05-08
"""
This module provides access to the Unix password database.
It is available on all Unix versions.

Password database entries are reported as 7-tuples containing the following
items from the password database (see `<pwd.h>'), in order:
pw_name, pw_passwd, pw_uid, pw_gid, pw_gecos, pw_dir, pw_shell.
The uid and gid items are integers, all others are strings. An
exception is raised if the entry asked for cannot be found.
"""

from _pwdgrp_cffi import ffi, lib
import _structseq

try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


class struct_passwd:
    """
    pwd.struct_passwd: Results from getpw*() routines.

    This object may be accessed either as a tuple of
      (pw_name,pw_passwd,pw_uid,pw_gid,pw_gecos,pw_dir,pw_shell)
    or via the object attributes as named in the above tuple.
    """
    __metaclass__ = _structseq.structseqtype
    name = "pwd.struct_passwd"

    pw_name = _structseq.structseqfield(0)
    pw_passwd = _structseq.structseqfield(1)
    pw_uid = _structseq.structseqfield(2)
    pw_gid = _structseq.structseqfield(3)
    pw_gecos = _structseq.structseqfield(4)
    pw_dir = _structseq.structseqfield(5)
    pw_shell = _structseq.structseqfield(6)


def _mkpwent(pw):
    return struct_passwd([
        ffi.string(pw.pw_name),
        ffi.string(pw.pw_passwd),
        pw.pw_uid,
        pw.pw_gid,
        ffi.string(pw.pw_gecos),
        ffi.string(pw.pw_dir),
        ffi.string(pw.pw_shell)])

@builtinify
def getpwuid(uid):
    """
    getpwuid(uid) -> (pw_name,pw_passwd,pw_uid,
                      pw_gid,pw_gecos,pw_dir,pw_shell)
    Return the password database entry for the given numeric user ID.
    See pwd.__doc__ for more on password database entries.
    """
    pw = lib.getpwuid(uid)
    if not pw:
        raise KeyError("getpwuid(): uid not found: %s" % uid)
    return _mkpwent(pw)

@builtinify
def getpwnam(name):
    """
    getpwnam(name) -> (pw_name,pw_passwd,pw_uid,
                        pw_gid,pw_gecos,pw_dir,pw_shell)
    Return the password database entry for the given user name.
    See pwd.__doc__ for more on password database entries.
    """
    if not isinstance(name, basestring):
        raise TypeError("expected string")
    name = str(name)
    pw = lib.getpwnam(name)
    if not pw:
        raise KeyError("getpwname(): name not found: %s" % name)
    return _mkpwent(pw)

@builtinify
def getpwall():
    """
    getpwall() -> list_of_entries
    Return a list of all available password database entries, in arbitrary order.
    See pwd.__doc__ for more on password database entries.
    """
    users = []
    lib.setpwent()
    while True:
        pw = lib.getpwent()
        if not pw:
            break
        users.append(_mkpwent(pw))
    lib.endpwent()
    return users

__all__ = ('struct_passwd', 'getpwuid', 'getpwnam', 'getpwall')

if __name__ == "__main__":
# Uncomment next line to test CPython implementation
#    from pwd import getpwuid, getpwnam, getpwall
    from os import getuid
    uid = getuid()
    pw = getpwuid(uid)
    print("uid %s: %s" % (pw.pw_uid, pw))
    name = pw.pw_name
    print("name %r: %s" % (name, getpwnam(name)))
    print("All:")
    for pw in getpwall():
        print(pw)
