import py
from prolog.interpreter import arithmetic
from prolog.interpreter.parsing import parse_file, TermBuilder
from prolog.interpreter import helper, term, error
from prolog.builtin.register import expose_builtin
from prolog.interpreter.memo import CopyMemo

# ___________________________________________________________________
# comparison and unification of terms

@expose_builtin("=", unwrap_spec=["raw", "raw"])
def impl_unify(engine, heap, obj1, obj2):
    obj1.unify(obj2, heap)

@expose_builtin("unify_with_occurs_check",
                unwrap_spec=["raw", "raw"])
def impl_unify_with_occurs_check(engine, heap, obj1, obj2):
    obj1.unify(obj2, heap, occurs_check=True)

@expose_builtin("\\=", unwrap_spec=["raw", "raw"])
def impl_does_not_unify(engine, heap, obj1, obj2):
    new_heap = heap.branch()
    try:
        obj1.unify(obj2, new_heap)
    except error.UnificationFailed:
        new_heap.revert_upto(heap)
        return
    new_heap.revert_upto(heap)
    raise error.UnificationFailed()


for ext, prolog, python in [("eq", "==", "== 0"),
                            ("ne", "\\==", "!= 0"),
                            ("lt", "@<", "== -1"),
                            ("le", "@=<", "!= 1"),
                            ("gt", "@>", "== 1"),
                            ("ge", "@>=", "!= -1")]:
    exec py.code.Source("""
@expose_builtin(prolog, unwrap_spec=["obj", "obj"])
def impl_standard_comparison_%s(engine, heap, obj1, obj2):
    c = term.cmp_standard_order(obj1, obj2, heap)
    if not c %s:
        raise error.UnificationFailed()""" % (ext, python)).compile()
 
@expose_builtin("compare", unwrap_spec=["raw", "obj", "obj"])
def impl_compare(engine, heap, result, obj1, obj2):
    """docstring for impl_compare"""
    c = term.cmp_standard_order(obj1, obj2, heap)
    if c == 0:
        res = term.Callable.build("=")
    elif c == -1:
        res = term.Callable.build("<")
    else:
        res = term.Callable.build(">")
    result.unify(res, heap)

@expose_builtin("?=", unwrap_spec=["obj", "obj"])
def impl_strictly_identical_or_not_unifiable(engine, heap, obj1, obj2):
    try:
        impl_standard_comparison_eq(engine, heap, obj1, obj2)
        return
    except error.UnificationFailed:
        memo = CopyMemo()
        copy1 = obj1.copy(heap, memo)
        copy2 = obj2.copy(heap, memo)
        try:
            copy1.unify(copy2, heap)
        except error.UnificationFailed:
            return
    raise error.UnificationFailed()
