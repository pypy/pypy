
from pypy.translator.platform import Platform, log, CompilationError
import py, sys, os
from pypy.translator.tool import stdoutcapture

def log_spawned_cmd(spawn):
    def spawn_and_log(cmd, *args, **kwds):
        log.execute(' '.join(cmd))
        return spawn(cmd, *args, **kwds)
    return spawn_and_log

CFLAGS = ['-O3']

if os.name != 'nt':
    so_ext = 'so'
else:
    so_ext = 'dll'

class DistutilsPlatform(Platform):
    """ This is a generic distutils platform. I hope it'll go away at some
    point soon completely
    """
    name = "distutils"
    so_ext = so_ext
    
    def __init__(self, cc=None):
        self.cc = cc
        if self.name == "distutils":
            self.name = sys.platform
    
    def _ensure_correct_math(self):
        if self.name != 'win32':
            return # so far
        from distutils import sysconfig
        gcv = sysconfig.get_config_vars()
        opt = gcv.get('OPT') # not always existent
        if opt and '/Op' not in opt:
            opt += '/Op'
        gcv['OPT'] = opt
    
    def compile(self, cfilenames, eci, outputfilename=None, standalone=True):
        self._ensure_correct_math()
        self.cfilenames = cfilenames
        if standalone:
            ext = ''
        else:
            ext = so_ext
        self.standalone = standalone
        self.libraries = list(eci.libraries)
        self.include_dirs = list(eci.include_dirs)
        self.library_dirs = list(eci.library_dirs)
        self.compile_extra = list(eci.compile_extra)
        self.link_extra = list(eci.link_extra)
        self.frameworks = list(eci.frameworks)
        if not self.name in ('win32', 'darwin'): # xxx
            if 'm' not in self.libraries:
                self.libraries.append('m')
            self.compile_extra += CFLAGS + ['-fomit-frame-pointer']
            if 'pthread' not in self.libraries:
                self.libraries.append('pthread')
            if self.name != 'sunos5': 
                self.compile_extra += ['-pthread']
                self.link_extra += ['-pthread']
            else:
                self.compile_extra += ['-pthreads']
                self.link_extra += ['-lpthread']
        if self.name == 'win32':
            self.link_extra += ['/DEBUG'] # generate .pdb file
        if self.name == 'darwin':
            # support Fink & Darwinports
            for s in ('/sw/', '/opt/local/'):
                if s + 'include' not in self.include_dirs and \
                   os.path.exists(s + 'include'):
                    self.include_dirs.append(s + 'include')
                if s + 'lib' not in self.library_dirs and \
                   os.path.exists(s + 'lib'):
                    self.library_dirs.append(s + 'lib')
            self.compile_extra += CFLAGS + ['-fomit-frame-pointer']
            for framework in self.frameworks:
                self.link_extra += ['-framework', framework]

        if outputfilename is None:
            self.outputfilename = py.path.local(cfilenames[0]).new(ext=ext)
        else:
            self.outputfilename = py.path.local(outputfilename)
        self.eci = eci
        import distutils.errors
        basename = self.outputfilename.new(ext='')
        data = ''
        try:
            saved_environ = os.environ.copy()
            c = stdoutcapture.Capture(mixed_out_err = True)
            try:
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
                    fdump = basename.new(ext='errors').open("wb")
                    fdump.write(data)
                    fdump.close()
        except (distutils.errors.CompileError,
                distutils.errors.LinkError), e:
            raise CompilationError('', data)
        except:
            print >>sys.stderr, data
            raise
        return self.outputfilename

    def _build(self):
        from distutils.ccompiler import new_compiler
        from distutils import sysconfig
        compiler = new_compiler(force=1)
        if self.cc is not None:
            for c in '''compiler compiler_so compiler_cxx
                        linker_exe linker_so'''.split():
                compiler.executables[c][0] = self.cc
        if not self.standalone:
            sysconfig.customize_compiler(compiler) # XXX
        compiler.spawn = log_spawned_cmd(compiler.spawn)
        objects = []
        for cfile in self.cfilenames:
            cfile = py.path.local(cfile)
            compile_extra = self.compile_extra[:]
            # -frandom-seed is only to try to be as reproducable as possible
            if 0 and self.fix_gcc_random_seed:
                compile_extra.append('-frandom-seed=%s' % (cfile.basename,))
                # XXX horrible workaround for a bug of profiling in gcc on
                # OS X with functions containing a direct call to fork()
                if '/*--no-profiling-for-this-file!--*/' in cfile.read():
                    compile_extra = [arg for arg in compile_extra
                                     if not arg.startswith('-fprofile-')]

            old = cfile.dirpath().chdir()
            try:
                res = compiler.compile([cfile.basename],
                                       include_dirs=self.eci.include_dirs,
                                       extra_preargs=compile_extra)
                assert len(res) == 1
                cobjfile = py.path.local(res[0])
                assert cobjfile.check()
                objects.append(str(cobjfile))
            finally:
                old.chdir()

        if self.standalone:
            cmd = compiler.link_executable
        else:
            cmd = compiler.link_shared_object
        cmd(objects, str(self.outputfilename),
            libraries=self.eci.libraries,
            extra_preargs=self.link_extra,
            library_dirs=self.eci.library_dirs)

    def include_dirs_for_libffi(self):
        return ['/usr/include/libffi']

    def library_dirs_for_libffi(self):
        return ['/usr/lib/libffi']

