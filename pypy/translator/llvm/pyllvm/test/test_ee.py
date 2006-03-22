import py
from pypy.translator.llvm.buildllvm import llvm_is_on_path
if not llvm_is_on_path():
    py.test.skip("llvm not found")

from pypy.translator.llvm.pyllvm.build import pyllvm


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
    for function in functions:
        returnId, name, args = function
        assert len(function) == 3
        assert returnId > 0
        assert name in ('gethellostr', 'hello')
        assert len(args) == 0

def test_call_parse_once():
    ee = get_fresh_ee()
    ee.parse(codepath.join("hello.s").read())
    assert ee.call("hello") == 0
    assert ee.call("gethellostr") == "hello world\n"
    py.test.raises(Exception, ee.call, "gethellostrx")
    py.test.raises(Exception, ee.call, "gethellostr", 1)

def test_call_parse_twice():
    ee = get_fresh_ee()
    ee.parse(codepath.join("hello.s").read())
    assert ee.call("gethellostr") == "hello world\n"
    ee.parse(codepath.join("addnumbers.s").read())
    assert ee.call("add", 10, 32) == 42
    assert ee.call("gethellostr") == "hello world\n"

def TODOtest_call_between_parsed_code():
    pass

def TODOtest_share_data_between_parsed_code():
    pass

def TODOtest_delete_function():
    pass
