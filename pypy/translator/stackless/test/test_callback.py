import py
from pypy.rlib import rstack
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.stackless.test.test_transform import \
     run_stackless_function

eci = ExternalCompilationInfo(
    separate_module_sources = ["""
        int f1(int (*callback)(int))
        {
            return callback(25) + 1;
        }
    """])

CALLBACK = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed))
f1 = rffi.llexternal("f1", [CALLBACK], lltype.Signed, compilation_info=eci)

def my_callback(n):
    try:
        rstack.stack_unwind()
    except RuntimeError:
        return -20
    return n * 10

def test_my_callback():
    def fn():
        return f1(my_callback)
    res = run_stackless_function(fn)
    assert res == -19
