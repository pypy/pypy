import autopath

import sys
from cStringIO import StringIO
from pypy.objspace.flow import FlowObjSpace
from pypy.translator.gencl import GenCL
from vpath.adapter.process import exec_cmd

def readlisp(s):
    # For now, let's return int only
    return int(s)

def make_cl_func(func, cl, path):
    fun = FlowObjSpace().build_flow(func)
    gen = GenCL(fun)
    out = gen.emitcode()
    i = 1
    fpath = path.join("test%d.lisp" % i)
    while fpath.exists():
        fpath = path.join("test%d.lisp" % i)
        i += 1
    def _(*args):
        fpath.write(out)
        fp = file(str(fpath), "a")
        print >>fp, "(write (", fun.functionname,
        for arg in args:
            print >>fp, gen.conv(arg),
        print >>fp, "))"
        fp.close()
        output = exec_cmd("%s %s" % (cl, str(fpath)))
        return readlisp(output)
    return _
