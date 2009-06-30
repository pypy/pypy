
import py, os
from pypy.translator.platform import posix

class Darwin(posix.BasePosix):
    name = "darwin"
    
    link_flags = ['-mmacosx-version-min=10.4']
    cflags = ['-O3', '-fomit-frame-pointer', '-mmacosx-version-min=10.4']
    standalone_only = ['-mdynamic-no-pic']
    shared_only = []

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

    def _frameworks(self, frameworks):
        args = []
        for f in frameworks:
            args.append('-framework')
            args.append(f)
        return args

    def _link_args_from_eci(self, eci):
        args = super(Darwin, self)._link_args_from_eci(eci)
        frameworks = self._frameworks(eci.frameworks)
        include_dirs = self._includedirs(eci.include_dirs)
        return (args + frameworks + include_dirs)

