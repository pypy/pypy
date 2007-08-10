import py
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# arithmetic


def impl_between(engine, lower, upper, varorint, continuation):
    if isinstance(varorint, term.Var):
        for i in range(lower, upper):
            oldstate = engine.heap.branch()
            try:
                varorint.unify(term.Number(i), engine.heap)
                return continuation.call(engine, choice_point=True)
            except error.UnificationFailed:
                engine.heap.revert(oldstate)
        varorint.unify(term.Number(upper), engine.heap)
        return continuation.call(engine, choice_point=False)
    else:
        integer = helper.unwrap_int(varorint)
        if not (lower <= integer <= upper):
            raise error.UnificationFailed
    return continuation.call(engine, choice_point=False)
expose_builtin(impl_between, "between", unwrap_spec=["int", "int", "obj"],
               handles_continuation=True)

def impl_is(engine, var, num):
    var.unify(num, engine.heap)
impl_is._look_inside_me_ = True
expose_builtin(impl_is, "is", unwrap_spec=["raw", "arithmetic"])

for ext, prolog, python in [("eq", "=:=", "=="),
                            ("ne", "=\\=", "!="),
                            ("lt", "<", "<"),
                            ("le", "=<", "<="),
                            ("gt", ">", ">"),
                            ("ge", ">=", ">=")]:
    exec py.code.Source("""
def impl_arith_%s(engine, num1, num2):
    eq = False
    if isinstance(num1, term.Number):
        if isinstance(num2, term.Number):
            if not (num1.num %s num2.num):
                raise error.UnificationFailed()
            else:
                return
        n1 = num1.num
    else:
        assert isinstance(num1, term.Float)
        n1 = num1.floatval
    if isinstance(num2, term.Number):
        n2 = num2.num
    else:
        assert isinstance(num2, term.Float)
        n2 = num2.floatval
    eq = n1 %s n2
    if not eq:
        raise error.UnificationFailed()""" % (ext, python, python)).compile()
    expose_builtin(globals()["impl_arith_%s" % (ext, )], prolog,
                   unwrap_spec=["arithmetic", "arithmetic"])
 
