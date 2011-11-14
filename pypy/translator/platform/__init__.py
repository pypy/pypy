"""Platform-specific support for compiling/executing C sources."""

import py, os, sys

from pypy.tool.ansi_print import ansi_log
from pypy.tool.runsubprocess import run_subprocess as _run_subprocess
from pypy.tool.udir import udir

log = py.log.Producer("platform")
py.log.setconsumer("platform", ansi_log)

class CompilationError(Exception):
    def __init__(self, out, err):
        self.out = out.replace('\r\n', '\n')
        self.err = err.replace('\r\n', '\n')

    def __repr__(self):
        if self.err:
            attr = 'err'
        else:
            attr = 'out'
        text = getattr(self, attr).replace('\n', '\n\t')
        return 'CompilationError(%s="""\n\t%s""")' % (attr, text)

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

    relevant_environ = ()
    log_errors = True

    so_prefixes = ('',)

    extra_libs = ()

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
        else:
            env = env.copy()

        # On Windows, %SystemRoot% must be present for most programs to start
        if (os.name == 'nt' and
            "SystemRoot" not in env and
            "SystemRoot" in os.environ):
            env["SystemRoot"] = os.environ["SystemRoot"]

        # Set LD_LIBRARY_PATH on posix platforms
        if os.name == 'posix' and compilation_info is not None:
            env['LD_LIBRARY_PATH'] = ':'.join(
                [str(i) for i in compilation_info.library_dirs])

        returncode, stdout, stderr = _run_subprocess(str(executable), args,
                                                     env)
        return ExecutionResult(returncode, stdout, stderr)

    def gen_makefile(self, cfiles, eci, exe_name=None, path=None,
                     shared=False):
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
        bits = [self.__class__.__name__, 'cc=%r' % self.cc]
        for varname in self.relevant_environ:
            bits.append('%s=%r' % (varname, os.environ.get(varname)))
        # adding sys.maxint to disambiguate windows
        bits.append('%s=%r' % ('sys.maxint', sys.maxint))
        return ' '.join(bits)

    # some helpers which seem to be cross-platform enough

    def _execute_c_compiler(self, cc, args, outname, cwd=None):
        log.execute(cc + ' ' + ' '.join(args))
        # 'cc' can also contain some options for the C compiler;
        # e.g. it can be "gcc -m32".  We handle it by splitting on ' '.
        cclist = cc.split()
        cc = cclist[0]
        args = cclist[1:] + args
        returncode, stdout, stderr = _run_subprocess(cc, args, self.c_environ,
                                                     cwd)
        self._handle_error(returncode, stdout, stderr, outname)

    def _handle_error(self, returncode, stdout, stderr, outname):
        if returncode != 0:
            errorfile = outname.new(ext='errors')
            errorfile.write(stderr, 'wb')
            if self.log_errors:
                stderrlines = stderr.splitlines()
                for line in stderrlines:
                    log.Error(line)
                # ^^^ don't use ERROR, because it might actually be fine.
                # Also, ERROR confuses lib-python/conftest.py.
            raise CompilationError(stdout, stderr)
        else:
            for line in stderr.splitlines():
                log.WARNING(line)

    def _make_response_file(self, prefix):
        """Creates a temporary file with the specified prefix,
        and returns its name"""
        # Build unique filename
        num = 0
        while 1:
            response_file = udir.join('%s%i' % (prefix, num))
            num += 1
            if not response_file.check():
                break
        return response_file

    def preprocess_include_dirs(self, include_dirs):
        if 'PYPY_LOCALBASE' in os.environ:
            dirs = list(self._preprocess_include_dirs(include_dirs))
            return [os.environ['PYPY_LOCALBASE'] + '/include'] + dirs
        return self._preprocess_include_dirs(include_dirs)

    def _preprocess_include_dirs(self, include_dirs):
        return include_dirs

    def _compile_args_from_eci(self, eci, standalone):
        include_dirs = self.preprocess_include_dirs(eci.include_dirs)
        args = self._includedirs(include_dirs)
        if standalone:
            extra = self.standalone_only
        else:
            extra = self.shared_only
        cflags = list(self.cflags) + list(extra)
        return (cflags + list(eci.compile_extra) + args)

    def preprocess_library_dirs(self, library_dirs):
        if 'PYPY_LOCALBASE' in os.environ:
            dirs = list(self._preprocess_library_dirs(library_dirs))
            return [os.environ['PYPY_LOCALBASE'] + '/lib'] + dirs
        return self._preprocess_library_dirs(library_dirs)

    def _preprocess_library_dirs(self, library_dirs):
        return library_dirs

    def _link_args_from_eci(self, eci, standalone):
        library_dirs = self.preprocess_library_dirs(eci.library_dirs)
        library_dirs = self._libdirs(library_dirs)
        libraries = self._libs(eci.libraries)
        link_files = self._linkfiles(eci.link_files)
        export_flags = self._exportsymbols_link_flags(eci)
        return (library_dirs + list(self.link_flags) + export_flags +
                link_files + list(eci.link_extra) + libraries +
                list(self.extra_libs))

    def _exportsymbols_link_flags(self, eci, relto=None):
        if eci.export_symbols:
            raise ValueError("This platform does not support export symbols")
        return []

    def _finish_linking(self, ofiles, eci, outputfilename, standalone):
        if outputfilename is None:
            outputfilename = ofiles[0].purebasename
        if ofiles:
            dirname = ofiles[0].dirpath()
        else:
            dirname = udir.join('module_cache')
        exe_name = dirname.join(outputfilename, abs=True)
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
        dirs = self._include_dirs_for_libffi()
        if 'PYPY_LOCALBASE' in os.environ:
            return [os.environ['PYPY_LOCALBASE'] + '/include'] + dirs
        return dirs

    def library_dirs_for_libffi(self):
        dirs = self._library_dirs_for_libffi()
        if 'PYPY_LOCALBASE' in os.environ:
            return [os.environ['PYPY_LOCALBASE'] + '/lib'] + dirs
        return dirs

    def _include_dirs_for_libffi(self):
        raise NotImplementedError("Needs to be overwritten")

    def _library_dirs_for_libffi(self):
        raise NotImplementedError("Needs to be overwritten")

    def check___thread(self):
        return True


if sys.platform.startswith('linux'):
    from pypy.translator.platform.linux import Linux, Linux64
    import platform
    if platform.architecture()[0] == '32bit':
        host_factory = Linux
    else:
        host_factory = Linux64
elif sys.platform == 'darwin':
    from pypy.translator.platform.darwin import Darwin_i386, Darwin_x86_64, Darwin_PowerPC
    import platform
    assert platform.machine() in ('Power Macintosh', 'i386', 'x86_64')

    if  platform.machine() == 'Power Macintosh':
        host_factory = Darwin_PowerPC
    elif sys.maxint <= 2147483647:
        host_factory = Darwin_i386
    else:
        host_factory = Darwin_x86_64
elif "freebsd" in sys.platform:
    from pypy.translator.platform.freebsd import Freebsd, Freebsd_64
    import platform
    if platform.architecture()[0] == '32bit':
        host_factory = Freebsd
    else:
        host_factory = Freebsd_64
elif "openbsd" in sys.platform:
    from pypy.translator.platform.openbsd import OpenBSD, OpenBSD_64
    import platform
    if platform.architecture()[0] == '32bit':
        host_factory = OpenBSD
    else:
        host_factory = OpenBSD_64
elif os.name == 'nt':
    from pypy.translator.platform.windows import Windows, Windows_x64
    import platform
    if platform.architecture()[0] == '32bit':
        host_factory = Windows
    else:
        host_factory = Windows_x64
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

