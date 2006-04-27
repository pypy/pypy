import os
import py

from pypy.tool.udir import udir
from pypy.translator.translator import TranslationContext
from pypy.translator.cl.gencl import GenCL
from pypy.translator.cl.clrepr import clrepr
from pypy import conftest
from pypy.translator.cl import conftest as clconftest

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

def readlisp(s):
    # Return bool/char/str/int/float or give up
    lines = s.splitlines()
    lines = [ line for line in lines if line and not line.startswith(';') ]
    assert len(lines) == 1
    s = lines[0]
    s = s.strip()
    if s == "T":
        return True
    elif s == "NIL":
        return False
    elif s.startswith("#\\"):
        return s[2:]
    elif s[0] == '"':
        return s[1:-1]
    elif s.isdigit():
        return int(s)
    try:
        return float(s)
    except ValueError:
        pass
    raise NotImplementedError("cannot read %s" % (s,))

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
    out = generate_cl_func(func, argtypes)
    fpath = path.join("%s.lisp" % func.func_name)

    if clconftest.option.prettyprint:
        script = path.join(".printer.lisp")
        fp = file(str(script), "w")
        fp.write(pretty_printer % (fpath,))
        fp.close()

    def _(*args):
        fpath.write(out)
        fp = file(str(fpath), "a")
        print >>fp, "(write (", clrepr(func.func_name),
        for arg in args:
            print >>fp, clrepr(arg),
        print >>fp, "))"
        fp.close()
        if clconftest.option.prettyprint:
            py.process.cmdexec("%s %s" % (cl, str(script)))
        output = py.process.cmdexec("%s %s" % (cl, str(fpath)))
        return readlisp(output)
    return _

def generate_cl_func(func, argtypes=[]):
    t = TranslationContext()
    t.buildannotator().build_types(func, argtypes)
    t.buildrtyper(type_system="ootype").specialize()

    if conftest.option.view:
        t.view()
    
    gen = GenCL(t, func)
    code = gen.emitcode()
    return code
