"""Support for Linux."""

import os
import platform
import sys
from rpython.translator.platform.posix import BasePosix

class Linux(BasePosix):
    name = "linux"

    link_flags = tuple(
                 ['-pthread',]
                 + os.environ.get('LDFLAGS', '').split())
    extra_libs = ('-lrt',)
    cflags = tuple(
             ['-O3', '-pthread', '-fomit-frame-pointer',
              '-Wall', '-Wno-unused', '-Wno-address',
              '-Wno-discarded-qualifiers',  # RPyField does not know about const
              # The parser turns 'const char *const *includes' into 'const const char **includes'
              '-Wno-duplicate-decl-specifier',
              # These make older gcc  behave like gcc-14
              '-Werror=incompatible-pointer-types', '-Werror=implicit',
              '-Werror=int-conversion',
             ]
             + os.environ.get('CFLAGS', '').split())
    standalone_only = ()
    shared_only = ('-fPIC',)
    so_ext = 'so'

    if platform.machine() == 's390x':
        from rpython.translator.platform.arch import s390x
        cflags = s390x.update_cflags(cflags)

    def _args_for_shared(self, args, **kwds):
        return ['-shared'] + args

    def _include_dirs_for_libffi(self):
        return self._pkg_config("libffi", "--cflags-only-I",
                                ['/usr/include/libffi'],
                                check_result_dir=True)

    def _library_dirs_for_libffi(self):
        return self._pkg_config("libffi", "--libs-only-L",
                                ['/usr/lib/libffi'],
                                check_result_dir=True)
