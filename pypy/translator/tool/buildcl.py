import autopath

from pypy.objspace.flow import FlowObjSpace
from pypy.translator.gencl import GenCL
from vpath.adapter.process import exec_cmd

def readlisp(s):
    # Return bool/int/str
    s = s.strip()
    if s == "T":
        return True
    elif s == "NIL":
        return False
    elif s[0] == '"':
        return s[1:-1]
    else:
        return int(s)

def _make_cl_func(func, cl, path, argtypes=[]):
    fun = FlowObjSpace().build_flow(func)
    gen = GenCL(fun)
    gen.annotate(argtypes)
    out = gen.emitcode()
    i = 1
    fpath = path.join("%s.lisp" % fun.name)
    def _(*args):
        fpath.write(out)
        fp = file(str(fpath), "a")
        print >>fp, "(write (", fun.name,
        for arg in args:
            print >>fp, gen.conv(arg),
        print >>fp, "))"
        fp.close()
        output = exec_cmd("%s %s" % (cl, str(fpath)))
        return readlisp(output)
    return _
