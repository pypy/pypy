
import py, os
from pypy.translator.platform import posix

class Darwin(posix.BasePosix):
    name = "darwin"
    
    link_flags = []
    cflags = ['-O3', '-fomit-frame-pointer']
    standalone_only = ['-mdynamic-no-pic']
    shared_only = ['-mmacosx-version-min=10.4']

    so_ext = 'so'
    
    def __init__(self, cc=None):
        if cc is None:
            cc = 'gcc'
        self.cc = cc

    def _args_for_shared(self, args):
        return (self.shared_only + ['-bundle', '-undefined', 'dynamic_lookup']
                                 + args)

    def include_dirs_for_libffi(self):
        return ['/usr/include/ffi']

    def library_dirs_for_libffi(self):
        return []

    def check___thread(self):
        # currently __thread is not supported by Darwin gccs
        return False

