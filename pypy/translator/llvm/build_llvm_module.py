"""
Build a Python module out of llvmfile and a Pyrex wrapper file.
"""

import os, sys, inspect, re, exceptions

from py.process import cmdexec 
from py import path 
import py

from pypy.translator.tool.cbuild import make_c_from_pyxfile
from pypy.translator.tool import stdoutcapture
from pypy.translator.llvm.genllvm import use_boehm_gc
from pypy.translator.llvm.log import log

EXCEPTIONS_SWITCHES   = "-enable-correct-eh-support"
SIMPLE_OPTIMIZATION_SWITCHES = (" ".join([
    # kill code - hopefully to speed things up
    "-globaldce -adce -deadtypeelim -simplifycfg",

    # call %malloc -> malloc inst
    "-raiseallocs",

    # clean up disgusting code
    "-simplifycfg",

    # kill useless allocas
    "-mem2reg",

    # clean up disgusting code
    "-simplifycfg",
    ]))

# XXX: TODO: refactoring: use gccas to populate this list
# suggested by: gccas /dev/null -o /dev/null -debug-pass=Arguments
OPTIMIZATION_SWITCHES = (" ".join([
    "-verify -lowersetjmp -funcresolve -raiseallocs -simplifycfg -mem2reg -globalopt -globaldce -ipconstprop -deadargelim -instcombine -simplifycfg -prune-eh -inline -simplify-libcalls -argpromotion -raise -tailduplicate -simplifycfg -scalarrepl -instcombine -break-crit-edges -condprop -tailcallelim -simplifycfg -reassociate -loopsimplify -licm -instcombine -indvars -loop-unroll -instcombine -load-vn -gcse -sccp -instcombine -break-crit-edges -condprop -dse -mergereturn -adce -simplifycfg -deadtypeelim -constmerge -verify"
    ]))

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
    cmdexec(cmd)

def make_module_from_llvm(llvmfile, pyxfile=None, optimize=True, exe_name=None):
    include_dir = py.magic.autopath().dirpath()
    dirpath = llvmfile.dirpath()
    lastdir = path.local()
    os.chdir(str(dirpath))
    b = llvmfile.purebasename
    if pyxfile:
        modname = pyxfile.purebasename
        source_files = [ "%s.c" % modname ]
    else:
        source_files = []
    object_files = []
    library_files = []
    if use_boehm_gc:
        gc_libs = '-lgc -lpthread'
        library_files.append('gc')
    else:
        gc_libs = ''

    if optimize:
        optimization_switches = OPTIMIZATION_SWITCHES
    else:
        optimization_switches = SIMPLE_OPTIMIZATION_SWITCHES

    #XXX outcommented for testing merging extern.ll in main .ll file
    #cmds = ["llvm-as %s.ll" % b]
    #
    #bcfile = dirpath.join("externs", "externs_linked.bc")
    #cmds.append("llvm-link %s.bc %s -o %s_all.bc" % (b, str(bcfile), b))
    #ball = str(dirpath.join('%s_all.bc' % b))
    #cmds.append("opt %s %s -f -o %s.bc" % (OPTIMIZATION_SWITCHES, ball, b))

    cmds = ["llvm-as < %s.ll | opt %s -f -o %s.bc" % (b, OPTIMIZATION_SWITCHES, b)]

    if False and sys.maxint == 2147483647:        #32 bit platform
        cmds.append("llc %s %s.bc -f -o %s.s" % (EXCEPTIONS_SWITCHES, b, b))
        cmds.append("as %s.s -o %s.o" % (b, b))
        if exe_name:
            cmds.append("gcc %s.o %s -lm -ldl -o %s" % (b, gc_libs, exe_name))
        object_files.append("%s.o" % b)
    else:       #assume 64 bit platform (x86-64?)
        #this special case for x86-64 (called ia64 in llvm) can go as soon as llc supports ia64 assembly output!
        cmds.append("llc %s %s.bc -march=c -f -o %s.c" % (EXCEPTIONS_SWITCHES, b, b))
        if exe_name:
            #XXX TODO: use CFLAGS when available
            cmds.append("gcc %s.c -c -march=pentium4 -O2 -fomit-frame-pointer" % (b,))
            cmds.append("gcc %s.o %s -lm -ldl -o %s" % (b, gc_libs, exe_name))
        source_files.append("%s.c" % b)

    try:
        if pyxfile:
            log.build("modname", modname)
        c = stdoutcapture.Capture(mixed_out_err = True)
        log.build("working in", path.local())
        try:
            try:
                for cmd in cmds:
                    #log.build(cmd)
                    cmdexec(cmd)
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
        # XXX do we need to do some check on fout/ferr?
        # XXX not a nice way to import a module
        if pyxfile:
            log.build("inserting path to sys.path", dirpath)
            sys.path.insert(0, '.')
            cmd = "import %(modname)s as testmodule" % locals()
            log.build(cmd)
            exec cmd
            sys.path.pop(0)
    finally:
        os.chdir(str(lastdir))
    if pyxfile:
        return testmodule
    if exe_name:
        exe_path = str(llvmfile.dirpath().join(exe_name))
        return exe_path
