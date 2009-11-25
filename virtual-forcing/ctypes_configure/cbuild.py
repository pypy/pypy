
import os, sys, inspect, re, imp, py
from ctypes_configure import stdoutcapture
import distutils

debug = 0

log = py.log.Producer("cbuild")

configdir = py.path.local.make_numbered_dir(prefix='ctypes_configure')

class ExternalCompilationInfo(object):

    _ATTRIBUTES = ['pre_include_lines', 'includes', 'include_dirs',
                   'post_include_lines', 'libraries', 'library_dirs',
                   'separate_module_sources', 'separate_module_files']
    _AVOID_DUPLICATES = ['separate_module_files', 'libraries', 'includes',
                         'include_dirs', 'library_dirs', 'separate_module_sources']

    def __init__(self,
                 pre_include_lines       = [],
                 includes                = [],
                 include_dirs            = [],
                 post_include_lines      = [],
                 libraries               = [],
                 library_dirs            = [],
                 separate_module_sources = [],
                 separate_module_files   = []):
        """
        pre_include_lines: list of lines that should be put at the top
        of the generated .c files, before any #include.  They shouldn't
        contain an #include themselves.

        includes: list of .h file names to be #include'd from the
        generated .c files.

        include_dirs: list of dir names that is passed to the C compiler

        post_include_lines: list of lines that should be put at the top
        of the generated .c files, after the #includes.

        libraries: list of library names that is passed to the linker

        library_dirs: list of dir names that is passed to the linker

        separate_module_sources: list of multiline strings that are
        each written to a .c file and compiled separately and linked
        later on.  (If function prototypes are needed for other .c files
        to access this, they can be put in post_include_lines.)

        separate_module_files: list of .c file names that are compiled
        separately and linked later on.  (If an .h file is needed for
        other .c files to access this, it can be put in includes.)
        """
        for name in self._ATTRIBUTES:
            value = locals()[name]
            assert isinstance(value, (list, tuple))
            setattr(self, name, tuple(value))

    def _value(self):
        return tuple([getattr(self, x) for x in self._ATTRIBUTES])

    def __hash__(self):
        return hash(self._value())

    def __eq__(self, other):
        return self.__class__ is other.__class__ and \
               self._value() == other._value()

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        info = []
        for attr in self._ATTRIBUTES:
            val = getattr(self, attr)
            info.append("%s=%s" % (attr, repr(val)))
        return "<ExternalCompilationInfo (%s)>" % ", ".join(info)

    def merge(self, *others):
        others = list(others)
        attrs = {}
        for name in self._ATTRIBUTES:
            if name not in self._AVOID_DUPLICATES:
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
        return ExternalCompilationInfo(**attrs)

    def write_c_header(self, fileobj):
        for line in self.pre_include_lines:
            print >> fileobj, line
        for path in self.includes:
            print >> fileobj, '#include <%s>' % (path,)
        for line in self.post_include_lines:
            print >> fileobj, line

    def _copy_attributes(self):
        d = {}
        for attr in self._ATTRIBUTES:
            d[attr] = getattr(self, attr)
        return d

    def convert_sources_to_files(self, cache_dir=None, being_main=False):
        if not self.separate_module_sources:
            return self
        if cache_dir is None:
            cache_dir = configdir.join('module_cache').ensure(dir=1)
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

    def compile_shared_lib(self):
        self = self.convert_sources_to_files()
        if not self.separate_module_files:
            return self
        lib = compile_c_module([], 'externmod', self)
        d = self._copy_attributes()
        d['libraries'] += (lib,)
        d['separate_module_files'] = ()
        d['separate_module_sources'] = ()
        return ExternalCompilationInfo(**d)

if sys.platform == 'win32':
    so_ext = '.dll'
else:
    so_ext = '.so'

def compiler_command():
    # e.g. for tcc, you might set this to
    #    "tcc -shared -o %s.so %s.c"
    return os.getenv('PYPY_CC')

def enable_fast_compilation():
    if sys.platform == 'win32':
        dash = '/'
    else:
        dash = '-'
    from distutils import sysconfig
    gcv = sysconfig.get_config_vars()
    opt = gcv.get('OPT') # not always existent
    if opt:
        opt = re.sub('%sO\d+' % dash, '%sO0' % dash, opt)
    else:
        opt = '%sO0' % dash
    gcv['OPT'] = opt

def ensure_correct_math():
    if sys.platform != 'win32':
        return # so far
    from distutils import sysconfig
    gcv = sysconfig.get_config_vars()
    opt = gcv.get('OPT') # not always existent
    if opt and '/Op' not in opt:
        opt += '/Op'
    gcv['OPT'] = opt


