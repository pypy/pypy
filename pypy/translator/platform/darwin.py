
import py, os
from pypy.translator.platform import posix

class Darwin(posix.BasePosix):
    name = "darwin"

    link_flags = ('-mmacosx-version-min=10.4',)
    cflags = ('-O3', '-fomit-frame-pointer', '-mmacosx-version-min=10.4')
    standalone_only = ('-mdynamic-no-pic',)
    shared_only = ()

    so_ext = 'so'
    
    default_cc = 'gcc'

    def __init__(self, cc=None):
        if cc is None:
            try:
                cc = os.environ['CC']
            except KeyError:
                cc = default_cc
        self.cc = cc

    def _args_for_shared(self, args):
        return (list(self.shared_only)
                + ['-dynamiclib', '-undefined', 'dynamic_lookup']
                + args)
    
    def _preprocess_include_dirs(self, include_dirs):
        res_incl_dirs = list(include_dirs)
        res_incl_dirs.append('/usr/local/include') # Homebrew
        res_incl_dirs.append('/opt/local/include') # MacPorts
        return res_incl_dirs

    def _preprocess_library_dirs(self, library_dirs):
        res_lib_dirs = list(library_dirs) 
        res_lib_dirs.append('/usr/local/lib') # Homebrew
        res_lib_dirs.append('/opt/local/lib') # MacPorts
        return res_lib_dirs

    def include_dirs_for_libffi(self):
        return ['/usr/include/ffi']

    def library_dirs_for_libffi(self):
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
    link_flags = ('-arch', 'i386', '-mmacosx-version-min=10.4')
    cflags = ('-arch', 'i386', '-O3', '-fomit-frame-pointer',
              '-mmacosx-version-min=10.4')

class Darwin_x86_64(Darwin):
    name = "darwin_x86_64"
    link_flags = ('-arch', 'x86_64', '-mmacosx-version-min=10.4')
    cflags = ('-arch', 'x86_64', '-O3', '-fomit-frame-pointer',
              '-mmacosx-version-min=10.4')
    default_cc = 'gcc-4.0'
