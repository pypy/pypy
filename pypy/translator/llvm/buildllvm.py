import os
import sys

import py

from pypy.translator.tool import stdoutcapture
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.llvm.log import log
from pypy.translator.llvm.modwrapper import CtypesModule
from pypy.translator.llvm.externs2ll import get_incdirs

def llvm_is_on_path():
    if py.path.local.sysfind("llvm-as") is None or \
       py.path.local.sysfind("llvm-gcc") is None:
        return False
    return True

CFLAGS = os.getenv("CFLAGS") or "-O3"

def exe_version(exe, cache={}):
    try:
        v =  cache[exe]
    except KeyError:
        v = os.popen(exe + ' -version 2>&1').read()
        v = ''.join([c for c in v if c.isdigit()])
        v = int(v) / 10.0
        cache[exe] = v
    return v

def exe_version2(exe):
    v = os.popen(exe + ' --version 2>&1').read()
    i = v.index(')')
    v = v[i+2:].split()[0].split('.')
    major, minor = v[0], ''.join([c for c in v[1] if c.isdigit()])
    v = float(major) + float(minor) / 10.0
    return v

llvm_version = lambda: exe_version('llvm-as')
gcc_version = lambda: exe_version2('gcc')
llvm_gcc_version = lambda: exe_version2('llvm-gcc')

def have_boehm():
    import distutils.sysconfig
    from os.path import exists
    libdir = distutils.sysconfig.EXEC_PREFIX + "/lib"
    return exists(libdir + '/libgc.so') or exists(libdir + '/libgc.a')

def postfix():
    if llvm_version() >= 2.0:
        return '.i32'
    else:
        return ''

class Builder(object):
    def __init__(self, genllvm):
        self.genllvm = genllvm
        self.cmds = []

    def optimizations(self):
        return self.genllvm.config.translation.llvm.opt_options

    def execute_cmds(self):
        c = stdoutcapture.Capture(mixed_out_err=True)
        log.build("working in", py.path.local())
        try:
            try:
                for cmd in self.cmds:
                    log.build(cmd)
                    py.process.cmdexec(cmd)
            finally:
                foutput, ferror = c.done()
        except:
            data = 'OUTPUT:\n' + foutput.read() + '\n\nERROR:\n' + ferror.read()
            fdump = open("%s.errors" % self.genllvm.filename, "w")
            fdump.write(data)
            fdump.close()
            log.build(data)
            raise

    def cmds_bytecode(self, base):
        # run llvm assembler and optimizer
        opts = self.optimizations()
        self.cmds.append("llvm-as < %s.ll | opt %s -f -o %s.bc" % (base, opts, base))

    def cmds_objects(self, base, standalone):
        use_gcc = self.genllvm.config.translation.llvm_via_c
        if use_gcc:
            self.cmds.append("llc %s.bc -march=c -f -o %s.c" % (base, base))
            self.cmds.append("gcc %s.c -c %s -fomit-frame-pointer" % (base, CFLAGS))
        else:
            model = ''
            if not standalone:
                model = ' -relocation-model=pic'

            self.cmds.append("llc %s %s.bc -f -o %s.s" % (model, base, base))
            self.cmds.append("as %s.s -o %s.o" % (base, base))

        include_opts = get_incdirs(self.genllvm.eci)

        # compile separate files
        # XXX rxe: why do we want to run a c compiler, when we run llvm
        # compiler - these seems a step backwards IMHO ?????
        libraries = set()
        for filename in self.genllvm.eci.separate_module_files:
            assert filename.endswith(".c")
            objname = filename[:-2] + ".o"
            libraries.add(objname)
            self.cmds.append("gcc %s -c %s %s -o %s" % (filename, include_opts, CFLAGS, objname))

        attrs = self.genllvm.eci._copy_attributes()
        attrs['libraries'] = tuple(libraries) + attrs['libraries']
        self.genllvm.eci = ExternalCompilationInfo(**attrs)

# XXX support profile?
#             if (self.genllvm.config.translation.profopt is not None and
#                 not self.genllvm.config.translation.noprofopt):
#                 cmd = "gcc -fprofile-generate %s.c -c %s -pipe -o %s.o" % (base, CFLAGS, base)
#                 self.cmds.append(cmd)
#                 cmd = "gcc -fprofile-generate %s.o %s %s -lm -pipe -o %s_gen" % \
#                       (base, gc_libs_path, gc_libs, exename)
#                 self.cmds.append(cmd)
#                 self.cmds.append("./%s_gen %s" % (exename, self.genllvm.config.translation.profopt))
#                 cmd = "gcc -fprofile-use %s.c -c %s -pipe -o %s.o" % (b, CFLAGS, b)
#                 self.cmds.append(cmd)
#                 cmd = "gcc -fprofile-use %s.o %s %s -lm -pipe -o %s" % \
#                       (b, gc_libs_path, gc_libs, exename)
#             else:

    def setup(self):
        # set up directories
        llvmfile = self.genllvm.filename

        # change into dirpath and store current path to change back
        self.dirpath = llvmfile.dirpath()
        self.lastdir = py.path.local()
        self.dirpath.chdir()

        return self.genllvm.entry_name

    def setup_linker_command(self, base, exename=None):
        eci = self.genllvm.eci
        library_files = self.genllvm.db.gcpolicy.gc_libraries()
        library_files = list(library_files) + list(eci.libraries)
        library_dirs = list(eci.library_dirs)
        compiler_opts = []

        if sys.platform == 'darwin':
            library_dirs.append('/sw/lib')
            library_files.append("m")
            library_files.append("dl")
            if not exename:
                compiler_opts.append("-bundle")
        else:
            if not exename:
                compiler_opts.append("-shared")
            else:
                compiler_opts.append("-static")
            compiler_opts.append("-pipe")

        lib_opts = []
        for lib in library_files:
            if lib[0] != "/":
                lib = "-l" + lib
            lib_opts.append(lib)
        lib_dir_opts = ["-L" + libdir for libdir in library_dirs]
        compiler_opts.extend(lib_opts)
        compiler_opts.extend(lib_dir_opts)

        out = base + ".so"
        if exename:
            out = exename
        self.cmds.append("gcc %s %s.o %s -o %s" % (CFLAGS, base, " ".join(compiler_opts), out))

    def make_module(self):
        base = self.setup()
        self.cmds_bytecode(base)
        self.cmds_objects(base, False)
        self.setup_linker_command(base)
        try:
            self.execute_cmds()
            modname = CtypesModule(self.genllvm, "%s.so" % base).create()
        finally:
            self.lastdir.chdir()

        return modname, str(self.dirpath)

    def make_standalone(self, exename):
        base = self.setup()
        self.cmds_bytecode(base)
        self.cmds_objects(base, True)
        self.setup_linker_command(base, exename)

        try:
            self.execute_cmds()
        finally:
            self.lastdir.chdir()

        return str(self.dirpath.join(exename))
