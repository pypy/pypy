# Regression tests for assignment expressions (walrus) inside comprehensions,
# based on https://github.com/python/cpython/issues/87447: only names that
# are directly bound by the comprehension's for-target forbid rebinding via
# ':='. Names that merely appear (in Load context) inside a complex target,
# e.g. as part of a subscript or attribute target, are not iteration
# variables and may be freely rebound.

TARGET = "a, (*b, c[d+e::f(g)], h.i)"

def _check_valid(fmt):
    for name in "cdefgh":
        code = fmt % (name, TARGET)
        with __import__("pytest").raises(NameError):
            exec(code, {})
        exec("lambda: %s" % code, {})

def test_valid_rebind_genexp():
    _check_valid("((%s := 1) for %s in j)")

def test_valid_rebind_listcomp():
    _check_valid("[(%s := 1) for %s in j]")

def test_valid_rebind_setcomp():
    _check_valid("{(%s := 1) for %s in j}")

def _check_invalid(fmt):
    for name in "ab":
        code = fmt % (name, TARGET)
        with __import__("pytest").raises(SyntaxError) as info:
            exec(code, {})
        assert ("cannot rebind comprehension iteration variable '%s'"
                % name) in str(info.value)

def test_invalid_rebind_genexp():
    _check_invalid("((%s := 1) for %s in j)")

def test_invalid_rebind_listcomp():
    _check_invalid("[(%s := 1) for %s in j]")

def test_invalid_rebind_setcomp():
    _check_invalid("{(%s := 1) for %s in j}")
