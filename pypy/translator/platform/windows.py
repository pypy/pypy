
import py, os, sys
from pypy.translator.platform import CompilationError, ExecutionResult
from pypy.translator.platform import log, _run_subprocess
from pypy.translator.platform import Platform, posix
from pypy.tool import autopath

def _install_msvc_env():
    # The same compiler must be used for the python interpreter
    # and extension modules
    msc_pos = sys.version.find('MSC v.')
    if msc_pos == -1:
        # Not a windows platform...
        return

    msc_ver = int(sys.version[msc_pos+6:msc_pos+10])
    # 1300 -> 70, 1310 -> 71, 1400 -> 80, 1500 -> 90
    vsver = (msc_ver / 10) - 60
    toolsdir = os.environ['VS%sCOMNTOOLS' % vsver]
    vcvars = os.path.join(toolsdir, 'vsvars32.bat')

    import subprocess
    popen = subprocess.Popen('"%s" & set' % (vcvars,),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

    stdout, stderr = popen.communicate()
    if popen.wait() != 0:
        raise IOError(stderr)
    for line in stdout.split("\n"):
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key.upper() in ['PATH', 'INCLUDE', 'LIB']:
            os.environ[key] = value
            log.msg(line)
    log.msg("Updated environment with %s" % (vcvars,))

try:
    _install_msvc_env()
except Exception, e:
    print >>sys.stderr, "Could not find a suitable Microsoft Compiler"
    import traceback
    traceback.print_exc()
    # Assume that the compiler is already part of the environment

class Windows(Platform):
    name = "win32"
    so_ext = 'dll'
    exe_ext = 'exe'

    cc = 'cl.exe'
    link = 'link.exe'

    cflags = ['/MD']
    link_flags = []
    standalone_only = []
    shared_only = []

    def __init__(self, cc=None):
        self.cc = 'cl.exe'

        # Install debug options only when interpreter is in debug mode
        if sys.executable.lower().endswith('_d.exe'):
            self.cflags = ['/MDd', '/Z7']
            self.link_flags = ['/debug']

        self.add_cpython_dirs = True

    def _preprocess_dirs(self, include_dirs):
        if self.add_cpython_dirs:
            return include_dirs + (py.path.local(sys.exec_prefix).join('PC'),)
        return include_dirs

    def _includedirs(self, include_dirs):
        return ['/I%s' % (idir,) for idir in include_dirs]

    def _libs(self, libraries):
        return ['%s.lib' % (lib,) for lib in libraries]

    def _libdirs(self, library_dirs):
        if self.add_cpython_dirs:
            library_dirs = library_dirs + (
                py.path.local(sys.exec_prefix).join('libs'),
                py.path.local(sys.executable).dirpath(),
                )
        return ['/LIBPATH:%s' % (ldir,) for ldir in library_dirs]

    def _args_for_shared(self, args):
        return ['/dll'] + args

    def _link_args_from_eci(self, eci):
        args = super(Windows, self)._link_args_from_eci(eci)
        return args + ['/EXPORT:%s' % symbol for symbol in eci.export_symbols]

    def _compile_c_file(self, cc, cfile, compile_args):
        oname = cfile.new(ext='obj')
        args = ['/nologo', '/c'] + compile_args + [str(cfile), '/Fo%s' % (oname,)]
        self._execute_c_compiler(cc, args, oname)
        return oname

    def _link(self, cc, ofiles, link_args, standalone, exe_name):
        args = ['/nologo'] + [str(ofile) for ofile in ofiles] + link_args
        args += ['/out:%s' % (exe_name,)]
        if not standalone:
            args = self._args_for_shared(args)
        self._execute_c_compiler(self.link, args, exe_name)
        return exe_name

    def _handle_error(self, returncode, stderr, stdout, outname):
        if returncode != 0:
            # Microsoft compilers write compilation errors to stdout
            stderr = stdout + stderr
            errorfile = outname.new(ext='errors')
            errorfile.write(stderr)
            stderrlines = stderr.splitlines()
            for line in stderrlines[:5]:
                log.ERROR(line)
            if len(stderrlines) > 5:
                log.ERROR('...')
            raise CompilationError(stdout, stderr)


    def gen_makefile(self, cfiles, eci, exe_name=None, path=None):
        cfiles = [py.path.local(f) for f in cfiles]
        cfiles += [py.path.local(f) for f in eci.separate_module_files]

        if path is None:
            path = cfiles[0].dirpath()

        pypypath = py.path.local(autopath.pypydir)

        if exe_name is None:
            exe_name = cfiles[0].new(ext=self.exe_ext)

        m = NMakefile(path)
        m.exe_name = exe_name
        m.eci = eci

        def pypyrel(fpath):
            rel = py.path.local(fpath).relto(pypypath)
            if rel:
                return os.path.join('$(PYPYDIR)', rel)
            else:
                return fpath

        rel_cfiles = [m.pathrel(cfile) for cfile in cfiles]
        rel_ofiles = [rel_cfile[:-2]+'.obj' for rel_cfile in rel_cfiles]
        m.cfiles = rel_cfiles

        rel_includedirs = [pypyrel(incldir) for incldir in eci.include_dirs]

        m.comment('automatically generated makefile')
        definitions = [
            ('PYPYDIR', autopath.pypydir),
            ('TARGET', exe_name.basename),
            ('DEFAULT_TARGET', '$(TARGET)'),
            ('SOURCES', rel_cfiles),
            ('OBJECTS', rel_ofiles),
            ('LIBS', self._libs(eci.libraries)),
            ('LIBDIRS', self._libdirs(eci.library_dirs)),
            ('INCLUDEDIRS', self._includedirs(rel_includedirs)),
            ('CFLAGS', self.cflags + list(eci.compile_extra)),
            ('LDFLAGS', self.link_flags + list(eci.link_extra)),
            ('CC', self.cc)
            ]
        for args in definitions:
            m.definition(*args)

        rules = [
            ('all', '$(DEFAULT_TARGET)', []),
            ('$(TARGET)', '$(OBJECTS)', '$(CC) $(LDFLAGS) -o $@ $(OBJECTS) $(LIBDIRS) $(LIBS)'),
            ('%.obj', '%.c', '$(CC) $(CFLAGS) -o $@ -c $< $(INCLUDEDIRS)'),
            ]

        for rule in rules:
            m.rule(*rule)

        return m

    def execute_makefile(self, path_to_makefile):
        if isinstance(path_to_makefile, NMakefile):
            path = path_to_makefile.makefile_dir
        else:
            path = path_to_makefile
        log.execute('make in %s' % (path,))
        oldcwd = path.chdir()
        try:
            returncode, stdout, stderr = _run_subprocess(
                'nmake',
                ['/f', str(path.join('Makefile'))])
        finally:
            oldcwd.chdir()

        self._handle_error(returncode, stdout, stderr, path.join('make'))

class NMakefile(posix.GnuMakefile):
    pass # for the moment
