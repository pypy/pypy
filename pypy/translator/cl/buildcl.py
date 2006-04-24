import os
import py

from pypy.tool.udir import udir
from pypy.objspace.flow import FlowObjSpace
from pypy.translator.translator import TranslationContext
from pypy.translator.cl.gencl import GenCL
from pypy.translator.cl.clrepr import repr_const, repr_fun_name
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
    if is_on_path("openmcl"):
        if is_on_path("openmclinvoke.sh"):
            return "openmclinvoke.sh"
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
    lines = s.splitlines()
    lines = [ line for line in lines if line and not line.startswith(';') ]
    assert len(lines) == 1
    s = lines[0]
    s = s.strip()
    if s == "T":
        return True
    elif s == "NIL":
        return False
    elif s[0] == '"':
        return s[1:-1]
    elif s.isdigit():
        return int(s)
    else:
        return Literal(s)

def writelisp(obj):
    if isinstance(obj, (bool, int, type(None), str)):
        return repr_const(obj)
    if isinstance(obj, (tuple, list)):
        content = ' '.join([writelisp(elt) for elt in obj])
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

pretty_printer = """
(let* ((filename "%s")
       (content (with-open-file (f filename)
         (loop for sexp = (read f nil) while sexp collect sexp))))
  (with-open-file (out filename
      :direction :output :if-does-not-exist :create :if-exists :supersede)
    (loop for sexp in content do (pprint sexp out))))
"""

def _make_cl_func(func, cl, path, argtypes=[]):
    t = TranslationContext()
    t.buildannotator().build_types(func, argtypes)
    t.buildrtyper(type_system="ootype").specialize()

    if conftest.option.view:
        t.view()
    
    graph = t.graphs[0]
        
    gen = GenCL(graph, argtypes)
    out = gen.emitcode()
    i = 1
    fpath = path.join("%s.lisp" % graph.name)

    if conftest.option.prettyprint:
        script = path.join(".printer.lisp")
        fp = file(str(script), "w")
        fp.write(pretty_printer % (fpath,))
        fp.close()

    def _(*args):
        fpath.write(out)
        fp = file(str(fpath), "a")
        print >>fp, "(write (", repr_fun_name(graph.name),
        for arg in args:
            print >>fp, writelisp(arg),
        print >>fp, "))"
        fp.close()
        if conftest.option.prettyprint:
            cmdexec("%s %s" % (cl, str(script)))
        output = cmdexec("%s %s" % (cl, str(fpath)))
        return readlisp(output)
    return _
