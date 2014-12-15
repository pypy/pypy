
import py
import sys
from rpython.rtyper.lltypesystem.rffi import *
from rpython.rtyper.lltypesystem.rffi import _keeper_for_type # crap
from rpython.rlib.rposix import get_errno, set_errno
from rpython.translator.c.test.test_genc import compile as compile_c
from rpython.rtyper.lltypesystem.lltype import Signed, Ptr, Char, malloc
from rpython.rtyper.lltypesystem import lltype
from rpython.translator import cdir
from rpython.tool.udir import udir
from rpython.rtyper.test.test_llinterp import interpret
from rpython.annotator.annrpython import RPythonAnnotator
from rpython.rtyper.rtyper import RPythonTyper
from rpython.translator.backendopt.all import backend_optimizations
from rpython.translator.translator import graphof
from rpython.conftest import option
from rpython.flowspace.model import summary
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.rarithmetic import r_singlefloat

"""
def test_string():
    eci = ExternalCompilationInfo(includes=['string.h'])
    z = llexternal('strlen', [CCHARP], Signed, compilation_info=eci)

    def f():
        s = str2charp("xxx")
        res = z(s)
        free_charp(s)
        return res

    xf = compile_c(f, [], backendopt=False)
    assert xf() == 3
"""

from rpython.jit.backend.libgccjit.rffi_bindings import make_eci, Library

def test_compile_empty_context():
    eci = make_eci()

    lib = Library(eci)

    def f():
        ctxt = lib.gcc_jit_context_acquire()
        result = lib.gcc_jit_context_compile(ctxt)
        lib.gcc_jit_context_release(ctxt)
        lib.gcc_jit_result_release(result)
        
    f1 = compile_c(f, [], backendopt=False)
    f1 ()
    #assert False # to see stderr

def make_param_array(lib, l):
    array = lltype.malloc(lib.PARAM_P_P.TO,
                          len(l),
                          flavor='raw') # of maybe gc?
    for i in range(len(l)):
        array[i] = l[i]
    return array
    # FIXME: don't leak!
    
def test_compile_add_one_to():
    eci = make_eci()

    lib = Library(eci)

    ft = lltype.FuncType([INT], INT)#, abi="C")
    ftp = lltype.Ptr(ft)

    def f():
        ctxt = lib.gcc_jit_context_acquire()

        lib.gcc_jit_context_set_bool_option(ctxt,
                                            lib.GCC_JIT_BOOL_OPTION_DUMP_INITIAL_GIMPLE,
                                            1)
        lib.gcc_jit_context_set_int_option(ctxt,
                                           lib.GCC_JIT_INT_OPTION_OPTIMIZATION_LEVEL,
                                           3)
        lib.gcc_jit_context_set_bool_option(ctxt,
                                            lib.GCC_JIT_BOOL_OPTION_KEEP_INTERMEDIATES,
                                            1)
        lib.gcc_jit_context_set_bool_option(ctxt,
                                            lib.GCC_JIT_BOOL_OPTION_DUMP_EVERYTHING,
                                            1)
        lib.gcc_jit_context_set_bool_option(ctxt,
                                            lib.GCC_JIT_BOOL_OPTION_DUMP_GENERATED_CODE,
                                            1)
        t_int = lib.gcc_jit_context_get_type(ctxt, lib.GCC_JIT_TYPE_INT)
        param = lib.gcc_jit_context_new_param(ctxt,
                                              lib.null_location_ptr,
                                              t_int,
                                              "input")
        # FIXME: how to build an array of params at this level?
        # see liststr2charpp in rffi.py
        
        param_array = make_param_array(lib, [param])
        fn = lib.gcc_jit_context_new_function(ctxt,
                                              lib.null_location_ptr,
                                              lib.GCC_JIT_FUNCTION_EXPORTED,
                                              t_int,
                                              "add_one_to",
                                              1, param_array, 0)
        lltype.free(param_array, flavor='raw')

        v_res = lib.gcc_jit_function_new_local(fn,
                                               lib.null_location_ptr,
                                               t_int,
                                               "v_res")
        b_initial = lib.gcc_jit_function_new_block(fn, "initial")
        c_one = lib.gcc_jit_context_new_rvalue_from_int(ctxt, t_int, 1)
        op_add = lib.gcc_jit_context_new_binary_op(ctxt,
                                                   lib.null_location_ptr,
                                                   lib.GCC_JIT_BINARY_OP_PLUS,
                                                   t_int,
                                                   lib.gcc_jit_param_as_rvalue(param),
                                                   c_one)
        lib.gcc_jit_block_add_assignment(b_initial, lib.null_location_ptr,
                                         v_res,
                                         op_add)
        lib.gcc_jit_block_end_with_return(b_initial, lib.null_location_ptr,
                                          lib.gcc_jit_lvalue_as_rvalue(v_res))

        jit_result = lib.gcc_jit_context_compile(ctxt)
        lib.gcc_jit_context_release(ctxt)
        if not jit_result:
            # FIXME: get error from context
            raise Exception("jit_result is NULL")

        fn_ptr = lib.gcc_jit_result_get_code(jit_result, "add_one_to")
        if not fn_ptr:
            raise Exception("fn_ptr is NULL")
        print('fn_ptr: %s' % fn_ptr)

        #ft = lltype.FuncType([INT], INT)#, abi="C")
        # looks like we can't build a FuncType inside RPython
        # but we can use one built outside:
        print(ft)
        print(ftp)

        typed_fn_ptr = cast(ftp, fn_ptr)
        print(typed_fn_ptr)
        fn_result = typed_fn_ptr (r_int(41))
        #print('fn_result: %d' % fn_result)
        #assert fn_result == r_int(42)

        # and it looks like we can't create a functionptr from this
        # FuncType:
        #funcptr = lltype.functionptr(ft)

        lib.gcc_jit_result_release(jit_result)

        return int(fn_result)
        
    f1 = compile_c(f, [], backendopt=False)
    assert f1() == 42
    #assert False # to see stderr
    
# TODO: test of an error
# should turn it into an exception, and capture the error
