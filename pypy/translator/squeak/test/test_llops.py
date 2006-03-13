from pypy.translator.squeak.test.runtest import compile_function
from pypy.translator.translator import TranslationContext
from pypy.objspace.flow.operation import FunctionByName
from pypy.objspace.flow.model import *

def optest(testcase):
    opname = testcase[0]
    llopname = testcase[1]
    args = testcase[2:]

    # This code adpated from translator/c/test/test_operation.py
    inputvars = [Variable() for _ in args]
    block = Block(inputvars)
    op = SpaceOperation(opname, inputvars, Variable())
    block.operations.append(op)
    graph = FunctionGraph('operationdummy', block)
    block.closeblock(Link([op.result], graph.returnblock))

    annotation = [type(a) for a in args]
    sqfunc = compile_function(operationdummy, annotation, graph)

    # Make sure we actually test what we intend to test
    found_llop = False
    for op in sqfunc.graph.startblock.operations:
        if op.opname == llopname:
            found_llop = True
            break
    assert found_llop

    expected_result = FunctionByName[opname](*args)
    assert sqfunc(*args) == str(expected_result)

def operationdummy(v1, v2):
    pass

def test_intoperations():
    tests = [
        # XXX Must handle overflows for all integer ops
        ("add", "int_add", 1, 2),
        ("sub", "int_sub", 1, 3),
        ("mul", "int_mul", 2, 3),
        # I think int_div and int_truediv are currently never generated
        ("floordiv", "int_floordiv", 7, 3),
        ("floordiv", "int_floordiv", -7, 3),
    ]
    for t in tests:
        yield optest, t

