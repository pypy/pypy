import py
from pypy.translator.llvm.buildllvm import llvm_is_on_path
py.test.skip("'python setup.py build_ext -i' is not quiet working yet")
if not llvm_is_on_path():
    py.test.skip("llvm not found")
from pypy.translator.llvm.pyllvm import pyllvm 

def test_execution_engine():
    ee = pyllvm.get_ee()
    ee = pyllvm.get_ee()
    ee = pyllvm.get_ee()
    pyllvm.delete_ee()
    ee2 = pyllvm.get_ee()
    ee2 = pyllvm.get_ee()
    ee2 = pyllvm.get_ee()

def get_fresh_ee():
    pyllvm.delete_ee()
    return pyllvm.get_ee()

codepath = py.path.local(__file__).dirpath()

def test_load():
    ee = get_fresh_ee()
    ee.parse(codepath.join("hello.s").read())
    ee.parse(codepath.join("addnumbers.s").read())

def test_functions():
    ee = get_fresh_ee()
    ee.parse(codepath.join("hello.s").read())
    functions = ee.functions()
    assert len(functions) == 2
    for ii in functions:
        assert len(ii) == 3
        assert ii[0] > 0
        assert ii[1] in 'gethellostr', 'hello'
        assert len(ii[2]) == 0

def test_call1():
    ee = get_fresh_ee()
    ee.parse(codepath.join("hello.s").read())
    assert ee.call("hello") == 0
    assert ee.call("gethellostr") == "hello world\n"
    try:
        ee.call("gethellostrx")
    except:
        pass
    try:
        ee.call("gethellostr", 1)
    except:
        pass
    ee.parse(codepath.join("addnumbers.s").read())
    assert ee.call("add", 10, 32) == 42
