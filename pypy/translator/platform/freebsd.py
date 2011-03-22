"""Support for FreeBSD."""

import os

from pypy.translator.platform import posix

def get_env(key, default):
    if key in os.environ:
        return os.environ[key]
    else:
        return default

def get_env_vector(key, default):
    string = get_env(key, default)
    # XXX: handle quotes
    return string.split()

class Freebsd(posix.BasePosix):
    name = "freebsd"

    link_flags = get_env_vector("LDFLAGS", '-pthread')
    cflags = get_env_vector("CFLAGS", "-O3 -pthread -fomit-frame-pointer")
    standalone_only = []
    shared_only = []
    so_ext = 'so'
    make_cmd = 'gmake'

    def __init__(self, cc=None):
        if cc is None:
            cc = get_env("CC", "gcc")
        super(Freebsd, self).__init__(cc)

    def _args_for_shared(self, args):
        return ['-shared'] + args

    def _preprocess_include_dirs(self, include_dirs):
        res_incl_dirs = list(include_dirs)
        res_incl_dirs.append(os.path.join(get_env("LOCALBASE", "/usr/local"), "include"))
        return res_incl_dirs

    def _preprocess_library_dirs(self, library_dirs):
        res_lib_dirs = list(library_dirs)
        res_lib_dirs.append(os.path.join(get_env("LOCALBASE", "/usr/local"), "lib"))
        return res_lib_dirs

    def _include_dirs_for_libffi(self):
        return [os.path.join(get_env("LOCALBASE", "/usr/local"), "include")]

    def _library_dirs_for_libffi(self):
        return [os.path.join(get_env("LOCALBASE", "/usr/local"), "lib")]

class Freebsd_64(Freebsd):
    shared_only = ('-fPIC',)
