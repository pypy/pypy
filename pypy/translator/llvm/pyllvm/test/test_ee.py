import py
from pypy.translator.llvm.buildllvm import llvm_is_on_path
if not llvm_is_on_path():
    py.test.skip("llvm not found")

from pypy.translator.llvm.pyllvm.build import pyllvm
from pypy.translator.llvm.pyllvm.test import ll_snippet

#XXX When running this with py.test a segfault occurs instead of a nice traceback.
#    I don't know currently (and don't care either because I intend to switch to ctypes anyway)
#    What I do in this case is find out the failing test (py.test -v) and run that one on
#    its own with "py.test -k <testcase>". Have fun!

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
    py.test.raises(Exception, ee.functions, 1)
    py.test.raises(Exception, ee.functions, "string")

def test_call_parse_once():
    ee = get_fresh_ee()
    ee.parse(codepath.join("hello.s").read())
    assert ee.call("hello") == 0
    assert ee.call("gethellostr") == "hello world\n"
    py.test.raises(Exception, ee.call)
    py.test.raises(Exception, ee.call, 1)
    py.test.raises(Exception, ee.call, "gethellostrx")
    py.test.raises(Exception, ee.call, "gethellostrx", 1)
    py.test.raises(Exception, ee.call, "gethellostr", 1)

def test_call_parse_twice():
    ee = get_fresh_ee()
    ee.parse(codepath.join("hello.s").read())
    assert ee.call("gethellostr") == "hello world\n"
    ee.parse(codepath.join("addnumbers.s").read())
    assert ee.call("add", 10, 32) == 42
    assert ee.call("gethellostr") == "hello world\n"
    py.test.raises(Exception, ee.parse)
    py.test.raises(Exception, ee.parse, 1)
    py.test.raises(Exception, ee.parse, "abc")

def test_call_between_parsed_code():
    """we parse add1 last on purpose to see if the JIT resolves
    the function at execution time. Not sure if we really need this
    particular feature. It appears that 'calc' requires a forward
    declaration to add1 otherwise a segfault will occur!"""
    ee = get_fresh_ee()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    assert ee.call("add1", 41) == 42
    assert ee.call("calc", 122) == 123

def test_replace_function():
    """similar to test_call_between_parsed_code with additional complexity
    because we rebind the add1 function to another version after it the
    first version already has been used."""
    py.test.skip("function replacement support in progress")
    ee = get_fresh_ee()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    assert ee.call("add1", 41) == 42
    assert ee.call("calc", 122) == 123
    ee.parse(ll_snippet.add1_version2, "add1")
    assert ee.call("add1", 42) == 142
    assert ee.call("calc", 142) == 242

def test_share_data_between_parsed_code():
    ee = get_fresh_ee()
    ee.parse(ll_snippet.global_int_a_is_100)
    ee.parse(ll_snippet.add1_to_global_int_a)
    ee.parse(ll_snippet.sub10_from_global_int_a)
    assert ee.call("add1_to_global_int_a") == 101
    assert ee.call("sub10_from_global_int_a") == 91
    assert ee.call("add1_to_global_int_a") == 92
    assert ee.call("sub10_from_global_int_a") == 82

def TODOtest_native_code(): #examine JIT generate native (assembly) code
    pass

def TODOtest_delete_function():
    pass

def TODOtest_add_to_function():
    pass

def TODOtest_optimize_functions(): #add/del/list llvm transformation passes
    pass
