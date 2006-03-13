from pypy.translator.squeak.test.runtest import compile_function

def optest(testcase):
    opname = testcase[0]
    opstring = testcase[1]
    args = testcase[2:]
    annotation = [type(a) for a in args]
    func = opfunction(opstring, args)
    sqfunc = compile_function(func, annotation)

    # Make sure we actually test what we intend to test
    found_llop = False
    for op in sqfunc.graph.startblock.operations:
        if op.opname == opname:
            found_llop = True
            break
    assert found_llop

    assert sqfunc(*args) == str(func(*args))

def opfunction(opstring, annotation):
    exec """def fn(v1, v2):
                return v1 %s v2""" % opstring
    return fn

def test_intoperations():
    tests = [
        # XXX Must handle overflows for all integer ops
        ("int_add", "+", 1, 2),
        ("int_sub", "-", 1, 3),
        ("int_mul", "*", 2, 3),
        # XXX how to produce int_div and int_truediv?
        ("int_floordiv", "//", 7, 3),
        ("int_floordiv", "//", -7, 3),
    ]
    for t in tests:
        yield optest, t