def try_compile(c_files, eci):
    try:
        build_executable(c_files, eci)
        result = True
    except (distutils.errors.CompileError,
            distutils.errors.LinkError):
        result = False
    return result

def compile_c_module(cfiles, modbasename, eci, tmpdir=None):
    #try:
    #    from distutils.log import set_threshold
    #    set_threshold(10000)
    #except ImportError:
    #    print "ERROR IMPORTING"
    #    pass
    cfiles = [py.path.local(f) for f in cfiles]
    if tmpdir is None:
        tmpdir = configdir.join("module_cache").ensure(dir=1)
    num = 0
    cfiles += eci.separate_module_files
    include_dirs = list(eci.include_dirs)
    library_dirs = list(eci.library_dirs)
    if sys.platform == 'darwin':    # support Fink & Darwinports
        for s in ('/sw/', '/opt/local/'):
            if s + 'include' not in include_dirs and \
               os.path.exists(s + 'include'):
                include_dirs.append(s + 'include')
            if s + 'lib' not in library_dirs and \
               os.path.exists(s + 'lib'):
                library_dirs.append(s + 'lib')

    num = 0
    modname = modbasename
    while 1:
        if not tmpdir.join(modname + so_ext).check():
            break
        num += 1
        modname = '%s_%d' % (modbasename, num)

    lastdir = tmpdir.chdir()
    libraries = eci.libraries
    ensure_correct_math()
    try:
        if debug: print "modname", modname
        c = stdoutcapture.Capture(mixed_out_err = True)
        try:
            try:
                if compiler_command():
                    # GCC-ish options only
                    from distutils import sysconfig
                    gcv = sysconfig.get_config_vars()
                    cmd = compiler_command().replace('%s',
                                                     str(tmpdir.join(modname)))
                    for dir in [gcv['INCLUDEPY']] + list(include_dirs):
                        cmd += ' -I%s' % dir
                    for dir in library_dirs:
                        cmd += ' -L%s' % dir
                    os.system(cmd)
                else:
                    from distutils.dist import Distribution
                    from distutils.extension import Extension
                    from distutils.ccompiler import get_default_compiler
                    saved_environ = os.environ.items()
                    try:
                        # distutils.core.setup() is really meant for end-user
                        # interactive usage, because it eats most exceptions and
                        # turn them into SystemExits.  Instead, we directly
                        # instantiate a Distribution, which also allows us to
                        # ignore unwanted features like config files.
                        extra_compile_args = []
                        # ensure correct math on windows
                        if sys.platform == 'win32':
                            extra_compile_args.append('/Op') # get extra precision
                        if get_default_compiler() == 'unix':
                            old_version = False
                            try:
                                g = os.popen('gcc --version', 'r')
                                verinfo = g.read()
                                g.close()
                            except (OSError, IOError):
                                pass
                            else:
                                old_version = verinfo.startswith('2')
                            if not old_version:
                                extra_compile_args.extend(["-Wno-unused-label",
                                                        "-Wno-unused-variable"])
                        attrs = {
                            'name': "testmodule",
                            'ext_modules': [
                                Extension(modname, [str(cfile) for cfile in cfiles],
                                    include_dirs=include_dirs,
                                    library_dirs=library_dirs,
                                    extra_compile_args=extra_compile_args,
                                    libraries=list(libraries),)
                                ],
                            'script_name': 'setup.py',
                            'script_args': ['-q', 'build_ext', '--inplace', '--force'],
                            }
                        dist = Distribution(attrs)
                        if not dist.parse_command_line():
                            raise ValueError, "distutils cmdline parse error"
                        dist.run_commands()
                    finally:
                        for key, value in saved_environ:
                            if os.environ.get(key) != value:
                                os.environ[key] = value
            finally:
                foutput, foutput = c.done()
                data = foutput.read()
                if data:
                    fdump = open("%s.errors" % modname, "w")
                    fdump.write(data)
                    fdump.close()
            # XXX do we need to do some check on fout/ferr?
            # XXX not a nice way to import a module
        except:
            print >>sys.stderr, data
            raise
    finally:
        lastdir.chdir()
    return str(tmpdir.join(modname) + so_ext)

def make_module_from_c(cfile, eci):
    cfile = py.path.local(cfile)
    modname = cfile.purebasename
    compile_c_module([cfile], modname, eci)
    return import_module_from_directory(cfile.dirpath(), modname)

def import_module_from_directory(dir, modname):
    file, pathname, description = imp.find_module(modname, [str(dir)])
    try:
        mod = imp.load_module(modname, file, pathname, description)
    finally:
        if file:
            file.close()
    return mod


