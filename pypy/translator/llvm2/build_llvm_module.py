"""
Build a Python module out of llvmfile and a Pyrex wrapper file.
"""

import os, sys, inspect, re, exceptions

from py.process import cmdexec 
from py import path 
import py

from pypy.translator.tool.cbuild import make_c_from_pyxfile
from pypy.translator.tool import stdoutcapture
from pypy.translator.llvm2.genllvm import use_boehm_gc
from pypy.translator.llvm2.log import log

EXCEPTIONS_SWITCHES   = "-enable-correct-eh-support"
SIMPLE_OPTIMIZATION_SWITCHES = (" ".join([

    # call %malloc -> malloc inst
    "-raiseallocs",

    # clean up disgusting code
    "-simplifycfg",

    # kill useless allocas
    "-mem2reg",

    # clean up disgusting code
    "-simplifycfg",
    ]))

# suggested by: gccas /dev/null -o /dev/null -debug-pass=Arguments
OPTIMIZATION_SWITCHES = (" ".join([
    "-verify -lowersetjmp -funcresolve -raiseallocs -simplifycfg -mem2reg -globalopt -globaldce -ipconstprop -deadargelim -instcombine -simplifycfg -prune-eh -inline -simplify-libcalls -argpromotion -raise -tailduplicate -simplifycfg -scalarrepl -instcombine -break-crit-edges -condprop -tailcallelim -simplifycfg -reassociate -loopsimplify -licm -instcombine -indvars -loop-unroll -instcombine -load-vn -gcse -sccp -instcombine -break-crit-edges -condprop -dse -mergereturn -adce -simplifycfg -deadtypeelim -constmerge -verify"
    ]))

def compile_module(module, source_files, object_files, library_files):
    print 'QQQQQQQQQQQ compile_module'
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
    print 'QQQQQQQQQQQ make_module_from_llvm'
    print 'QQQQQQQ aaa make_module_from_llvm'
    include_dir = py.magic.autopath().dirpath()
    print 'QQQQQQQ AAA make_module_from_llvm'
    dirpath = llvmfile.dirpath()
    print 'QQQQQQQ BBB make_module_from_llvm'
    lastdir = path.local()
    print 'QQQQQQQ CCC make_module_from_llvm'
    os.chdir(str(dirpath))
    print 'QQQQQQQ DDD make_module_from_llvm'
    b = llvmfile.purebasename
    print 'QQQQQQQ EEE make_module_from_llvm'
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

    print 'QQQQQQQ 111 make_module_from_llvm'
    if False and sys.maxint == 2147483647:        #32 bit platform
        cmds.append("llc %s %s.bc -f -o %s.s" % (EXCEPTIONS_SWITCHES, b, b))
        cmds.append("as %s.s -o %s.o" % (b, b))
        if exe_name:
            cmds.append("gcc %s.o -static %s -lm -o %s" % (b, gc_libs, exe_name))
        object_files.append("%s.o" % b)
    else:       #assume 64 bit platform (x86-64?)
        #this special case for x86-64 (called ia64 in llvm) can go as soon as llc supports ia64 assembly output!
        cmds.append("llc %s %s.bc -march=c -f -o %s.c" % (EXCEPTIONS_SWITCHES, b, b))
        if exe_name:
            cmds.append("gcc %s.c -c -O2 -fomit-frame-pointer" % (b,))
            cmds.append("gcc %s.o -static %s -lm -o %s" % (b, gc_libs, exe_name))
        source_files.append("%s.c" % b)

    try:
        print 'QQQQQQQ 222 make_module_from_llvm'
        if pyxfile:
            log.build("modname", modname)
        c = stdoutcapture.Capture(mixed_out_err = True)
        log.build("working in", path.local())
        print 'QQQ X 111   make_module_from_llvm'
        try:
            print 'QQQ X 222   make_module_from_llvm'
            try:
                print 'QQQ X 333   make_module_from_llvm'
                for cmd in cmds:
                    #log.build(cmd)
                    print 'QQQQQQQQQQQ cmd', cmd
                    cmdexec(cmd)
                if pyxfile:
                    print 'QQQ aaa        ', cmd
                    make_c_from_pyxfile(pyxfile)
                    print 'QQQ bbb        ', cmd
                    compile_module(modname, source_files, object_files, library_files)
                    print 'QQQ ccc        ', cmd
                print 'QQQ ddd        ', cmd
            finally:
                print 'QQQ eee        ', cmd
                foutput, ferror = c.done()
        except:
            print 'QQQ fff        ', cmd
            data = 'OUTPUT:\n' + foutput.read() + '\n\nERROR:\n' + ferror.read()
            if pyxfile:
                fdump = open("%s.errors" % modname, "w")
                fdump.write(data)
                fdump.close()
            log.build(data)
            raise
        print 'QQQQQQQ bbb make_module_from_llvm'
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
    print 'QQQQQQQ ccc make_module_from_llvm'
    if pyxfile:
        print 'QQQQQQQ ddd make_module_from_llvm'
        return testmodule
    if exe_name:
        print 'QQQQQQQ eee make_module_from_llvm'
        return exe_name
