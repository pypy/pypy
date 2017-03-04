"""Support for Windows."""

import py, os, sys, re, shutil

from rpython.translator.platform import CompilationError
from rpython.translator.platform import log, _run_subprocess
from rpython.translator.platform import Platform, posix

import rpython
rpydir = str(py.path.local(rpython.__file__).join('..'))

def _get_compiler_type(cc, x64_flag):
    import subprocess
    if not cc:
        cc = os.environ.get('CC','')
    if not cc:
        return MsvcPlatform(x64=x64_flag)
    elif cc.startswith('mingw') or cc == 'gcc':
        return MingwPlatform(cc)
    else:
        return MsvcPlatform(cc=cc, x64=x64_flag)
    try:
        subprocess.check_output([cc, '--version'])
    except:
        raise ValueError("Could not find compiler specified by cc option '%s',"
                         " it must be a valid exe file on your path" % cc)
    return MingwPlatform(cc)

def Windows(cc=None):
    return _get_compiler_type(cc, False)

def Windows_x64(cc=None):
    raise Exception("Win64 is not supported.  You must either build for Win32"
                    " or contribute the missing support in PyPy.")
    return _get_compiler_type(cc, True)

def _find_vcvarsall(version):
    # copied from setuptools.msvc9_support.py
    from distutils.msvc9compiler import Reg
    VC_BASE = r'Software\%sMicrosoft\DevDiv\VCForPython\%0.1f'
    key = VC_BASE % ('', version)
    try:
        # Per-user installs register the compiler path here
        productdir = Reg.get_value(key, "installdir")
    except KeyError:
        try:
            # All-user installs on a 64-bit system register here
            key = VC_BASE % ('Wow6432Node\\', version)
            productdir = Reg.get_value(key, "installdir")
        except KeyError:
            productdir = None

    if productdir:
        vcvarsall = os.path.join(productdir, "vcvarsall.bat")
        if os.path.isfile(vcvarsall):
            return vcvarsall
    return None

