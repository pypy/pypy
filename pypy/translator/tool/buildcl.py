import autopath

from pypy.objspace.flow import FlowObjSpace
from pypy.translator.translator import TranslationContext
from pypy.translator.gencl import GenCL
from py.process import cmdexec 
from pypy import conftest

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
