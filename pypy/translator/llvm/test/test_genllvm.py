import autopath
import py

import StringIO

from pypy.translator.translator import Translator
from pypy.translator.llvm.genllvm import LLVMGenerator
from pypy.translator.llvm.test import llvmsnippet
from pypy.translator.test import snippet as test
from pypy.objspace.flow.model import Constant, Variable

def setup_module(mod): 
    mod.llvm_found = is_on_path("llvm-as")

def compile_function(function, annotate):
    t = Translator(function)
    a = t.annotate(annotate)
    a.simplify()
    gen = LLVMGenerator(t)
    return gen.compile(True)

def is_on_path(name):
    try:
        py.path.local.sysfind(name) 
    except py.error.ENOENT: 
        return False 
    else: 
        return True


class TestLLVMRepr(object):
    def setup_method(self,method):
        if not llvm_found:
            py.test.skip("llvm-as not found on path")

    def DONOT_test_simple1(self):
        t = Translator(llvmsnippet.simple1)
        a = t.annotate([])
        gen = LLVMGenerator(t)
        l_repr = gen.get_repr(t.getflowgraph().startblock.exits[0].args[0])
        assert l_repr.llvmname() == "1"
        assert l_repr.typed_name() == "int 1"
        print gen.l_entrypoint.get_functions()
        assert gen.l_entrypoint.get_functions() == """\
int %simple1() {
block0:
\tbr label %block1
block1:
\t%v0 = phi int [1, %block0]
\tret int %v0
}

"""

    def test_simple2(self):
        t = Translator(llvmsnippet.simple2)
        a = t.annotate([])
        gen = LLVMGenerator(t)
        print gen
        print t.getflowgraph().startblock.exits[0].args[0]
        l_repr = gen.get_repr(t.getflowgraph().startblock.exits[0].args[0])
        assert l_repr.llvmname() == "false"
        assert l_repr.typed_name() == "bool false"

    def DONOT_test_typerepr(self):
        t = Translator(llvmsnippet.simple1)
        a = t.annotate([])
        gen = LLVMGenerator(t)
        l_repr = gen.get_repr(str)
        assert l_repr.llvmname() == "%std.string*"

    def DONOT_test_stringrepr(self):
        t = Translator(llvmsnippet.simple3)
        a = t.annotate([])
        gen = LLVMGenerator(t)
        l_repr1 = gen.get_repr(t.getflowgraph().startblock.exits[0].args[0])
        l_repr2 = gen.get_repr(t.getflowgraph().startblock.exits[0].args[0])
        assert l_repr1 is l_repr2
        assert l_repr1.typed_name() == "%std.string* %glb.StringRepr.2"
        assert l_repr2.get_globals() == """%glb.StringRepr.1 = \
internal constant [13 x sbyte] c"Hello, Stars!"
%glb.StringRepr.2 = internal constant %std.string {uint 13,\
sbyte* getelementptr ([13 x sbyte]* %glb.StringRepr.1, uint 0, uint 0)}"""

class TestGenLLVM(object):
    def setup_method(self,method):
        if not llvm_found:
            py.test.skip("llvm-as not found on path")

    def test_simple1(self):
        f = compile_function(llvmsnippet.simple1, [])
        assert f() == 1

    def test_simple2(self):
        f = compile_function(llvmsnippet.simple2, [])
        assert f() == 0

    def test_simple4(self):
        f = compile_function(llvmsnippet.simple4, [])
        assert f() == 4

    def test_simple5(self):
        f = compile_function(llvmsnippet.simple5, [int])
        assert f(1) == 12
        assert f(0) == 13

    def test_ackermann(self):
        f = compile_function(llvmsnippet.ackermann, [int, int])
        for i in range(10):
            assert f(0, i) == i + 1
            assert f(1, i) == i + 2
            assert f(2, i) == 2 * i + 3
            assert f(3, i) == 2 ** (i + 3) - 3

    def test_calling(self):
        f = compile_function(llvmsnippet.calling1, [int])
        assert f(10) == 1

class TestLLVMArray(object):
    def setup_method(self, method):
        if not llvm_found:
            py.test.skip("llvm-as not found on path.")

    def test_array(self):
        f = compile_function(llvmsnippet.array_simple, [])
        assert f() == 42

    def test_array1(self):
        f = compile_function(llvmsnippet.array_simple1, [int])
        assert f(1) == 10
        assert f(-42) == -420

    def test_array_setitem(self):
        f = compile_function(llvmsnippet.array_setitem, [int])
        print f(1), f(2), f(3)
        assert f(1) == 12
        assert f(2) == 13
        assert f(3) == 3

    def test_array_add(self):
        f = compile_function(llvmsnippet.array_add, [int, int, int, int, int])
        assert f(1,2,3,4,0) == 1
        assert f(1,2,3,4,1) == 2
        assert f(1,2,3,4,2) == 3
        assert f(1,2,5,6,3) == 6

    def test_array_double(self):
        f = compile_function(llvmsnippet.double_array, [])
        assert f() == 15

    def test_bool_array(self):
        f = compile_function(llvmsnippet.bool_array, [])
        assert f() == 1

    def test_array_arg(self):
        f = compile_function(llvmsnippet.array_arg, [int])
        assert f(5) == 0

    def test_array_len(self):
        f = compile_function(llvmsnippet.array_len, [])
        assert f() == 10

    def test_array_append(self):
        f = compile_function(llvmsnippet.array_append, [int])
        for i in range(3):
            assert f(i) == 0
        assert f(3) == 10

    def test_array_reverse(self):
        f = compile_function(llvmsnippet.array_reverse, [int])
        assert f(0) == 1
        assert f(1) == 0

    def test_range(self):
        f = compile_function(llvmsnippet.rangetest, [int])
        for i in range(10):
            assert f(i) == i

    def test_array_pop(i):
        f = compile_function(llvmsnippet.array_pop, [int])
        assert f(0) == 5
        assert f(1) == 6
        assert f(2) == 7

