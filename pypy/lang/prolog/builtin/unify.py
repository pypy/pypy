import py
from pypy.lang.prolog.interpreter import arithmetic
from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# comparison and unification of terms

def impl_unify(engine, obj1, obj2):
    obj1.unify(obj2, engine.heap)
expose_builtin(impl_unify, "=", unwrap_spec=["raw", "raw"])

def impl_unify_with_occurs_check(engine, obj1, obj2):
    obj1.unify(obj2, engine.heap, occurs_check=True)
expose_builtin(impl_unify_with_occurs_check, "unify_with_occurs_check",
               unwrap_spec=["raw", "raw"])

def impl_does_not_unify(engine, obj1, obj2):
    try:
        branch = engine.heap.branch()
        try:
            obj1.unify(obj2, engine.heap)
        finally:
            engine.heap.revert(branch)
    except error.UnificationFailed:
        return
    raise error.UnificationFailed()
expose_builtin(impl_does_not_unify, "\\=", unwrap_spec=["raw", "raw"])


for ext, prolog, python in [("eq", "==", "== 0"),
                            ("ne", "\\==", "!= 0"),
                            ("lt", "@<", "== -1"),
                            ("le", "@=<", "!= 1"),
                            ("gt", "@>", "== 1"),
                            ("ge", "@>=", "!= -1")]:
    exec py.code.Source("""
def impl_standard_comparison_%s(engine, obj1, obj2):
    c = term.cmp_standard_order(obj1, obj2, engine.heap)
    if not c %s:
        raise error.UnificationFailed()""" % (ext, python)).compile()
    expose_builtin(globals()["impl_standard_comparison_%s" % (ext, )], prolog,
                   unwrap_spec=["obj", "obj"])
 
