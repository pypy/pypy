import os
import sys

import py

from pypy.translator.tool import stdoutcapture
from pypy.translator.llvm.log import log
from pypy.translator.llvm.modwrapper import CtypesModule

def llvm_is_on_path():
    if py.path.local.sysfind("llvm-as") is None or \
       py.path.local.sysfind("llvm-gcc") is None:
        return False 
    return True

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
        return '-std-compile-opts'

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

    def cmds_objects(self, base):
        use_gcc = self.genllvm.config.translation.llvm_via_c
        if use_gcc:
            self.cmds.append("llc %s.bc -march=c -f -o %s.c" % (base, base))
            self.cmds.append("gcc %s.c -c -O3 -fomit-frame-pointer" % base)
        else:
            self.cmds.append("llc -relocation-model=pic %s.bc -f -o %s.s" % (base, base))
            self.cmds.append("as %s.s -o %s.o" % (base, base))

# XXX support profile?
#             if (self.genllvm.config.translation.profopt is not None and
#                 not self.genllvm.config.translation.noprofopt):
#                 cmd = "gcc -fprofile-generate %s.c -c -O3 -pipe -o %s.o" % (base, base)
#                 self.cmds.append(cmd)
#                 cmd = "gcc -fprofile-generate %s.o %s %s -lm -pipe -o %s_gen" % \
#                       (base, gc_libs_path, gc_libs, exename)
#                 self.cmds.append(cmd)
#                 self.cmds.append("./%s_gen %s" % (exename, self.genllvm.config.translation.profopt))
#                 cmd = "gcc -fprofile-use %s.c -c -O3 -pipe -o %s.o" % (b, b)
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
        
    def make_module(self):
        base = self.setup()
        self.cmds_bytecode(base)
        self.cmds_objects(base)

        # link (ok this is a mess!)
        library_files = self.genllvm.db.gcpolicy.gc_libraries()
        gc_libs = ' '.join(['-l' + lib for lib in library_files])

        if sys.platform == 'darwin':
            libdir = '/sw/lib'
            gc_libs_path = '-L%s -ldl' % libdir
            self.cmds.append("gcc -O3 %s.o %s %s -lm -bundle -o %s.so" % (base, gc_libs_path, gc_libs, base))
        else:

            gc_libs_path = '-shared'
            self.cmds.append("gcc -O3 %s.o %s %s -pipe -o %s.so" % (base, gc_libs_path, gc_libs, base))

        try:
            self.execute_cmds()
            modname = CtypesModule(self.genllvm, "%s.so" % base).create()

        finally:
            self.lastdir.chdir()

        return modname, str(self.dirpath)

    def make_standalone(self, exename):
        base = self.setup()
        self.cmds_bytecode(base)
        self.cmds_objects(base)

        object_files = ["-L/sw/lib"]
        library_files = self.genllvm.db.gcpolicy.gc_libraries()
        gc_libs = ' '.join(['-l' + lib for lib in library_files])

        if sys.platform == 'darwin':
            libdir = '/sw/' + "/lib"
            gc_libs_path = '-L%s -ldl' % libdir
        else:
            gc_libs_path = '-static'

        self.cmds.append("gcc -O3 %s.o %s %s -lm -pipe -o %s" % (base, gc_libs_path, gc_libs, exename))

        try:
            self.execute_cmds()
        finally:
            self.lastdir.chdir()

        return str(self.dirpath.join(exename))
