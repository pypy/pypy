
import py, os
from pypy.translator.platform import posix

class Freebsd7(posix.BasePosix):
    name = "freebsd7"
    
    link_flags = ['-pthread']
    cflags = ['-O3', '-pthread', '-fomit-frame-pointer']
    standalone_only = []
    shared_only = []
    so_ext = 'so'
    make_cmd = 'gmake'
    
    def _args_for_shared(self, args):
        return ['-shared'] + args

    def include_dirs_for_libffi(self):
        return ['/usr/local/include']

    def library_dirs_for_libffi(self):
        return ['/usr/local/lib']

class Freebsd7_64(Freebsd7):
    shared_only = ['-fPIC']