def _get_msvc_env(vsver, x64flag):
    vcvars = None
    try:
        toolsdir = os.environ['VS%sCOMNTOOLS' % vsver]
    except KeyError:
        # try to import from the registry, as done in setuptools
        # XXX works for 90 but is it generalizable?
        toolsdir = ''
        vcvars = _find_vcvarsall(vsver/10)

    if not vcvars:
        if x64flag:
            vsinstalldir = os.path.abspath(os.path.join(toolsdir, '..', '..'))
            vcinstalldir = os.path.join(vsinstalldir, 'VC')
            vcbindir = os.path.join(vcinstalldir, 'BIN')
            vcvars = os.path.join(vcbindir, 'amd64', 'vcvarsamd64.bat')
        else:
            vcvars = os.path.join(toolsdir, 'vsvars32.bat')

    import subprocess
    try:
        popen = subprocess.Popen('"%s" & set' % (vcvars,),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

        stdout, stderr = popen.communicate()
        if popen.wait() != 0:
            return None
    except:
        return None
    env = {}

    stdout = stdout.replace("\r\n", "\n")
    for line in stdout.split("\n"):
        if '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key.upper() in ['PATH', 'INCLUDE', 'LIB']:
            env[key.upper()] = value
    ## log.msg("Updated environment with %s" % (vcvars,))
    return env

def find_msvc_env(x64flag=False):
    # First, try to get the compiler which served to compile python
    msc_pos = sys.version.find('MSC v.')
    if msc_pos != -1:
        msc_ver = int(sys.version[msc_pos+6:msc_pos+10])
        # 1300 -> 70, 1310 -> 71, 1400 -> 80, 1500 -> 90
        vsver = (msc_ver / 10) - 60
        env = _get_msvc_env(vsver, x64flag)

        if env is not None:
            return env

    # Then, try any other version
    for vsver in (100, 90, 80, 71, 70): # All the versions I know
        env = _get_msvc_env(vsver, x64flag)

        if env is not None:
            return env
    log.error("Could not find a Microsoft Compiler")
    # Assume that the compiler is already part of the environment

class MsvcPlatform(Platform):
    name = "msvc"
    so_ext = 'dll'
    exe_ext = 'exe'

    relevant_environ = ('PATH', 'INCLUDE', 'LIB')

    cc = 'cl.exe'
    link = 'link.exe'

    cflags = ('/MD', '/O2', '/Zi')
    link_flags = ('/debug','/LARGEADDRESSAWARE')
    standalone_only = ()
    shared_only = ()
    environ = None

    def __init__(self, cc=None, x64=False):
        self.x64 = x64
        if cc is None:
            msvc_compiler_environ = find_msvc_env(x64)
            Platform.__init__(self, 'cl.exe')
            if msvc_compiler_environ:
                self.c_environ = os.environ.copy()
                self.c_environ.update(msvc_compiler_environ)
        else:
            self.cc = cc

        # detect version of current compiler
        returncode, stdout, stderr = _run_subprocess(self.cc, '',
                                                     env=self.c_environ)
        r = re.search(r'Microsoft.+C/C\+\+.+\s([0-9]+)\.([0-9]+).*', stderr)
        if r is not None:
            self.version = int(''.join(r.groups())) / 10 - 60
        else:
            # Probably not a msvc compiler...
            self.version = 0

        # Try to find a masm assembler
        returncode, stdout, stderr = _run_subprocess('ml.exe', '',
                                                     env=self.c_environ)
        r = re.search('Macro Assembler', stderr)
        if r is None and os.path.exists('c:/masm32/bin/ml.exe'):
            masm32 = 'c:/masm32/bin/ml.exe'
            masm64 = 'c:/masm64/bin/ml64.exe'
        else:
            masm32 = 'ml.exe'
            masm64 = 'ml64.exe'

        if x64:
            self.masm = masm64
        else:
            self.masm = masm32

        # Install debug options only when interpreter is in debug mode
        if sys.executable.lower().endswith('_d.exe'):
            self.cflags = ['/MDd', '/Z7', '/Od']

            # Increase stack size, for the linker and the stack check code.
            stack_size = 8 << 20  # 8 Mb
            self.link_flags = self.link_flags + ('/STACK:%d' % stack_size,)
            # The following symbol is used in c/src/stack.h
            self.cflags.append('/DMAX_STACK_SIZE=%d' % (stack_size - 1024))

    def _includedirs(self, include_dirs):
        return ['/I%s' % (idir,) for idir in include_dirs]

    def _libs(self, libraries):
        libs = []
        for lib in libraries:
            lib = str(lib)
            if lib.endswith('.dll'):
                lib = lib[:-4]
            libs.append('%s.lib' % (lib,))
        return libs

    def _libdirs(self, library_dirs):
        return ['/LIBPATH:%s' % (ldir,) for ldir in library_dirs]

    def _linkfiles(self, link_files):
        return list(link_files)

    def _args_for_shared(self, args):
        return ['/dll'] + args

    def check___thread(self):
        # __declspec(thread) does not seem to work when using assembler.
        # Returning False will cause the program to use TlsAlloc functions.
        # see src/thread_nt.h
        return False

    def _link_args_from_eci(self, eci, standalone):
        # Windows needs to resolve all symbols even for DLLs
        return super(MsvcPlatform, self)._link_args_from_eci(eci, standalone=True)

    def _compile_c_file(self, cc, cfile, compile_args):
        oname = self._make_o_file(cfile, ext='obj')
        # notabene: (tismer)
        # This function may be called for .c but also .asm files.
        # The c compiler accepts any order of arguments, while
        # the assembler still has the old behavior that all options
        # must come first, and after the file name all options are ignored.
        # So please be careful with the order of parameters! ;-)
        pdb_dir = oname.dirname
        if pdb_dir:
                compile_args = compile_args + ['/Fd%s\\' % (pdb_dir,)]
        args = ['/nologo', '/c'] + compile_args + ['/Fo%s' % (oname,), str(cfile)]
        self._execute_c_compiler(cc, args, oname)
        return oname

    def _link(self, cc, ofiles, link_args, standalone, exe_name):
        args = ['/nologo'] + [str(ofile) for ofile in ofiles] + link_args
        args += ['/out:%s' % (exe_name,), '/incremental:no']
        if not standalone:
            args = self._args_for_shared(args)

        if self.version >= 80:
            # Tell the linker to generate a manifest file
            temp_manifest = exe_name.dirpath().join(
                exe_name.purebasename + '.manifest')
            args += ["/MANIFEST", "/MANIFESTFILE:%s" % (temp_manifest,)]

        self._execute_c_compiler(self.link, args, exe_name)

        if self.version >= 80:
            # Now, embed the manifest into the program
            if standalone:
                mfid = 1
            else:
                mfid = 2
            out_arg = '-outputresource:%s;%s' % (exe_name, mfid)
            args = ['-nologo', '-manifest', str(temp_manifest), out_arg]
            self._execute_c_compiler('mt.exe', args, exe_name)

        return exe_name

    def _handle_error(self, returncode, stdout, stderr, outname):
        if returncode != 0:
            # Microsoft compilers write compilation errors to stdout
            stderr = stdout + stderr
            errorfile = outname.new(ext='errors')
            errorfile.write(stderr, mode='wb')
            if self.log_errors:
                stderrlines = stderr.splitlines()
                for line in stderrlines:
                    log.Error(line)
                # ^^^ don't use ERROR, because it might actually be fine.
                # Also, ERROR confuses lib-python/conftest.py.
            raise CompilationError(stdout, stderr)


    def gen_makefile(self, cfiles, eci, exe_name=None, path=None,
                     shared=False, headers_to_precompile=[],
                     no_precompile_cfiles = [], icon=None):
        cfiles = self._all_cfiles(cfiles, eci)

        if path is None:
            path = cfiles[0].dirpath()

        rpypath = py.path.local(rpydir)

        if exe_name is None:
            exe_name = cfiles[0].new(ext=self.exe_ext)
        else:
            exe_name = exe_name.new(ext=self.exe_ext)

        if shared:
            so_name = exe_name.new(purebasename='lib' + exe_name.purebasename,
                                   ext=self.so_ext)
            wtarget_name = exe_name.new(purebasename=exe_name.purebasename + 'w',
                                   ext=self.exe_ext)
            target_name = so_name.basename
        else:
            target_name = exe_name.basename

        m = NMakefile(path)
        m.exe_name = path.join(exe_name.basename)
        m.eci = eci

        linkflags = list(self.link_flags)
        if shared:
            linkflags = self._args_for_shared(linkflags)
        linkflags += self._exportsymbols_link_flags()
        # Make sure different functions end up at different addresses!
        # This is required for the JIT.
        linkflags.append('/opt:noicf')

        def rpyrel(fpath):
            rel = py.path.local(fpath).relto(rpypath)
            if rel:
                return os.path.join('$(RPYDIR)', rel)
            else:
                return fpath

        rel_cfiles = [m.pathrel(cfile) for cfile in cfiles]
        rel_ofiles = [rel_cfile[:rel_cfile.rfind('.')]+'.obj' for rel_cfile in rel_cfiles]
        m.cfiles = rel_cfiles

        rel_includedirs = [rpyrel(incldir) for incldir in
                           self.preprocess_include_dirs(eci.include_dirs)]
        rel_libdirs = [rpyrel(libdir) for libdir in
                       self.preprocess_library_dirs(eci.library_dirs)]

        m.comment('automatically generated makefile')
        definitions = [
            ('RPYDIR', '"%s"' % rpydir),
            ('TARGET', target_name),
            ('DEFAULT_TARGET', exe_name.basename),
            ('SOURCES', rel_cfiles),
            ('OBJECTS', rel_ofiles),
            ('LIBS', self._libs(eci.libraries)),
            ('LIBDIRS', self._libdirs(rel_libdirs)),
            ('INCLUDEDIRS', self._includedirs(rel_includedirs)),
            ('CFLAGS', self.cflags),
            ('CFLAGSEXTRA', list(eci.compile_extra)),
            ('LDFLAGS', linkflags),
            ('LDFLAGSEXTRA', list(eci.link_extra)),
            ('CC', self.cc),
            ('CC_LINK', self.link),
            ('LINKFILES', eci.link_files),
            ('MASM', self.masm),
            ('MAKE', 'nmake.exe'),
            ('_WIN32', '1'),
            ]
        if shared:
            definitions.insert(0, ('WTARGET', wtarget_name.basename))
        if self.x64:
            definitions.append(('_WIN64', '1'))

        rules = [
            ('all', '$(DEFAULT_TARGET) $(WTARGET)', []),
            ('.asm.obj', '', '$(MASM) /nologo /Fo$@ /c $< $(INCLUDEDIRS)'),
            ]

        if len(headers_to_precompile)>0:
            stdafx_h = path.join('stdafx.h')
            txt  = '#ifndef PYPY_STDAFX_H\n'
            txt += '#define PYPY_STDAFX_H\n'
            txt += '\n'.join(['#include "' + m.pathrel(c) + '"' for c in headers_to_precompile])
            txt += '\n#endif\n'
            stdafx_h.write(txt)
            stdafx_c = path.join('stdafx.c')
            stdafx_c.write('#include "stdafx.h"\n')
            definitions.append(('CREATE_PCH', '/Ycstdafx.h /Fpstdafx.pch /FIstdafx.h'))
            definitions.append(('USE_PCH', '/Yustdafx.h /Fpstdafx.pch /FIstdafx.h'))
            rules.append(('$(OBJECTS)', 'stdafx.pch', []))
            rules.append(('stdafx.pch', 'stdafx.h',
               '$(CC) stdafx.c /c /nologo $(CFLAGS) $(CFLAGSEXTRA) '
               '$(CREATE_PCH) $(INCLUDEDIRS)'))
            rules.append(('.c.obj', '',
                    '$(CC) /nologo $(CFLAGS) $(CFLAGSEXTRA) $(USE_PCH) '
                    '/Fo$@ /c $< $(INCLUDEDIRS)'))
            #Do not use precompiled headers for some files
            #rules.append((r'{..\module_cache}.c{..\module_cache}.obj', '',
            #        '$(CC) /nologo $(CFLAGS) $(CFLAGSEXTRA) /Fo$@ /c $< $(INCLUDEDIRS)'))
            # nmake cannot handle wildcard target specifications, so we must
            # create a rule for compiling each file from eci since they cannot use
            # precompiled headers :(
            no_precompile = []
            for f in list(no_precompile_cfiles):
                f = m.pathrel(py.path.local(f))
                if f not in no_precompile and (f.endswith('.c') or f.endswith('.cpp')):
                    no_precompile.append(f)
                    target = f[:f.rfind('.')] + '.obj'
                    rules.append((target, f,
                        '$(CC) /nologo $(CFLAGS) $(CFLAGSEXTRA) '
                        '/Fo%s /c %s $(INCLUDEDIRS)' %(target, f)))

        else:
            rules.append(('.c.obj', '',
                          '$(CC) /nologo $(CFLAGS) $(CFLAGSEXTRA) '
                          '/Fo$@ /c $< $(INCLUDEDIRS)'))


        if icon:
            shutil.copyfile(icon, str(path.join('icon.ico')))
            rc_file = path.join('icon.rc')
            rc_file.write('IDI_ICON1 ICON DISCARDABLE "icon.ico"')
            rules.append(('icon.res', 'icon.rc', 'rc icon.rc'))


        for args in definitions:
            m.definition(*args)

        for rule in rules:
            m.rule(*rule)

        if len(headers_to_precompile)>0 and self.version >= 80:
            # at least from VS2013 onwards we need to include PCH
            # objects in the final link command
            linkobjs = 'stdafx.obj @<<\n$(OBJECTS)\n<<'
        else:
            linkobjs = '@<<\n$(OBJECTS)\n<<'

        extra_deps = []
        if icon and not shared:
            extra_deps.append('icon.res')
            linkobjs = 'icon.res ' + linkobjs
        if self.version < 80:
            m.rule('$(TARGET)', ['$(OBJECTS)'] + extra_deps,
                    [ '$(CC_LINK) /nologo $(LDFLAGS) $(LDFLAGSEXTRA) /out:$@' +\
                      ' $(LIBDIRS) $(LIBS) ' + linkobjs,
                   ])
        else:
            m.rule('$(TARGET)', ['$(OBJECTS)'] + extra_deps,
                    [ '$(CC_LINK) /nologo $(LDFLAGS) $(LDFLAGSEXTRA)' + \
                      ' $(LINKFILES) /out:$@ $(LIBDIRS) $(LIBS) /MANIFEST' + \
                      ' /MANIFESTFILE:$*.manifest ' + linkobjs,
                    'mt.exe -nologo -manifest $*.manifest -outputresource:$@;1',
                    ])
        m.rule('debugmode_$(TARGET)', ['$(OBJECTS)'] + extra_deps,
                [ '$(CC_LINK) /nologo /DEBUG $(LDFLAGS) $(LDFLAGSEXTRA)' + \
                  ' $(LINKFILES) /out:$@ $(LIBDIRS) $(LIBS) ' + linkobjs,
                ])

        if shared:
            m.definition('SHARED_IMPORT_LIB', so_name.new(ext='lib').basename)
            m.definition('PYPY_MAIN_FUNCTION', "pypy_main_startup")
            m.rule('main.c', '',
                   'echo '
                   'int $(PYPY_MAIN_FUNCTION)(int, char*[]); '
                   'int main(int argc, char* argv[]) '
                   '{ return $(PYPY_MAIN_FUNCTION)(argc, argv); } > $@')
            deps = ['main.obj']
            m.rule('wmain.c', '',
                   ['echo #define WIN32_LEAN_AND_MEAN > $@',
                   'echo #include "stdlib.h" >> $@',
                   'echo #include "windows.h" >> $@',
                   'echo int $(PYPY_MAIN_FUNCTION)(int, char*[]); >> $@',
                   'echo int WINAPI WinMain( >> $@',
                   'echo     HINSTANCE hInstance,      /* handle to current instance */ >> $@',
                   'echo     HINSTANCE hPrevInstance,  /* handle to previous instance */ >> $@',
                   'echo     LPSTR lpCmdLine,          /* pointer to command line */ >> $@',
                   'echo     int nCmdShow              /* show state of window */ >> $@',
                   'echo ) >> $@',
                   'echo    { return $(PYPY_MAIN_FUNCTION)(__argc, __argv); } >> $@'])
            wdeps = ['wmain.obj']
            if icon:
                deps.append('icon.res')
                wdeps.append('icon.res')
            m.rule('$(DEFAULT_TARGET)', ['$(TARGET)'] + deps,
                   ['$(CC_LINK) /nologo /debug %s ' % (' '.join(deps),) + \
                    '$(SHARED_IMPORT_LIB) /out:$@ ' + \
                    '/MANIFEST /MANIFESTFILE:$*.manifest',
                    'mt.exe -nologo -manifest $*.manifest -outputresource:$@;1',
                    ])
            m.rule('$(WTARGET)', ['$(TARGET)'] + wdeps,
                   ['$(CC_LINK) /nologo /debug /SUBSYSTEM:WINDOWS %s ' % (' '.join(wdeps),) + \
                    '$(SHARED_IMPORT_LIB) /out:$@ ' + \
                    '/MANIFEST /MANIFESTFILE:$*.manifest',
                    'mt.exe -nologo -manifest $*.manifest -outputresource:$@;1',
                    ])
            m.rule('debugmode_$(DEFAULT_TARGET)', ['debugmode_$(TARGET)']+deps,
                   ['$(CC_LINK) /nologo /DEBUG %s ' % (' '.join(deps),) + \
                    'debugmode_$(SHARED_IMPORT_LIB) /out:$@',
                    ])

        return m

    def execute_makefile(self, path_to_makefile, extra_opts=[]):
        if isinstance(path_to_makefile, NMakefile):
            path = path_to_makefile.makefile_dir
        else:
            path = path_to_makefile
        log.execute('make %s in %s' % (" ".join(extra_opts), path))
        oldcwd = path.chdir()
        try:
            returncode, stdout, stderr = _run_subprocess(
                'nmake',
                ['/nologo', '/f', str(path.join('Makefile'))] + extra_opts,
                env = self.c_environ)
        finally:
            oldcwd.chdir()

        self._handle_error(returncode, stdout, stderr, path.join('make'))

class WinDefinition(posix.Definition):
    def write(self, f):
        def write_list(prefix, lst):
            lst = lst or ['']
            for i, fn in enumerate(lst):
                print >> f, prefix, fn,
                if i < len(lst)-1:
                    print >> f, '\\'
                else:
                    print >> f
                prefix = ' ' * len(prefix)
        name, value = self.name, self.value
        if isinstance(value, str):
            f.write('%s = %s\n' % (name, value))
        else:
            write_list('%s =' % (name,), value)
        f.write('\n')


class NMakefile(posix.GnuMakefile):
    def write(self, out=None):
        # nmake expands macros when it parses rules.
        # Write all macros before the rules.
        if out is None:
            f = self.makefile_dir.join('Makefile').open('w')
        else:
            f = out
        for line in self.lines:
            if not isinstance(line, posix.Rule):
                line.write(f)
        for line in self.lines:
            if isinstance(line, posix.Rule):
                line.write(f)
        f.flush()
        if out is None:
            f.close()

    def definition(self, name, value):
        defs = self.defs
        defn = WinDefinition(name, value)
        if name in defs:
            self.lines[defs[name]] = defn
        else:
            defs[name] = len(self.lines)
            self.lines.append(defn)

class MingwPlatform(posix.BasePosix):
    name = 'mingw32'
    standalone_only = ()
    shared_only = ()
    cflags = ('-O3',)
    link_flags = ()
    exe_ext = 'exe'
    so_ext = 'dll'

    def __init__(self, cc=None):
        if not cc:
            cc = 'gcc'
        Platform.__init__(self, cc)

    def _args_for_shared(self, args):
        return ['-shared'] + args

    def _include_dirs_for_libffi(self):
        return []

    def _library_dirs_for_libffi(self):
        return []

    def _handle_error(self, returncode, stdout, stderr, outname):
        # Mingw tools write compilation errors to stdout
        super(MingwPlatform, self)._handle_error(
            returncode, '', stderr + stdout, outname)
