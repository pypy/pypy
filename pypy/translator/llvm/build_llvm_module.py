"""
Build a pyrex module out of llvmfile
"""

import autopath

import os, sys, inspect, re, exceptions

from py.process import cmdexec 
from py import path 

from pypy.tool.udir import udir
from pypy.translator.genpyrex import GenPyrex
from pypy.translator.tool.buildpyxmodule import make_c_from_pyxfile
from pypy.translator.tool import stdoutcapture

debug = 1

class CompileError(exceptions.Exception):
    pass

def system_trace(cmd):
    print cmd
    return old_system(cmd)

old_system = os.system
os.system = system_trace

def make_module_from_llvm(llvmfile, pyxfile, optimize=True):
    include_dir = autopath.this_dir
    dirpath = llvmfile.dirpath()
    lastdir = path.local()
    os.chdir(str(dirpath))
    modname = pyxfile.purebasename
    ops1 = ["llvm-as %s -f -o %s.bc" % (llvmfile, llvmfile.purebasename), 
            "llvmc -f -O3 %s.bc -o %s_optimized.o" % (llvmfile.purebasename,
                                                      llvmfile.purebasename),
            "llc %s_optimized.o.bc -f -o %s.s" % (llvmfile.purebasename,
                                                   llvmfile.purebasename),
            "as %s.s -o %s.o" % (llvmfile.purebasename, llvmfile.purebasename)]
    if not optimize:
        ops1 = ["llvm-as %s -f" % llvmfile,
                "llc %s.bc -f -o %s.s" % (llvmfile.purebasename,
                                          llvmfile.purebasename),
                "as %s.s -o %s.o" % (llvmfile.purebasename,
                                          llvmfile.purebasename)]
    ops2 = ["gcc -c -fPIC -I/usr/include/python %s.c" % pyxfile.purebasename,
           "gcc -shared %s.o %s.o -o %s.so" % (llvmfile.purebasename,
                                                modname, modname)]
    try:
        if debug: print "modname", modname
        c = stdoutcapture.Capture(mixed_out_err = True)
        if debug: print "working in", path.local()
        try:
            try:
                for op in ops1:
                    print op
                    cmdexec(op)
                make_c_from_pyxfile(pyxfile)
                for op in ops2:
                    print op
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
