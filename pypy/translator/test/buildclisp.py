import autopath

import sys
from cStringIO import StringIO
from pypy.objspace.flow import Space
from pypy.translator.gencl import GenCL
from vpath.adapter.process import exec_cmd

def readlisp(s):
    # For now, let's return int only
    return int(s)

def make_cl_func(func, path):
    fun = Space().build_flow(func)
    gen = GenCL(fun)
    out = StringIO()
    sys.stdout = out
    gen.emit()
    sys.stdout = sys.__stdout__
    fp = path.join("test.lisp")
    i = 0
    while fp.exists():
        fp = path.join("test%d.lisp" % i)
        i += 1
    fp.write(out.getvalue())
    fname = fp.path
    def _(*args):
        fp = file(fname, "a")
        print >>fp, "(write (", fun.functionname,
        for arg in args:
            print >>fp, str(arg),
        print >>fp, "))"
        fp.close()
        output = exec_cmd("clisp %s" % fname)
        return readlisp(output)
    return _
