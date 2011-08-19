"""Support for OpenBSD."""

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

class OpenBSD(posix.BasePosix):
    name = "openbsd"

    link_flags = get_env_vector("LDFLAGS", '-pthread')
    cflags = get_env_vector("CFLAGS", "-O3 -pthread -fomit-frame-pointer -D_BSD_SOURCE")
    standalone_only = []
    shared_only = []
    so_ext = 'so'
    make_cmd = 'gmake'

    def __init__(self, cc=None):
        if cc is None:
            cc = get_env("CC", "gcc")
        super(OpenBSD, self).__init__(cc)

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

    def _libs(self, libraries):
        libraries=set(libraries + ("intl", "iconv", "compat"))
        return ['-l%s' % lib for lib in libraries if lib not in ["crypt", "dl", "rt"]]

    def check___thread(self):
        # currently __thread is not supported by Darwin gccs
        return False

class OpenBSD_64(OpenBSD):
    shared_only = ('-fPIC',)