class TestClass(object):
    def setup_method(self, method):
        if not llvm_found:
            py.test.skip("llvm-as not found on path.")

    def test_classsimple(self):
        f = compile_function(llvmsnippet.class_simple, [])
        assert f() == 14

    def test_classsimple1(self):
        f = compile_function(llvmsnippet.class_simple1, [int])
        assert f(2) == 10

    def test_id_int(self):
        f = compile_function(llvmsnippet.id_int, [int])
        for i in range(1, 20):
            assert f(i) == i

    def test_classsimple2(self):
        f = compile_function(llvmsnippet.class_simple2, [int])
        assert f(2) == 10

    def test_method_of_base_class(self):
        f = compile_function(llvmsnippet.method_of_base_class, [])
        assert f() == 14

    def test_attribute_from_base_class(self):
        f = compile_function(llvmsnippet.attribute_from_base_class, [])
        assert f() == 4

    def test_direct_call_of_virtual_method(self):
        f = compile_function(llvmsnippet.direct_call_of_virtual_method, [])
        assert f() == 14

    def test_flow_type(self):
        f = compile_function(llvmsnippet.flow_type, [])
        assert f() == 16

    def test_merge_class(self):
        f = compile_function(llvmsnippet.merge_classes, [bool])
        assert f(True) == 1
        assert f(False) == 2
    
class TestString(object):
    def setup_method(self, method):
        if not llvm_found:
            py.test.skip("llvm-as not found on path.")

    def test_f2(self):
        f = compile_function(llvmsnippet.string_f2, [int, int])
        assert chr(f(1, 0)) == "a"

class TestTuple(object):
    def setup_method(self, method):
        if not llvm_found:
            py.test.skip("llvm-as not found on path.")

    def test_f1(self):
        f = compile_function(llvmsnippet.tuple_f1, [int])
        assert f(10) == 10
        assert f(15) == 15

    def test_f3(self):
        f = compile_function(llvmsnippet.tuple_f3, [int])
        assert f(10) == 10
        assert f(15) == 15
        assert f(30) == 30

class TestException(object):
    def test_two_exception(self):
        f = compile_function(llvmsnippet.two_exceptions, [int])
        for i in range(10):
            assert f(i) == 4
        for i in range(10, 20):
            assert f(i) == 2

    def test_catch_base_exception(self):
        f = compile_function(llvmsnippet.catch_base_exception, [int])
        for i in range(10):
            assert f(i) == 4
        for i in range(10, 20):
            assert f(i) == 2


class TestSnippet(object):
    def setup_method(self, method):
        if not llvm_found:
            py.test.skip("llvm-as not found on path.")
        
    def test_if_then_else(self):
        f = compile_function(test.if_then_else, [int, int, int])
        assert f(0, 12, 13) == 13
        assert f(13, 12, 13) == 12
        
    def test_my_gcd(self):
        f = compile_function(test.my_gcd, [int, int])
        assert f(15, 5) == 5
        assert f(18, 42) == 6

    def test_is_perfect_number(self):
        f = compile_function(test.is_perfect_number, [int])
        assert f(28) == 1
        assert f(123) == 0
        assert f(496) == 1

    def test_my_bool(self):
        f = compile_function(test.my_bool, [int])
        assert f(10) == 1
        assert f(1) == 1
        assert f(0) == 0

    def test_two_plus_two(self):
        f = compile_function(test.two_plus_two, [])
        assert f() == 4

    def test_sieve_of_eratosthenes(self):
        f = compile_function(test.sieve_of_eratosthenes, [])
        assert f() == 1028

    def test_simple_func(self):
        f = compile_function(test.simple_func, [int])
        assert f(1027) == 1028
        
    def test_while_func(self):
        while_func = compile_function(test.while_func, [int])
        assert while_func(10) == 55

    def test_time_waster(self):
        f = compile_function(test.time_waster, [int])
        assert f(1) == 1
        assert f(2) == 2
        assert f(3) == 6
        assert f(4) == 12

    def test_int_id(self):
        f = compile_function(test.int_id, [int])
        assert f(1027) == 1027

    def test_factorial2(self):
        factorial2 = compile_function(test.factorial2, [int])
        assert factorial2(5) == 120

    def test_factorial(self):
        factorial = compile_function(test.factorial, [int])
        assert factorial(5) == 120

    def test_set_attr(self):
        set_attr = compile_function(test.set_attr, [])
        assert set_attr() == 2

    def test_merge_setattr(self):
        merge_setattr = compile_function(test.merge_setattr, [bool])
        assert merge_setattr(1) == 1

    def test_simple_method(self):
        simple_method = compile_function(test.simple_method, [int])
        assert simple_method(65) == 65

    def test_with_init(self):
        with_init = compile_function(test.with_init, [int])
        assert with_init(42) == 42

    def DONOT_test_with_more_init(self):
        with_more_init = compile_function(test.with_more_init, [int, bool])
        assert with_more_init(42, True) == 42
        assert with_more_init(42, False) == -42
