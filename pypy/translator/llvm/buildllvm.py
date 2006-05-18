import os
import sys

import py

from pypy.translator.llvm.log import log
from pypy.translator.tool import stdoutcapture
from pypy.translator.tool.cbuild import make_c_from_pyxfile

import distutils.sysconfig

def llvm_is_on_path():
    try:
        py.path.local.sysfind("llvm-as")
        py.path.local.sysfind("llvm-gcc")
    except py.error.ENOENT: 
        return False 
    return True

def llvm_version():
    v = os.popen('llvm-as -version 2>&1').readline()
    v = ''.join([c for c in v if c.isdigit()])
    v = int(v) / 10.0
    return v

def optimizations(simple, use_gcc):

    if simple:
        opts = "-globaldce -adce -deadtypeelim -simplifycfg -raiseallocs " \
               "-simplifycfg -mem2reg -simplifycfg -verify "
    else:
        cmd = "gccas /dev/null -o /dev/null -debug-pass=Arguments 2>&1"
        gccas_output = os.popen(cmd)
        opts = gccas_output.read()[17:-1] + " "
        opts += "-globalopt -constmerge -ipsccp -deadargelim -inline " \
                "-instcombine -scalarrepl -globalsmodref-aa -licm -load-vn " \
                "-gcse -instcombine -simplifycfg -globaldce "
        #opts += "-inline-threshold=200 "   #default: 200
    return opts

def compile_module(module, source_files, object_files, library_files):

    open("%s_setup.py" % module, "w").write(str(py.code.Source(
        '''
        from distutils.core import setup
        from distutils.extension import Extension
        setup(name="%(module)s",
            ext_modules = [Extension(
                name = "%(module)s",
                sources = %(source_files)s,
                libraries = %(library_files)s,
                extra_objects = %(object_files)s)])
        ''' % locals())))
    cmd ="python %s_setup.py build_ext --inplace --force" % module
    log.build(cmd)
    py.process.cmdexec(cmd)

def make_module_from_llvm(genllvm, llvmfile,
                          pyxfile=None, optimize=True, exe_name=None,
                          profile=False, cleanup=False, use_gcc=True):

    if exe_name:
        use_gcc = False #XXX trying to get of gcc (at least for standalones)

    # where we are building
    dirpath = llvmfile.dirpath()

    # change into dirpath and store current path to change back
    lastdir = str(py.path.local())
    os.chdir(str(dirpath))

    b = llvmfile.purebasename

    # run llvm assembler and optimizer
    simple_optimizations = not optimize
    opts = optimizations(simple_optimizations, use_gcc)
    cmds = ["llvm-as < %s.ll | opt %s -f -o %s.bc" % (b, opts, b)]

    object_files = ["-L%s/lib" % distutils.sysconfig.EXEC_PREFIX]
    library_files = genllvm.db.gcpolicy.gc_libraries()
    gc_libs = ' '.join(['-l' + lib for lib in library_files])

    if sys.platform == 'darwin':
        libdir = distutils.sysconfig.EXEC_PREFIX + "/lib"
        gc_libs_path = '-L%s -ldl' % libdir
    else:
        gc_libs_path = '-static'

    if pyxfile:
        modname = pyxfile.purebasename
        source_files = ["%s.c" % modname]
    else:
        source_files = []

    if not use_gcc:
        llc_params = llvm_version() > 1.7 and '-enable-x86-fastcc' or ''
        if llc_params and exe_name and sys.platform != 'darwin':
            llc_params += ' -relocation-model=static'   #XXX while llvm jumptables not with PIC
        cmds.append("llc %s %s %s.bc -f -o %s.s" % (llc_params, genllvm.db.exceptionpolicy.llc_options(), b, b))
        cmds.append("as %s.s -o %s.o" % (b, b))

        if exe_name:
            cmd = "gcc %s.o %s %s -lm -pipe -o %s" % (b, gc_libs_path, gc_libs, exe_name)
            cmds.append(cmd)
        object_files.append("%s.o" % b)
    else:
        cmds.append("llc %s %s.bc -march=c -f -o %s.c" % (genllvm.db.exceptionpolicy.llc_options(), b, b))
        if exe_name:
            cmd = "gcc %s.c -c -O3 -pipe" % b
            if profile:
                cmd += ' -pg'
            else:
                cmd += ' -fomit-frame-pointer'
            cmds.append(cmd)
            cmd = "gcc %s.o %s %s -lm -pipe -o %s" % (b, gc_libs_path, gc_libs, exe_name)
            if profile:
                cmd += ' -pg'
            cmds.append(cmd)
        source_files.append("%s.c" % b)

    if cleanup and exe_name and not profile:
        cmds.append('strip ' + exe_name)
        upx = os.popen('which upx 2>&1').read()
        # compress file
        if upx and not upx.startswith('which'): 
            cmds.append('upx ' + exe_name)

    try:
        c = stdoutcapture.Capture(mixed_out_err = True)
        log.build("working in", py.path.local())
        try:
            try:
                for cmd in cmds:
                    log.build(cmd)
                    py.process.cmdexec(cmd)
                if pyxfile:
                    make_c_from_pyxfile(pyxfile)
                    compile_module(modname, source_files, object_files, library_files)
            finally:
                foutput, ferror = c.done()
        except:
            data = 'OUTPUT:\n' + foutput.read() + '\n\nERROR:\n' + ferror.read()
            if pyxfile:
                fdump = open("%s.errors" % modname, "w")
                fdump.write(data)
                fdump.close()
            log.build(data)
            raise
    finally:
        os.chdir(str(lastdir))

    if pyxfile:
        return modname, str(dirpath)

    if exe_name:
        exe_path = str(llvmfile.dirpath().join(exe_name))
        return exe_path
