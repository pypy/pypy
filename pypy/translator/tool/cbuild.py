import py
import sys

from pypy.tool.autopath import pypydir
from pypy.translator.platform import host
from pypy.tool.udir import udir


class ExternalCompilationInfo(object):

    _ATTRIBUTES = ['pre_include_bits', 'includes', 'include_dirs',
                   'post_include_bits', 'libraries', 'library_dirs',
                   'separate_module_sources', 'separate_module_files',
                   'export_symbols', 'compile_extra', 'link_extra',
                   'frameworks', 'link_files', 'testonly_libraries']
    _DUPLICATES_OK = ['compile_extra', 'link_extra']
    _EXTRA_ATTRIBUTES = ['use_cpp_linker', 'platform']

    def __init__(self,
                 pre_include_bits        = [],
                 includes                = [],
                 include_dirs            = [],
                 post_include_bits       = [],
                 libraries               = [],
                 library_dirs            = [],
                 separate_module_sources = [],
                 separate_module_files   = [],
                 export_symbols          = [],
                 compile_extra           = [],
                 link_extra              = [],
                 frameworks              = [],
                 link_files              = [],
                 testonly_libraries      = [],
                 use_cpp_linker          = False,
                 platform                = None):
        """
        pre_include_bits: list of pieces of text that should be put at the top
        of the generated .c files, before any #include.  They shouldn't
        contain an #include themselves.  (Duplicate pieces are removed.)

        includes: list of .h file names to be #include'd from the
        generated .c files.

        include_dirs: list of dir names that is passed to the C compiler

        post_include_bits: list of pieces of text that should be put at the top
        of the generated .c files, after the #includes.  (Duplicate pieces are
        removed.)

        libraries: list of library names that is passed to the linker

        library_dirs: list of dir names that is passed to the linker

        separate_module_sources: list of multiline strings that are
        each written to a .c file and compiled separately and linked
        later on.  (If function prototypes are needed for other .c files
        to access this, they can be put in post_include_bits.)

        separate_module_files: list of .c file names that are compiled
        separately and linked later on.  (If an .h file is needed for
        other .c files to access this, it can be put in includes.)

        export_symbols: list of names that should be exported by the final
        binary.

        compile_extra: list of parameters which will be directly passed to
        the compiler

        link_extra: list of parameters which will be directly passed to
        the linker

        frameworks: list of Mac OS X frameworks which should passed to the
        linker. Use this instead of the 'libraries' parameter if you want to
        link to a framework bundle. Not suitable for unix-like .dylib
        installations.

        link_files: list of file names which will be directly passed to the
        linker

        testonly_libraries: list of libraries that are searched for during
        testing only, by ll2ctypes.  Useful to search for a name in a dynamic
        library during testing but use the static library for compilation.

        use_cpp_linker: a flag to tell if g++ should be used instead of gcc
        when linking (a bit custom so far)

        platform: an object that can identify the platform
        """
        for name in self._ATTRIBUTES:
            value = locals()[name]
            assert isinstance(value, (list, tuple))
            setattr(self, name, tuple(value))
        self.use_cpp_linker = use_cpp_linker
        if platform is None:
            from pypy.translator.platform import platform
        self.platform = platform

    def from_compiler_flags(cls, flags):
        """Returns a new ExternalCompilationInfo instance by parsing
        the string 'flags', which is in the typical Unix compiler flags
        format."""
        pre_include_bits = []
        include_dirs = []
        compile_extra = []
        for arg in flags.split():
            if arg.startswith('-I'):
                include_dirs.append(arg[2:])
            elif arg.startswith('-D'):
                macro = arg[2:]
                if '=' in macro:
                    macro, value = macro.split('=')
                else:
                    value = '1'
                pre_include_bits.append('#define %s %s' % (macro, value))
            elif arg.startswith('-L') or arg.startswith('-l'):
                raise ValueError('linker flag found in compiler options: %r'
                                 % (arg,))
            else:
                compile_extra.append(arg)
        return cls(pre_include_bits=pre_include_bits,
                   include_dirs=include_dirs,
                   compile_extra=compile_extra)
    from_compiler_flags = classmethod(from_compiler_flags)

    def from_linker_flags(cls, flags):
        """Returns a new ExternalCompilationInfo instance by parsing
        the string 'flags', which is in the typical Unix linker flags
        format."""
        libraries = []
        library_dirs = []
        link_extra = []
        for arg in flags.split():
            if arg.startswith('-L'):
                library_dirs.append(arg[2:])
            elif arg.startswith('-l'):
                libraries.append(arg[2:])
            elif arg.startswith('-I') or arg.startswith('-D'):
                raise ValueError('compiler flag found in linker options: %r'
                                 % (arg,))
            else:
                link_extra.append(arg)
        return cls(libraries=libraries,
                   library_dirs=library_dirs,
                   link_extra=link_extra)
    from_linker_flags = classmethod(from_linker_flags)

    def from_config_tool(cls, execonfigtool):
        """Returns a new ExternalCompilationInfo instance by executing
        the 'execonfigtool' with --cflags and --libs arguments."""
        path = py.path.local.sysfind(execonfigtool)
        if not path:
            raise ImportError("cannot find %r" % (execonfigtool,))
            # we raise ImportError to be nice to the pypy.config.pypyoption
            # logic of skipping modules depending on non-installed libs
        cflags = py.process.cmdexec('"%s" --cflags' % (str(path),))
        eci1 = cls.from_compiler_flags(cflags)
        libs = py.process.cmdexec('"%s" --libs' % (str(path),))
        eci2 = cls.from_linker_flags(libs)
        return eci1.merge(eci2)
    from_config_tool = classmethod(from_config_tool)

    def _value(self):
        return tuple([getattr(self, x)
                          for x in self._ATTRIBUTES + self._EXTRA_ATTRIBUTES])

    def __hash__(self):
        return hash(self._value())

    def __eq__(self, other):
        return self.__class__ is other.__class__ and \
               self._value() == other._value()

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        info = []
        for attr in self._ATTRIBUTES + self._EXTRA_ATTRIBUTES:
            val = getattr(self, attr)
            info.append("%s=%s" % (attr, repr(val)))
        return "<ExternalCompilationInfo (%s)>" % ", ".join(info)

    def merge(self, *others):
        def unique_elements(l):
            seen = set()
            new_objs = []
            for obj in l:
                if obj not in seen:
                    new_objs.append(obj)
                    seen.add(obj)
            return new_objs
        others = unique_elements(list(others))

        attrs = {}
        for name in self._ATTRIBUTES:
            if name in self._DUPLICATES_OK:
                s = []
                for i in [self] + others:
                    s += getattr(i, name)
                attrs[name] = s
            else:
                s = set()
                attr = []
                for one in [self] + others:
                    for elem in getattr(one, name):
                        if elem not in s:
                            s.add(elem)
                            attr.append(elem)
                attrs[name] = attr
        use_cpp_linker = self.use_cpp_linker
        for other in others:
            use_cpp_linker = use_cpp_linker or other.use_cpp_linker
        attrs['use_cpp_linker'] = use_cpp_linker
        for other in others:
            if other.platform != self.platform:
                raise Exception("Mixing ECI for different platforms %s and %s"%
                                (other.platform, self.platform))
        attrs['platform'] = self.platform
        return ExternalCompilationInfo(**attrs)

    def write_c_header(self, fileobj):
        print >> fileobj, STANDARD_DEFINES
        for piece in self.pre_include_bits:
            print >> fileobj, piece
        for path in self.includes:
            print >> fileobj, '#include <%s>' % (path,)
        for piece in self.post_include_bits:
            print >> fileobj, piece

    def _copy_attributes(self):
        d = {}
        for attr in self._ATTRIBUTES + self._EXTRA_ATTRIBUTES:
            d[attr] = getattr(self, attr)
        return d

    def convert_sources_to_files(self, cache_dir=None, being_main=False):
        if not self.separate_module_sources:
            return self
        if cache_dir is None:
            cache_dir = udir.join('module_cache').ensure(dir=1)
        num = 0
        files = []
        for source in self.separate_module_sources:
            while 1:
                filename = cache_dir.join('module_%d.c' % num)
                num += 1
                if not filename.check():
                    break
            f = filename.open("w")
            if being_main:
                f.write("#define PYPY_NOT_MAIN_FILE\n")
            self.write_c_header(f)
            source = str(source)
            f.write(source)
            if not source.endswith('\n'):
                f.write('\n')
            f.close()
            files.append(str(filename))
        d = self._copy_attributes()
        d['separate_module_sources'] = ()
        d['separate_module_files'] += tuple(files)
        return ExternalCompilationInfo(**d)

    def get_module_files(self):
        d = self._copy_attributes()
        files = d['separate_module_files']
        d['separate_module_files'] = ()
        return files, ExternalCompilationInfo(**d)

    def compile_shared_lib(self, outputfilename=None):
        self = self.convert_sources_to_files()
        if not self.separate_module_files:
            if sys.platform != 'win32':
                return self
            if not self.export_symbols:
                return self
            basepath = udir.join('module_cache')
        else:
            #basepath = py.path.local(self.separate_module_files[0]).dirpath()
            basepath = udir.join('shared_cache')
        if outputfilename is None:
            # find more or less unique name there
            pth = basepath.join('externmod').new(ext=host.so_ext)
            num = 0
            while pth.check():
                pth = basepath.join(
                    'externmod_%d' % (num,)).new(ext=host.so_ext)
                num += 1
            basepath.ensure(dir=1)
            outputfilename = str(pth.dirpath().join(pth.purebasename))
        lib = str(host.compile([], self, outputfilename=outputfilename,
                               standalone=False))
        d = self._copy_attributes()
        d['libraries'] += (lib,)
        d['separate_module_files'] = ()
        d['separate_module_sources'] = ()
        return ExternalCompilationInfo(**d)


# ____________________________________________________________
#
# This is extracted from pyconfig.h from CPython.  It sets the macros
# that affect the features we get from system include files.

STANDARD_DEFINES = '''
/* Define on Darwin to activate all library features */
#define _DARWIN_C_SOURCE 1
/* This must be set to 64 on some systems to enable large file support. */
#define _FILE_OFFSET_BITS 64
/* Define on Linux to activate all library features */
#define _GNU_SOURCE 1
/* This must be defined on some systems to enable large file support. */
#define _LARGEFILE_SOURCE 1
/* Define on NetBSD to activate all library features */
#define _NETBSD_SOURCE 1
/* Define to activate features from IEEE Stds 1003.1-2001 */
#define _POSIX_C_SOURCE 200112L
/* Define on FreeBSD to activate all library features */
#define __BSD_VISIBLE 1
#define __XSI_VISIBLE 700
/* Windows: winsock/winsock2 mess */
#define WIN32_LEAN_AND_MEAN
'''
