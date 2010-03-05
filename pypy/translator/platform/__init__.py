
""" Platform object that allows you to compile/execute C sources for given
platform.
"""

import sys, py, os

from pypy.tool.ansi_print import ansi_log
from py.impl.code.code import safe_repr
log = py.log.Producer("platform")
py.log.setconsumer("platform", ansi_log)

from subprocess import PIPE, Popen

def _run_subprocess(executable, args, env=None):
    if isinstance(args, str):
        args = str(executable) + ' ' + args
        shell = True
    else:
        if args is None:
            args = [str(executable)]
        else:
            args = [str(executable)] + args
        shell = False
    pipe = Popen(args, stdout=PIPE, stderr=PIPE, shell=shell, env=env)
    stdout, stderr = pipe.communicate()
    return pipe.returncode, stdout, stderr

class CompilationError(Exception):
    def __init__(self, out, err):
        self.out = out.replace('\r\n', '\n')
        self.err = err.replace('\r\n', '\n')

    def __repr__(self):
        if self.err:
            return "<CompilationError err=%s>" % safe_repr(self.err)
        else:
            return "<CompilationError out=%s>" % safe_repr(self.out)

    __str__ = __repr__

class ExecutionResult(object):
    def __init__(self, returncode, out, err):
        self.returncode = returncode
        self.out = out.replace('\r\n', '\n')
        self.err = err.replace('\r\n', '\n')

    def __repr__(self):
        return "<ExecutionResult retcode=%d>" % (self.returncode,)

class Platform(object):
    name = "abstract platform"
    c_environ = None

    relevant_environ = []

    so_prefixes = ['']

    def __init__(self, cc):
        if self.__class__ is Platform:
            raise TypeError("You should not instantiate Platform class directly")
        self.cc = cc

    def compile(self, cfiles, eci, outputfilename=None, standalone=True):
        ofiles = self._compile_o_files(cfiles, eci, standalone)
        return self._finish_linking(ofiles, eci, outputfilename, standalone)

    def _compile_o_files(self, cfiles, eci, standalone=True):
        cfiles = [py.path.local(f) for f in cfiles]
        cfiles += [py.path.local(f) for f in eci.separate_module_files]
        compile_args = self._compile_args_from_eci(eci, standalone)
        ofiles = []
        for cfile in cfiles:
            ofiles.append(self._compile_c_file(self.cc, cfile, compile_args))
        return ofiles

    def execute(self, executable, args=None, env=None, compilation_info=None):
        if env is None:
            env = os.environ.copy()
        if compilation_info is not None:
            env['LD_LIBRARY_PATH'] = ':'.join(
                [str(i) for i in compilation_info.library_dirs])
        returncode, stdout, stderr = _run_subprocess(str(executable), args,
                                                     env)
        return ExecutionResult(returncode, stdout, stderr)

    def gen_makefile(self, cfiles, eci, exe_name=None, path=None):
        raise NotImplementedError("Pure abstract baseclass")

    def __repr__(self):
        return '<%s cc=%s>' % (self.__class__.__name__, self.cc)

    def __hash__(self):
        return hash(self.__class__.__name__)

    def __ne__(self, other):
        return not self == other

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.__dict__ == other.__dict__)

    def key(self):
        bits = [self.__class__.__name__, 'cc=%s' % self.cc]
        for varname in self.relevant_environ:
            bits.append('%s=%s' % (varname, os.environ.get(varname)))
        return ' '.join(bits)

    # some helpers which seem to be cross-platform enough

    def _execute_c_compiler(self, cc, args, outname):
        log.execute(cc + ' ' + ' '.join(args))
        returncode, stdout, stderr = _run_subprocess(cc, args, self.c_environ)
        self._handle_error(returncode, stderr, stdout, outname)

    def _handle_error(self, returncode, stderr, stdout, outname):
        if returncode != 0:
            errorfile = outname.new(ext='errors')
            errorfile.write(stderr, 'wb')
            stderrlines = stderr.splitlines()
            for line in stderrlines[:50]:
                log.ERROR(line)
            if len(stderrlines) > 50:
                log.ERROR('...')
            raise CompilationError(stdout, stderr)

    
    def _compile_args_from_eci(self, eci, standalone):
        include_dirs = self._preprocess_dirs(eci.include_dirs)
        args = self._includedirs(include_dirs)
        if standalone:
            extra = self.standalone_only
        else:
            extra = self.shared_only
        cflags = self.cflags + extra
        return (cflags + list(eci.compile_extra) + args)

    def _link_args_from_eci(self, eci, standalone):
        library_dirs = self._libdirs(eci.library_dirs)
        libraries = self._libs(eci.libraries)
        link_files = self._linkfiles(eci.link_files)
        return (library_dirs + self.link_flags +
                link_files + list(eci.link_extra) + libraries)

    def _finish_linking(self, ofiles, eci, outputfilename, standalone):
        if outputfilename is None:
            outputfilename = ofiles[0].purebasename
        exe_name = py.path.local(os.path.join(str(ofiles[0].dirpath()),
                                              outputfilename))
        if standalone:
            if self.exe_ext:
                exe_name += '.' + self.exe_ext
        else:
            exe_name += '.' + self.so_ext
        if eci.use_cpp_linker:
            cc_link = 'g++'      # XXX hard-coded so far
        else:
            cc_link = self.cc
        largs = self._link_args_from_eci(eci, standalone)
        return self._link(cc_link, ofiles, largs, standalone, exe_name)

    # below are some detailed informations for platforms

    def include_dirs_for_libffi(self):
        raise NotImplementedError("Needs to be overwritten")

    def library_dirs_for_libffi(self):
        raise NotImplementedError("Needs to be overwritten")        

    def check___thread(self):
        return True

    
if sys.platform == 'linux2':
    from pypy.translator.platform.linux import Linux, Linux64
    import platform
    if platform.architecture()[0] == '32bit':
        host_factory = Linux
    else:
        host_factory = Linux64
elif sys.platform == 'darwin':
    from pypy.translator.platform.darwin import Darwin_i386, Darwin_x86_64
    import platform
    assert platform.machine() in ('i386', 'x86_64')
    if sys.maxint <= 2147483647:
        host_factory = Darwin_i386
    else:
        host_factory = Darwin_x86_64
elif sys.platform == 'freebsd7':
    from pypy.translator.platform.freebsd7 import Freebsd7, Freebsd7_64
    import platform
    if platform.architecture()[0] == '32bit':
        host_factory = Freebsd7
    else:
        host_factory = Freebsd7_64
elif os.name == 'nt':
    from pypy.translator.platform.windows import Windows
    host_factory = Windows
else:
    # pray
    from pypy.translator.platform.distutils_platform import DistutilsPlatform
    host_factory = DistutilsPlatform

platform = host = host_factory()

def pick_platform(new_platform, cc):
    if new_platform == 'host':
        return host_factory(cc)
    elif new_platform == 'maemo':
        from pypy.translator.platform.maemo import Maemo
        return Maemo(cc)
    elif new_platform == 'distutils':
        from pypy.translator.platform.distutils_platform import DistutilsPlatform
        return DistutilsPlatform()
    else:
        raise ValueError("platform = %s" % (new_platform,))

def set_platform(new_platform, cc):
    global platform
    log.msg("Setting platform to %r cc=%s" % (new_platform,cc))
    platform = pick_platform(new_platform, cc)

    if new_platform == 'host':
        global host
        host = platform

