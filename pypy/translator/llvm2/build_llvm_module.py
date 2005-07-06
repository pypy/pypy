"""
Build a Python module out of llvmfile and a Pyrex wrapper file.
"""

import os, sys, inspect, re, exceptions

from py.process import cmdexec 
from py import path 
import py

from pypy.tool.udir import udir
from pypy.translator.pyrex.genpyrex import GenPyrex
from pypy.translator.tool.buildpyxmodule import make_c_from_pyxfile
from pypy.translator.tool import stdoutcapture
from pypy.translator.llvm2.genllvm import use_boehm_gc

debug = True

class CompileError(exceptions.Exception):
    pass

OPTIMIZATION_SWITCHES = "-simplifycfg -mem2reg -instcombine -dce -inline"

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
    cmd = "python %s_setup.py build_ext --inplace --force" % module
    if debug: print cmd
    cmdexec(cmd)

def make_module_from_llvm(llvmfile, pyxfile, optimize=True):
    include_dir = py.magic.autopath().dirpath()
    dirpath = llvmfile.dirpath()
    lastdir = path.local()
    os.chdir(str(dirpath))
    modname = pyxfile.purebasename
    b = llvmfile.purebasename
    source_files = [ "%s.c" % modname ]
    object_files = []
    library_files = []
    if use_boehm_gc:
        library_files.append('gc')

    if sys.maxint == 2147483647:        #32 bit platform
        if optimize:
            cmds = ["llvm-as %s.ll -f -o %s.bc" % (b, b), 
                    "opt %s -f %s.bc -o %s_optimized.bc" % (OPTIMIZATION_SWITCHES, b, b),
                    "llc -enable-correct-eh-support %s_optimized.bc -f -o %s.s" % (b, b)]
        else:
            cmds = ["llvm-as %s.ll -f -o %s.bc" % (b, b),
                    "llc -enable-correct-eh-support %s.bc -f -o %s.s" % (b, b)]
        cmds.append("as %s.s -o %s.o" % (b, b))
        object_files.append("%s.o" % b)
    else:       #assume 64 bit platform (x86-64?)
        #this special case for x86-64 (called ia64 in llvm) can go as soon as llc supports ia64 assembly output!
        if optimize:
            cmds = ["llvm-as %s.ll -f -o %s.bc" % (b, b), 
                    "opt %s -f %s.bc -o %s_optimized.bc" % (OPTIMIZATION_SWITCHES, b, b),
                    "llc -enable-correct-eh-support %s_optimized.bc -march=c -f -o %s.c" % (b, b)]
        else:
            cmds = ["llvm-as %s.ll -f -o %s.bc" % (b, b),
                    "llc -enable-correct-eh-support %s.bc -march=c -f -o %s.c" % (b, b)]
        source_files.append("%s.c" % b)

    try:
        if debug: print "modname", modname
        c = stdoutcapture.Capture(mixed_out_err = True)
        if debug: print "working in", path.local()
        try:
            try:
                for cmd in cmds:
                    if debug: print cmd
                    cmdexec(cmd)
                make_c_from_pyxfile(pyxfile)
                compile_module(modname, source_files, object_files, library_files)
            finally:
                foutput, foutput = c.done()
        except:
            data = foutput.read()
            fdump = open("%s.errors" % modname, "w")
            fdump.write(data)
            fdump.close()
            print data
            raise
        # XXX do we need to do some check on fout/ferr?
        # XXX not a nice way to import a module
        if debug: print "inserting path to sys.path", dirpath
        sys.path.insert(0, '.')
        if debug: print "import %(modname)s as testmodule" % locals()
        exec "import %(modname)s as testmodule" % locals()
        sys.path.pop(0)
    finally:
        os.chdir(str(lastdir))
        #if not debug:
        #dirpath.rmtree()
    return testmodule