def log_spawned_cmd(spawn):
    def spawn_and_log(cmd, *args, **kwds):
        if debug:
            log.execute(' '.join(cmd))
        return spawn(cmd, *args, **kwds)
    return spawn_and_log


class ProfOpt(object):
    #XXX assuming gcc style flags for now
    name = "profopt"
    
    def __init__(self, compiler):
        self.compiler = compiler

    def first(self):
        self.build('-fprofile-generate')

    def probe(self, exe, args):
        # 'args' is a single string typically containing spaces
        # and quotes, which represents several arguments.
        os.system("'%s' %s" % (exe, args))

    def after(self):
        self.build('-fprofile-use')

    def build(self, option):
        compiler = self.compiler
        compiler.compile_extra.append(option)
        compiler.link_extra.append(option)
        try:
            compiler._build()
        finally:
            compiler.compile_extra.pop()
            compiler.link_extra.pop()
            
class CCompiler:

    def __init__(self, cfilenames, eci, outputfilename=None,
                 compiler_exe=None, profbased=None):
        self.cfilenames = cfilenames
        ext = ''
        self.compile_extra = []
        self.link_extra = []
        self.libraries = list(eci.libraries)
        self.include_dirs = list(eci.include_dirs)
        self.library_dirs = list(eci.library_dirs)
        self.compiler_exe = compiler_exe
        self.profbased = profbased
        if not sys.platform in ('win32', 'darwin'): # xxx
            if 'm' not in self.libraries:
                self.libraries.append('m')
            if 'pthread' not in self.libraries:
                self.libraries.append('pthread')
            self.compile_extra += ['-O3', '-fomit-frame-pointer', '-pthread']
            self.link_extra += ['-pthread']
        if sys.platform == 'win32':
            self.link_extra += ['/DEBUG'] # generate .pdb file
        if sys.platform == 'darwin':
            # support Fink & Darwinports
            for s in ('/sw/', '/opt/local/'):
                if s + 'include' not in self.include_dirs and \
                   os.path.exists(s + 'include'):
                    self.include_dirs.append(s + 'include')
                if s + 'lib' not in self.library_dirs and \
                   os.path.exists(s + 'lib'):
                    self.library_dirs.append(s + 'lib')
            self.compile_extra += ['-O3', '-fomit-frame-pointer']

        if outputfilename is None:
            self.outputfilename = py.path.local(cfilenames[0]).new(ext=ext)
        else: 
            self.outputfilename = py.path.local(outputfilename)
        self.eci = eci

    def build(self, noerr=False):
        basename = self.outputfilename.new(ext='')
        data = ''
        try:
            saved_environ = os.environ.copy()
            try:
                c = stdoutcapture.Capture(mixed_out_err = True)
                self._build()
            finally:
                # workaround for a distutils bugs where some env vars can
                # become longer and longer every time it is used
                for key, value in saved_environ.items():
                    if os.environ.get(key) != value:
                        os.environ[key] = value
                foutput, foutput = c.done()
                data = foutput.read()
                if data:
                    fdump = basename.new(ext='errors').open("w")
                    fdump.write(data)
                    fdump.close()
        except:
            if not noerr:
                print >>sys.stderr, data
            raise
 
    def _build(self):
        from distutils.ccompiler import new_compiler 
        compiler = new_compiler(force=1)
        if self.compiler_exe is not None:
            for c in '''compiler compiler_so compiler_cxx
                        linker_exe linker_so'''.split():
                compiler.executables[c][0] = self.compiler_exe
        compiler.spawn = log_spawned_cmd(compiler.spawn)
        objects = []
        for cfile in self.cfilenames: 
            cfile = py.path.local(cfile)
            old = cfile.dirpath().chdir() 
            try: 
                res = compiler.compile([cfile.basename], 
                                       include_dirs=self.eci.include_dirs,
                                       extra_preargs=self.compile_extra)
                assert len(res) == 1
                cobjfile = py.path.local(res[0]) 
                assert cobjfile.check()
                objects.append(str(cobjfile))
            finally: 
                old.chdir() 
        compiler.link_executable(objects, str(self.outputfilename),
                                 libraries=self.eci.libraries,
                                 extra_preargs=self.link_extra,
                                 library_dirs=self.eci.library_dirs)

def build_executable(*args, **kwds):
    noerr = kwds.pop('noerr', False)
    compiler = CCompiler(*args, **kwds)
    compiler.build(noerr=noerr)
    return str(compiler.outputfilename)
