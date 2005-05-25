"""
Build a Python module out of llvmfile and a Pyrex wrapper file.
"""

import autopath

import os, sys, inspect, re, exceptions

from py.process import cmdexec 
from py import path 

from pypy.tool.udir import udir
from pypy.translator.pyrex.genpyrex import GenPyrex
from pypy.translator.tool.buildpyxmodule import make_c_from_pyxfile
from pypy.translator.tool import stdoutcapture

debug = False

class CompileError(exceptions.Exception):
    pass

OPTIMIZATION_SWITCHES = "-simplifycfg -mem2reg -instcombine -dce -inline"

def make_module_from_llvm(llvmfile, pyxfile, optimize=False):
    include_dir = autopath.this_dir
    dirpath = llvmfile.dirpath()
    lastdir = path.local()
    os.chdir(str(dirpath))
    modname = pyxfile.purebasename
    b = llvmfile.purebasename

    if sys.maxint == 2147483647:        #32 bit platform
        if optimize:
            ops1 = ["llvm-as %s.ll -f -o %s.bc" % (b, b), 
                    "opt %s -f %s.bc -o %s_optimized.bc" % (OPTIMIZATION_SWITCHES, b, b),
                    "llc -enable-correct-eh-support %s_optimized.bc -f -o %s.s" % (b, b),
                    "as %s.s -o %s.o" % (b, b)]
        else:
            ops1 = ["llvm-as %s.ll -f -o %s.bc" % (b, b),
                    "llc -enable-correct-eh-support %s.bc -f -o %s.s" % (b, b),
                    "as %s.s -o %s.o" % (b, b)]
        ops2 = ["gcc -c -shared -I/usr/include/python2.3 %s.c" % pyxfile.purebasename,
                "gcc -shared %s.o %s.o -o %s.so" % (b, modname, modname)]
    else:       #assume 64 bit platform (x86-64?)
        #this special case for x86-64 (called ia64 in llvm) can go as soon as llc supports ia64 assembly output!
        if optimize:
            ops1 = ["llvm-as %s.ll -f -o %s.bc" % (b, b), 
                    "opt %s -f %s.bc -o %s_optimized.bc" % (OPTIMIZATION_SWITCHES, b, b),
                    "llc -enable-correct-eh-support %s_optimized.bc -march=c -f -o %s.c" % (b, b)]
        else:
            ops1 = ["llvm-as %s.ll -f -o %s.bc" % (b, b),
                    "llc -enable-correct-eh-support %s.bc -march=c -f -o %s.c" % (b, b)]
        ops2 = ["gcc -shared -fPIC -I/usr/include/python2.3 %s.c %s.c -o %s.so" % (b, modname, modname)]

    try:
        if debug: print "modname", modname
        c = stdoutcapture.Capture(mixed_out_err = True)
        if debug: print "working in", path.local()
        try:
            try:
                for op in ops1:
                    if debug: print op
                    cmdexec(op)
                make_c_from_pyxfile(pyxfile)
                for op in ops2:
                    if debug: print op
                    cmdexec(op)
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
