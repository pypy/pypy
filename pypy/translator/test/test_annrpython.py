
import autopath
import py.test
from pypy.tool.udir import udir

from pypy.translator.annrpython import RPythonAnnotator, annmodel
from pypy.translator.translator import Translator
from pypy.objspace.flow.model import *

from pypy.translator.test import snippet

class TestAnnonateTestCase:
    objspacename = 'flow'

    def make_fun(self, func):
        import inspect
        try:
            func = func.im_func
        except AttributeError:
            pass
        name = func.func_name
        funcgraph = self.space.build_flow(func)
        funcgraph.source = inspect.getsource(func)
        return funcgraph

    def reallyshow(self, graph):
        import os
        from pypy.translator.tool.make_dot import make_dot
        dest = make_dot('b', graph)
        os.system('gv %s' % str(dest))

    def test_simple_func(self):
        """
        one test source:
        def f(x):
            return x+1
        """
        x = Variable("x")
        result = Variable("result")
        op = SpaceOperation("add", [x, Constant(1)], result)
        block = Block([x])
        fun = FunctionGraph("f", block)
        block.operations.append(op)
        block.closeblock(Link([result], fun.returnblock))
        a = RPythonAnnotator()
        a.build_types(fun, [int])
        assert a.gettype(fun.getreturnvar()) == int

    def test_while(self):
        """
        one test source:
        def f(i):
            while i > 0:
                i = i - 1
            return i
        """
        i = Variable("i")
        conditionres = Variable("conditionres")
        conditionop = SpaceOperation("gt", [i, Constant(0)], conditionres)
        decop = SpaceOperation("add", [i, Constant(-1)], i)
        headerblock = Block([i])
        whileblock = Block([i])

        fun = FunctionGraph("f", headerblock)
        headerblock.operations.append(conditionop)
        headerblock.exitswitch = conditionres
        headerblock.closeblock(Link([i], fun.returnblock, False),
                               Link([i], whileblock, True))
        whileblock.operations.append(decop)
        whileblock.closeblock(Link([i], headerblock))

        a = RPythonAnnotator()
        a.build_types(fun, [int])
        assert a.gettype(fun.getreturnvar()) == int

    def test_while_sum(self):
        """
        one test source:
        def f(i):
            sum = 0
            while i > 0:
                sum = sum + i
                i = i - 1
            return sum
        """
        i = Variable("i")
        sum = Variable("sum")

        conditionres = Variable("conditionres")
        conditionop = SpaceOperation("gt", [i, Constant(0)], conditionres)
        decop = SpaceOperation("add", [i, Constant(-1)], i)
        addop = SpaceOperation("add", [i, sum], sum)
        startblock = Block([i])
        headerblock = Block([i, sum])
        whileblock = Block([i, sum])

        fun = FunctionGraph("f", startblock)
        startblock.closeblock(Link([i, Constant(0)], headerblock))
        headerblock.operations.append(conditionop)
        headerblock.exitswitch = conditionres
        headerblock.closeblock(Link([sum], fun.returnblock, False),
                               Link([i, sum], whileblock, True))
        whileblock.operations.append(addop)
        whileblock.operations.append(decop)
        whileblock.closeblock(Link([i, sum], headerblock))

        a = RPythonAnnotator()
        a.build_types(fun, [int])
        assert a.gettype(fun.getreturnvar()) == int

    def test_f_calls_g(self):
        a = RPythonAnnotator()
        s = a.build_types(f_calls_g, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_lists(self):
        fun = self.make_fun(snippet.poor_man_rev_range)
        a = RPythonAnnotator()
        a.build_types(fun, [int])
        # result should be a list of integers
        assert a.gettype(fun.getreturnvar()) == list
        end_cell = a.binding(fun.getreturnvar())
        assert end_cell.s_item.knowntype == int

    def test_factorial(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.factorial, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_factorial2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.factorial2, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_build_instance(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.build_instance, [])
        # result should be a snippet.C instance
        assert s.knowntype == snippet.C

    def test_set_attr(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.set_attr, [])
        # result should be an integer
        assert s.knowntype == int

    def test_merge_setattr(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.merge_setattr, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_inheritance1(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.inheritance1, [])
        # result should be exactly:
        assert s == annmodel.SomeTuple([
                                a.bookkeeper.immutablevalue(()),
                                annmodel.SomeInteger()
                                ])

    def test_inheritance2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet._inheritance_nonrunnable, [])
        # result should be exactly:
        assert s == annmodel.SomeTuple([
                                annmodel.SomeInteger(),
                                annmodel.SomeObject()
                                ])

    def test_poor_man_range(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.poor_man_range, [int])
        # result should be a list of integers
        assert s.knowntype == list
        assert s.s_item.knowntype == int

    def test_methodcall1(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet._methodcall1, [int])
        # result should be a tuple of (C, positive_int)
        assert s.knowntype == tuple
        assert len(s.items) == 2
        assert s.items[0].knowntype == snippet.C
        assert s.items[1].knowntype == int
        assert s.items[1].nonneg == True

    def test_classes_methodcall1(self):
        a = RPythonAnnotator()
        a.build_types(snippet._methodcall1, [int])
        # the user classes should have the following attributes:
        classes = a.bookkeeper.userclasses
        assert classes[snippet.F].attrs.keys() == ['m']
        assert classes[snippet.G].attrs.keys() == ['m2']
        assert classes[snippet.H].attrs.keys() == ['attr'] 
        assert classes[snippet.H].about_attribute('attr') == (
                          a.bookkeeper.immutablevalue(1))

    def DISABLED_test_knownkeysdict(self):
        # disabled, SomeDict() is now a general {s_key: s_value} dict
        a = RPythonAnnotator()
        s = a.build_types(snippet.knownkeysdict, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_generaldict(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.generaldict, [str, int, str, int])
        # result should be an integer
        assert s.knowntype == int

    def test_somebug1(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet._somebug1, [int])
        # result should be a built-in method
        assert isinstance(s, annmodel.SomeBuiltin)

    def test_with_init(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.with_init, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_with_more_init(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.with_more_init, [int, bool])
        # the user classes should have the following attributes:
        classes = a.bookkeeper.userclasses
        # XXX on which class should the attribute 'a' appear?  We only
        #     ever flow WithInit.__init__ with a self which is an instance
        #     of WithMoreInit, so currently it appears on WithMoreInit.
        assert classes[snippet.WithMoreInit].about_attribute('a') == (
                          annmodel.SomeInteger())
        assert classes[snippet.WithMoreInit].about_attribute('b') == (
                          annmodel.SomeBool())

    def test_global_instance(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.global_instance, [])
        # currently this returns the constant 42.
        # XXX not sure this is the best behavior...
        assert s == a.bookkeeper.immutablevalue(42)

    def test_call_five(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.call_five, [])
        # returns should be a list of constants (= 5)
        assert isinstance(s, annmodel.SomeList)
        assert s.s_item == a.bookkeeper.immutablevalue(5)

    def test_call_five_six(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.call_five_six, [])
        # returns should be a list of positive integers
        assert isinstance(s, annmodel.SomeList)
        assert s.s_item == annmodel.SomeInteger(nonneg=True)

    def test_constant_result(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.constant_result, [])
        #a.translator.simplify()
        # must return "yadda"
        assert s == a.bookkeeper.immutablevalue("yadda")
        keys = a.translator.flowgraphs.keys()
        keys.sort()
        expected = [snippet.constant_result,
                    snippet.forty_two,
                    # and not snippet.never_called
                    ]
        expected.sort()
        assert keys == expected
        a.simplify()
        #a.translator.view()

    def test_call_pbc(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.call_cpbc, [])
        assert s == a.bookkeeper.immutablevalue(42)

    def test_flow_type_info(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_type_info, [object])
        a.translator.simplify()
        a.simplify()
        #a.translator.view()
        assert s.knowntype == int

    def test_flow_type_info_2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_type_info,
                          [annmodel.SomeInteger(nonneg=True)])
        # this checks that isinstance(i, int) didn't loose the
        # actually more precise information that i is non-negative
        assert s == annmodel.SomeInteger(nonneg=True)

    def test_flow_usertype_info(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_usertype_info, [object])
        #a.translator.view()
        assert s.knowntype == snippet.WithInit

    def test_flow_usertype_info2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_usertype_info, [snippet.WithMoreInit])
        #a.translator.view()
        assert s.knowntype == snippet.WithMoreInit

    def test_flow_identity_info(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_identity_info, [object, object])
        a.translator.simplify()
        a.simplify()
        #a.translator.view()
        assert s == a.bookkeeper.immutablevalue((None, None))

    def test_mergefunctions(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.mergefunctions, [int])
        # the test is mostly that the above line hasn't blown up
        # but let's at least check *something*
        assert isinstance(s, annmodel.SomePBC)

    def test_func_calls_func_which_just_raises(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.funccallsex, [])
        # the test is mostly that the above line hasn't blown up
        # but let's at least check *something*
        #self.assert_(isinstance(s, SomeCallable))

    def test_tuple_unpack_from_const_tuple_with_different_types(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.func_arg_unpack, [])
        assert isinstance(s, annmodel.SomeInteger) 
        assert s.const == 3 

    def test_pbc_attr_preserved_on_instance(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.preserve_pbc_attr_on_instance, [bool])
        #a.simplify()
        #a.translator.view()
        assert s == annmodel.SomeInteger(nonneg=True) 
        #self.assertEquals(s.__class__, annmodel.SomeInteger) 

    def test_is_and_knowntype_data(self): 
        a = RPythonAnnotator()
        s = a.build_types(snippet.is_and_knowntype, [bool])
        #a.simplify()
        #a.translator.view()
        assert s == a.bookkeeper.immutablevalue(None)

    def test_isinstance_and_knowntype_data(self): 
        a = RPythonAnnotator()
        x = annmodel.SomePBC({snippet.apbc: True}) 
        s = a.build_types(snippet.isinstance_and_knowntype, [x]) 
        #a.simplify()
        #a.translator.view()
        assert s == x

    def test_somepbc_simplify(self):
        a = RPythonAnnotator()
        # this example used to trigger an AssertionError
        a.build_types(snippet.somepbc_simplify, [])

    def test_builtin_methods(self):
        a = RPythonAnnotator()
        iv = a.bookkeeper.immutablevalue
        # this checks that some built-in methods are really supported by
        # the annotator (it doesn't check that they operate property, though)
        for example, methname, s_example in [
            ('', 'join',    annmodel.SomeString()),
            ([], 'append',  annmodel.SomeList({})),
            ([], 'reverse', annmodel.SomeList({})),
            ([], 'insert',  annmodel.SomeList({})),
            ([], 'pop',     annmodel.SomeList({})),
            ]:
            constmeth = getattr(example, methname)
            s_constmeth = iv(constmeth)
            assert isinstance(s_constmeth, annmodel.SomeBuiltin)
            s_meth = s_example.getattr(iv(methname))
            assert isinstance(s_constmeth, annmodel.SomeBuiltin)

    def test_simple_slicing0(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.simple_slice, [list])
        g = a.translator.getflowgraph(snippet.simple_slice)
        for thing in flatten(g):
            if isinstance(thing, Block):
                for op in thing.operations:
                    if op.opname == "newslice":
                        assert isinstance(a.binding(op.result),
                                          annmodel.SomeSlice)

    def test_simple_slicing(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.simple_slice, [list])
        assert isinstance(s, annmodel.SomeList)

    def test_simple_iter_list(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.simple_iter, [list])
        assert isinstance(s, annmodel.SomeIterator)
        
    def test_simple_iter_dict(self):
        a = RPythonAnnotator()
        t = annmodel.SomeDict({}, annmodel.SomeInteger(), annmodel.SomeInteger())
        s = a.build_types(snippet.simple_iter, [t])
        assert isinstance(s, annmodel.SomeIterator)
        
    def test_dict_copy(self):
        a = RPythonAnnotator()
        t = annmodel.SomeDict({}, annmodel.SomeInteger(), annmodel.SomeInteger())
        s = a.build_types(snippet.dict_copy, [t])
        assert isinstance(s, annmodel.SomeDict)
        assert isinstance(s.s_key, annmodel.SomeInteger)
        assert isinstance(s.s_value, annmodel.SomeInteger)

    def test_dict_update(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.dict_update, [int])
        assert isinstance(s, annmodel.SomeDict)
        assert isinstance(s.s_key, annmodel.SomeInteger)
        assert isinstance(s.s_value, annmodel.SomeInteger)
	
        a = RPythonAnnotator()
        s = a.build_types(snippet.dict_update, [str])
        assert isinstance(s, annmodel.SomeDict)
        assert not isinstance(s.s_key, annmodel.SomeString)
        assert not isinstance(s.s_value, annmodel.SomeString)

    def test_dict_keys(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.dict_keys, [])
        assert isinstance(s, annmodel.SomeList)
        assert isinstance(s.s_item, annmodel.SomeString)

    def test_dict_keys2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.dict_keys2, [])
        assert isinstance(s, annmodel.SomeList)
        assert not isinstance(s.s_item, annmodel.SomeString)

    def test_dict_values(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.dict_values, [])
        assert isinstance(s, annmodel.SomeList)
        assert isinstance(s.s_item, annmodel.SomeString)
    
    def test_dict_values2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.dict_values2, [])
        assert isinstance(s, annmodel.SomeList)
        assert not isinstance(s.s_item, annmodel.SomeString)

    def test_dict_items(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.dict_items, [])
        assert isinstance(s, annmodel.SomeList)
        assert isinstance(s.s_item, annmodel.SomeTuple)
        s_key, s_value = s.s_item.items
        assert isinstance(s_key, annmodel.SomeString)
        assert isinstance(s_value, annmodel.SomeInteger)

    def test_exception_deduction(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.exception_deduction, [])
        assert isinstance(s, annmodel.SomeInstance)
        assert s.knowntype is snippet.Exc
        
    def test_exception_deduction_we_are_dumb(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.exception_deduction_we_are_dumb, [])
        assert isinstance(s, annmodel.SomeInstance)
        assert s.knowntype is snippet.Exc
        
    def test_nested_exception_deduction(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.nested_exception_deduction, [])
        assert isinstance(s, annmodel.SomeTuple)
        assert isinstance(s.items[0], annmodel.SomeInstance)
        assert isinstance(s.items[1], annmodel.SomeInstance)
        assert s.items[0].knowntype is snippet.Exc
        assert s.items[1].knowntype is snippet.Exc2
        
    def test_slice_union(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.slice_union, [int])
        assert isinstance(s, annmodel.SomeSlice)

    def test_bltin_code_frame_confusion(self):
        a = RPythonAnnotator()
        a.build_types(snippet.bltin_code_frame_confusion,[])
        f_flowgraph = a.translator.getflowgraph(snippet.bltin_code_frame_f)
        g_flowgraph = a.translator.getflowgraph(snippet.bltin_code_frame_g)
        is_int = isinstance(a.binding(f_flowgraph.getreturnvar()),
                            annmodel.SomeInteger)
        if not is_int:
            py.test.skip("annotator confused with bltin code/frame setup")
        assert isinstance(a.binding(g_flowgraph.getreturnvar()),
                          annmodel.SomeString)


def g(n):
    return [0,1,2,n]

def f_calls_g(n):
    total = 0
    lst = g(n)
    i = 0
    while i < len(lst):
        total += i
        i += 1
    return total
