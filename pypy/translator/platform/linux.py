
import py, os
from pypy.translator.platform import Platform, CompilationError, ExecutionResult
from pypy.translator.platform import log, _run_subprocess
from pypy.tool import autopath
from pypy.translator.platform.posix import GnuMakefile, BasePosix

class Linux(BasePosix):
    name = "linux"
    
    link_flags = ['-pthread', '-lrt']
    cflags = ['-O3', '-pthread', '-fomit-frame-pointer']
    standalone_only = []
    shared_only = ['-fPIC']
    so_ext = 'so'
    so_prefixes = ['lib', '']
    
    def _args_for_shared(self, args):
        return ['-shared'] + args

    def include_dirs_for_libffi(self):
        return ['/usr/include/libffi']

    def library_dirs_for_libffi(self):
        return ['/usr/lib/libffi']

    def library_dirs_for_libffi_a(self):
        # places where we need to look for libffi.a
        return self.library_dirs_for_libffi() + ['/usr/lib']


class Linux64(Linux):
    shared_only = ['-fPIC']
