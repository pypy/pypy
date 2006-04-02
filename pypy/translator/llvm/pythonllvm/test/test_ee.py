import py
from pypy.translator.llvm.buildllvm import llvm_is_on_path
if not llvm_is_on_path():
    py.test.skip("llvm not found")

from pypy.translator.llvm.pythonllvm import pyllvm
from pypy.translator.llvm.pythonllvm.test import ll_snippet

py.test.skip("WIP")

def test_execution_engine():
    ee = pyllvm.ExecutionEngine()
    ee = pyllvm.ExecutionEngine()
    ee = pyllvm.ExecutionEngine()
    del ee  #XXX not actualy deleted at the moment!!!
    ee2 = pyllvm.ExecutionEngine()
    ee2 = pyllvm.ExecutionEngine()
    ee2 = pyllvm.ExecutionEngine()

codepath = py.path.local(__file__).dirpath()

def test_load():
    ee = pyllvm.ExecutionEngine()
    ee.parse(codepath.join("hello.s").read())
    ee.parse(codepath.join("addnumbers.s").read())

def test_functions():
    ee = pyllvm.ExecutionEngine()
    ee.parse(codepath.join("hello.s").read())
    assert ee.n_functions() == 2
    #TODO
    #for function in functions:
    #    returnId, name, args = function
    #    assert len(function) == 3
    #    assert returnId > 0
    #    assert name in ('gethellostr', 'hello')
    #    assert len(args) == 0
    py.test.raises(Exception, ee.n_functions, 1)
    py.test.raises(Exception, ee.n_functions, "string")

def test_call_parse_once():
    ee = pyllvm.ExecutionEngine()
    ee.parse(codepath.join("hello.s").read())
    assert ee.call("hello") == 0
    assert ee.call("gethellostr") == "hello world\n"
    py.test.raises(Exception, ee.call)
    py.test.raises(Exception, ee.call, 1)
    py.test.raises(Exception, ee.call, "gethellostrx")
    py.test.raises(Exception, ee.call, "gethellostrx", 1)
    py.test.raises(Exception, ee.call, "gethellostr", 1)

def test_call_parse_twice():
    ee = pyllvm.ExecutionEngine()
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
    ee = pyllvm.ExecutionEngine()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    assert ee.call("add1", 41) == 42
    assert ee.call("calc", 122) == 123

def test_replace_function():
    """similar to test_call_between_parsed_code with additional complexity
    because we rebind the add1 function to another version after it the
    first version already has been used."""
    ee = pyllvm.ExecutionEngine()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    assert ee.call("add1", 41) == 42
    assert ee.call("calc", 122) == 123 #XXX need recompileAndRelinkFunction somewhere
    ee.parse(ll_snippet.add1_version2, "add1")
    assert ee.call("add1", 42) == 142
    assert ee.call("calc", 142) == 242

def test_share_data_between_parsed_code():
    ee = pyllvm.ExecutionEngine()
    ee.parse(ll_snippet.global_int_a_is_100)
    ee.parse(ll_snippet.add1_to_global_int_a)
    ee.parse(ll_snippet.sub10_from_global_int_a)
    assert ee.call("add1_to_global_int_a") == 101
    assert ee.call("sub10_from_global_int_a") == 91
    assert ee.call("add1_to_global_int_a") == 92
    assert ee.call("sub10_from_global_int_a") == 82

def test_native_code(): #examine JIT generate native (assembly) code
    pyllvm.toggle_print_machineinstrs()
    ee = pyllvm.ExecutionEngine()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    assert ee.call("calc", 41) == 42
    pyllvm.toggle_print_machineinstrs()

def test_delete_function(): #this will only work if nothing uses Fn of course!
    ee = pyllvm.ExecutionEngine()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    assert ee.n_functions() == 2

    ee.delete("calc")
    assert ee.n_functions() == 1
    assert ee.call("add1", 41) == 42

    ee.delete("add1")
    assert ee.n_functions() == 0

    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    assert ee.call("calc", 100) == 101

def TODOtest_add_to_function():
    pass

def TODOtest_optimize_functions(): #add/del/list llvm transformation passes
    pass
