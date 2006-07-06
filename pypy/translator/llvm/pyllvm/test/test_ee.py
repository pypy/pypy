import py
from pypy.translator.llvm.buildllvm import llvm_is_on_path
#if not llvm_is_on_path():
#    py.test.skip("llvm not found")
#py.test.skip('aborts with SIGIOT on the snake machine :-(')

try:
    from pypy.translator.llvm.pyllvm import pyllvm
except:
    py.test.skip("Unable to import pyllvm")

from pypy.translator.llvm.pyllvm.test import ll_snippet

ee = None
def make_execution_engine():
    global ee
    if ee is None:
        ee = pyllvm.ExecutionEngine()
    mod = ee.getModule()
    assert mod.n_functions() == 0

def test_execution_engine_singleton():
    make_execution_engine()
    py.test.raises(AssertionError, pyllvm.ExecutionEngine)

codepath = py.path.local(__file__).dirpath()

def test_load():
    make_execution_engine()
    ee.parse(codepath.join("hello.ll").read())
    ee.parse(codepath.join("addnumbers.ll").read()) # why does this work ?
    ee.delete("hello")
    ee.delete("gethellostr")
    ee.delete("add")
    mod = ee.getModule()
    assert mod.n_functions() == 0

def test_functions():
    make_execution_engine()
    ee.parse(codepath.join("hello.ll").read())
    mod = ee.getModule()
    assert mod.n_functions() == 2
    #TODO
    #for function in functions:
    #    returnId, name, args = function
    #    assert len(function) == 3
    #    assert returnId > 0
    #    assert name in ('gethellostr', 'hello')
    #    assert len(args) == 0
    py.test.raises(Exception, mod.n_functions, 1)
    py.test.raises(Exception, mod.n_functions, "string")
    ee.delete("hello")
    ee.delete("gethellostr")
    assert mod.n_functions() == 0

def test_call_parse_once():
    make_execution_engine()
    mod = ee.getModule()
    assert mod.n_functions() == 0
    ee.parse(codepath.join("hello.ll").read())
    f = ee.getModule().getNamedFunction
    hello = f("hello")
    gethellostr = f("gethellostr")
    assert hello() == 0
    assert gethellostr() == "hello world\n"
    ee.delete("hello")
    ee.delete("gethellostr")
    assert mod.n_functions() == 0

def test_call_parse_twice():
    py.test.skip("WIP")
    make_execution_engine()
    mod = ee.getModule()
    ee.parse(codepath.join("hello.ll").read())
    f = ee.getModule().getNamedFunction
    f1 = f("gethellostr")
    assert f1() == "hello world\n"
    ee.parse(codepath.join("addnumbers.ll").read()) # blows here
    f2 = f("add")
    assert f2(10, 32) == 42
    assert f1() == "hello world\n"
    py.test.raises(Exception, ee.parse)
    py.test.raises(Exception, ee.parse, 1)
    py.test.raises(Exception, ee.parse, "abc")
    ee.delete("hello")
    ee.delete("gethellostr")
    ee.delete("add")
    assert mod.n_functions() == 0

def test_call_between_parsed_code():
    """we parse add1 last on purpose to see if the JIT resolves
    the function at execution time. Not sure if we really need this
    particular feature. It appears that 'calc' requires a forward
    declaration to add1 otherwise a segfault will occur!"""
    make_execution_engine()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    f = ee.getModule().getNamedFunction
    assert f("add1")(41) == 42
    assert f("calc")(122) == 123
    ee.delete("calc")
    ee.delete("add1")
    mod = ee.getModule()
    assert mod.n_functions() == 0

def test_replace_function():
    py.test.skip("WIP")
    """similar to test_call_between_parsed_code with additional complexity
    because we rebind the add1 function to another version after it the
    first version already has been used."""
    make_execution_engine()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    f = ee.getModule().getNamedFunction
    assert f("add1")(41) == 42
    assert f("calc")(122) == 123 #XXX need recompileAndRelinkFunction somewhere
    ee.parse(ll_snippet.add1_version2, "add1")
    assert f("add1")(42) == 142
    assert f("calc")(142) == 242
    ee.delete("calc")
    ee.delete("add1")
    mod = ee.getModule()
    assert mod.n_functions() == 0

def test_share_data_between_parsed_code():
    make_execution_engine()
    ee.parse(ll_snippet.global_int_a_is_100)
    ee.parse(ll_snippet.add1_to_global_int_a)
    ee.parse(ll_snippet.sub10_from_global_int_a)
    f = ee.getModule().getNamedFunction
    assert f("add1_to_global_int_a")() == 101
    assert f("sub10_from_global_int_a")() == 91
    assert f("add1_to_global_int_a")() == 92
    assert f("sub10_from_global_int_a")() == 82
    ee.delete("add1_to_global_int_a")
    ee.delete("sub10_from_global_int_a")
    mod = ee.getModule()
    assert mod.n_functions() == 0

def test_native_code(): #examine JIT generate native (assembly) code
#    py.test.skip("WIP")
    pyllvm.toggle_print_machineinstrs()
    make_execution_engine()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    f = ee.getModule().getNamedFunction
    assert f("calc")(41) == 42
    pyllvm.toggle_print_machineinstrs()
    ee.delete("calc")
    ee.delete("add1")
    mod = ee.getModule()
    assert mod.n_functions() == 0

def test_delete_function(): #this will only work if nothing uses Fn of course!
    make_execution_engine()
    mod = ee.getModule()
    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    assert mod.n_functions() == 2

    ee.delete("calc")
    assert mod.n_functions() == 1
    f = ee.getModule().getNamedFunction
    assert f("add1")(41) == 42

    ee.delete("add1")
    assert mod.n_functions() == 0

    ee.parse(ll_snippet.calc)
    ee.parse(ll_snippet.add1)
    assert f("calc")(100) == 101
    ee.delete("calc")
    ee.delete("add1")
    mod = ee.getModule()
    assert mod.n_functions() == 0

def TODOtest_multiple_executionengines():
    pass

def TODOtest_returntypes():
    pass

def TODOtest_paramtypes():
    pass

def TODOtest_add_to_function():
    pass

def TODOtest_optimize_functions(): #add/del/list llvm transformation passes
    pass
