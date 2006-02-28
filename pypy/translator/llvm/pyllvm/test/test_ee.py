from pypy.translator.llvm.buildllvm import llvm_is_on_path
if not llvm_is_on_path():
    py.test.skip("llvm not found")

from pypy.translator.llvm.pyllvm import pyllvm 

def test_execution_context():
    code = open("hello.s").read()
    pyllvm.start_ee("modname", code)
