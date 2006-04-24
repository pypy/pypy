import autopath
import os
import py

from pypy.tool.udir import udir
from pypy.objspace.flow import FlowObjSpace
from pypy.translator.translator import TranslationContext
from pypy.translator.cl.gencl import GenCL
from py.process import cmdexec 
from pypy import conftest

global_cl = None

def is_on_path(name):
    try:
        py.path.local.sysfind(name)
    except py.error.ENOENT:
        return False
    else:
        return True

def cl_detect():
    cl = os.getenv("PYPY_CL")
    if cl:
        return cl
    if is_on_path("clisp"):
        return "clisp"
    if is_on_path("lisp"):
        if is_on_path("cmuclinvoke.sh"):
            return "cmuclinvoke.sh"
    if is_on_path("sbcl"):
        if is_on_path("sbclinvoke.sh"):
            return "sbclinvoke.sh"
    return None

class Literal:
    def __init__(self, val):
        self.val = val

def readlisp(s):
    # Return bool/int/str or give up
    import string
    s = s.strip()
    if s == "T":
        return True
    elif s == "NIL":
        return False
    elif s[0] == '"':
        return s[1:-1]
    elif s.strip(string.digits) == '':
        return int(s)
    else:
        return Literal(s)

def writelisp(gen, obj):
    #if isinstance(obj, (bool, int, type(None), str)):
    if isinstance(obj, (int, type(None), str)):
        return gen.repr_const(obj)
    if isinstance(obj, (tuple, list)):
        content = ' '.join([writelisp(gen, elt) for elt in obj])
        content = '(' + content + ')'
        if isinstance(obj, list):
            content = '#' + content
        elif isinstance(obj, tuple):
            content = "'" + content # quote Lisp list
        return content

def make_cl_func(func, argtypes=[]):
    global global_cl
    if global_cl is None:
        global_cl = cl_detect()
    if not global_cl:
        py.test.skip("Common Lisp neither configured nor detected.")
    return _make_cl_func(func, global_cl, udir, argtypes)

def _make_cl_func(func, cl, path, argtypes=[]):
    t = TranslationContext()
    t.buildannotator().build_types(func, argtypes)
    t.buildrtyper(type_system="ootype").specialize()

    if conftest.option.view:
        t.view()
    
    graph = t.graphs[0]
        
    gen = GenCL(graph, argtypes)
    out = gen.globaldeclarations() + '\n' + gen.emitcode()
    i = 1
    fpath = path.join("%s.lisp" % graph.name)
    def _(*args):
        fpath.write(out)
        fp = file(str(fpath), "a")
        print >>fp, "(write (", graph.name,
        for arg in args:
            print >>fp, writelisp(gen, arg),
        print >>fp, "))"
        fp.close()
        output = cmdexec("%s %s" % (cl, str(fpath)))
        return readlisp(output)
    return _

if __name__ == '__main__':
    # for test
    # ultimately, GenCL's str and conv will move to here
    def f(): pass
    fun = FlowObjSpace().build_flow(f)
    gen = GenCL(fun)

    what = [True, "universe", 42, None, ("of", "them", ["eternal", 95])]
    it = writelisp(gen, what)
    print what
    print it
    assert it == '#(t "universe" 42 nil \'("of" "them" #("eternal" 95)))'
