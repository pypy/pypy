from pypy.translator.llvm.buildllvm import llvm_is_on_path
if not llvm_is_on_path():
    py.test.skip("llvm not found")
import py
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
    ee.functions()

def test_call1():
    ee = get_fresh_ee()
    ee.parse(codepath.join("hello.s").read())
    ee.call_noargs("hello")
    ee.call_noargs("gethellostr")
    try:
        ee.call_noargs("gethellostrx")
    except:
        pass
