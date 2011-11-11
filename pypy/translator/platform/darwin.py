"""Support for OS X."""

import os

from pypy.translator.platform import posix

class Darwin(posix.BasePosix):
    name = "darwin"

    standalone_only = ('-mdynamic-no-pic',)
    shared_only = ()

    so_ext = 'dylib'

    # NOTE: GCC 4.2 will fail at runtime due to subtle issues, possibly
    # related to GC roots. Using LLVM-GCC or Clang will break the build.
    default_cc = 'gcc-4.0'

    def __init__(self, cc=None):
        if cc is None:
            try:
                cc = os.environ['CC']
            except KeyError:
                cc = self.default_cc
        self.cc = cc

    def _args_for_shared(self, args):
        return (list(self.shared_only)
                + ['-dynamiclib', '-undefined', 'dynamic_lookup']
                + args)
    
    def _include_dirs_for_libffi(self):
        return ['/usr/include/ffi']

    def _library_dirs_for_libffi(self):
        return ['/usr/lib']

    def check___thread(self):
        # currently __thread is not supported by Darwin gccs
        return False

    def _frameworks(self, frameworks):
        args = []
        for f in frameworks:
            args.append('-framework')
            args.append(f)
        return args

    def _link_args_from_eci(self, eci, standalone):
        args = super(Darwin, self)._link_args_from_eci(eci, standalone)
        frameworks = self._frameworks(eci.frameworks)
        include_dirs = self._includedirs(eci.include_dirs)
        return (args + frameworks + include_dirs)

    def _exportsymbols_link_flags(self, eci, relto=None):
        if not eci.export_symbols:
            return []

        response_file = self._make_response_file("dynamic-symbols-")
        f = response_file.open("w")
        for sym in eci.export_symbols:
            f.write("_%s\n" % (sym,))
        f.close()

        if relto:
            response_file = relto.bestrelpath(response_file)
        return ["-Wl,-exported_symbols_list,%s" % (response_file,)]

class Darwin_i386(Darwin):
    name = "darwin_i386"
    link_flags = ('-arch', 'i386')
    cflags = ('-arch', 'i386', '-O3', '-fomit-frame-pointer')

class Darwin_PowerPC(Darwin):#xxx fixme, mwp
    name = "darwin_powerpc"
    link_flags = ()
    cflags = ('-O3', '-fomit-frame-pointer')

class Darwin_x86_64(Darwin):
    name = "darwin_x86_64"
    link_flags = ('-arch', 'x86_64')
    cflags = ('-arch', 'x86_64', '-O3', '-fomit-frame-pointer')
