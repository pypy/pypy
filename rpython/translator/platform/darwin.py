"""Support for OS X."""

from rpython.translator.platform import posix

class Darwin(posix.BasePosix):
    name = "darwin"

    standalone_only = ('-mdynamic-no-pic',)
    shared_only = ()

    so_ext = 'dylib'
    DEFAULT_CC = 'clang'
    rpath_flags = ['-Wl,-rpath', '-Wl,@executable_path/']

    def _args_for_shared(self, args):
        return (list(self.shared_only)
                + ['-dynamiclib', '-install_name', '@rpath/$(TARGET)', '-undefined', 'dynamic_lookup']
                + args)

    def _include_dirs_for_libffi(self):
        return ['/usr/include/ffi']

    def _library_dirs_for_libffi(self):
        return ['/usr/lib']

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

    def gen_makefile(self, cfiles, eci, exe_name=None, path=None,
                     shared=False, headers_to_precompile=[],
                     no_precompile_cfiles = []):
        # ensure frameworks are passed in the Makefile
        fs = self._frameworks(eci.frameworks)
        if len(fs) > 0:
            # concat (-framework, FrameworkName) pairs
            self.extra_libs += tuple(map(" ".join, zip(fs[::2], fs[1::2])))
        mk = super(Darwin, self).gen_makefile(cfiles, eci, exe_name, path,
                                shared=shared,
                                headers_to_precompile=headers_to_precompile,
                                no_precompile_cfiles = no_precompile_cfiles)
        return mk


class Darwin_i386(Darwin):
    name = "darwin_i386"
    link_flags = ('-arch', 'i386', '-mmacosx-version-min=10.4')
    cflags = ('-arch', 'i386', '-O3', '-fomit-frame-pointer',
              '-mmacosx-version-min=10.4')

class Darwin_PowerPC(Darwin):#xxx fixme, mwp
    name = "darwin_powerpc"
    link_flags = ()
    cflags = ('-O3', '-fomit-frame-pointer')

class Darwin_x86_64(Darwin):
    name = "darwin_x86_64"
    link_flags = ('-arch', 'x86_64', '-mmacosx-version-min=10.5')
    cflags = ('-arch', 'x86_64', '-O3', '-fomit-frame-pointer',
              '-mmacosx-version-min=10.5')
