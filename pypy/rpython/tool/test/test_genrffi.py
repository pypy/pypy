
import ctypes
from pypy.rpython.tool.genrffi import *
from pypy.rpython.tool.test.test_c import TestBasic
import py

class random_structure(ctypes.Structure):
    _fields_ = [('one', ctypes.c_int),
                ('two', ctypes.POINTER(ctypes.c_int))]

def test_proc_tp_simple():
    builder = RffiBuilder()
    assert builder.proc_tp(ctypes.c_int) == rffi.INT
    assert builder.proc_tp(ctypes.c_void_p) == rffi.VOIDP

def test_proc_tp_complicated():
    builder = RffiBuilder()    
    assert builder.proc_tp(ctypes.POINTER(ctypes.c_uint)) == \
           lltype.Ptr(lltype.Array(rffi.UINT, hints={'nolength': True}))
    ll_item = lltype.Struct('random_structure', ('one', rffi.INT), ('two', lltype.Ptr(lltype.Array(rffi.INT, hints={'nolength': True}))),  hints={'external':'C'})
    assert builder.proc_tp(random_structure) == ll_item

class TestMkrffi(TestBasic):
    def test_single_func(self):
        func = self.lib.int_to_void_p
        func.argtypes = [ctypes.c_int]
        func.restype = ctypes.c_voidp

        builder = RffiBuilder()
        ll_item = builder.proc_func(func)
        int_to_void_p = rffi.llexternal('int_to_void_p', [rffi.INT], rffi.VOIDP, )
        # XXX hmm, need a deep __eq__ for lowlevel types..
        assert str(ll_item) == str(int_to_void_p)

    def test_struct_return(self):
        func = self.lib.int_int_to_struct_p
        func.argtypes = [ctypes.c_int, ctypes.c_int]
        func.restype = ctypes.POINTER(random_structure)
        builder = RffiBuilder()
        ll_item = builder.proc_func(func)
        assert 'random_structure' in builder.ns

        ll_struct = lltype.Struct('random_structure', 
            ('one', rffi.INT), 
            ('two', lltype.Ptr(lltype.Array(rffi.INT, hints={'nolength': True}))),  
            hints={'external':'C'})

        int_int_to_struct_p = rffi.llexternal('int_int_to_struct_p', 
            [rffi.INT, rffi.INT], lltype.Ptr(ll_struct))
        
        #print dir( ll_item._TYPE)
        #assert ll_item == int_int_to_struct_p # ??



