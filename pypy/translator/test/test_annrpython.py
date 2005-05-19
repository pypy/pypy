
import autopath
import py.test
from pypy.tool.udir import udir

from pypy.translator.annrpython import annmodel
from pypy.translator.translator import Translator
from pypy.annotation.listdef import ListDef
from pypy.annotation.dictdef import DictDef
from pypy.objspace.flow.model import *
from pypy.rpython.rarithmetic import r_uint

from pypy.translator.test import snippet

def listitem(s_list):
    assert isinstance(s_list, annmodel.SomeList)
    return s_list.listdef.listitem.s_value

def somelist(s_type=annmodel.SomeObject()):
    return annmodel.SomeList(ListDef(None, s_type))

def dictkey(s_dict):
    assert isinstance(s_dict, annmodel.SomeDict)
    return s_dict.dictdef.dictkey.s_value

def dictvalue(s_dict):
    assert isinstance(s_dict, annmodel.SomeDict)
    return s_dict.dictdef.dictvalue.s_value

def somedict(s_key=annmodel.SomeObject(), s_value=annmodel.SomeObject()):
    return annmodel.SomeDict(DictDef(None, s_key, s_value))


class TestAnnotateTestCase:
    objspacename = 'flow'

    from pypy.translator.annrpython import RPythonAnnotator

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
        a = self.RPythonAnnotator()
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

        a = self.RPythonAnnotator()
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

        a = self.RPythonAnnotator()
        a.build_types(fun, [int])
        assert a.gettype(fun.getreturnvar()) == int

    def test_f_calls_g(self):
        a = self.RPythonAnnotator()
        s = a.build_types(f_calls_g, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_lists(self):
        a = self.RPythonAnnotator()
        end_cell = a.build_types(snippet.poor_man_rev_range, [int])
        # result should be a list of integers
        assert listitem(end_cell).knowntype == int

    def test_factorial(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.factorial, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_factorial2(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.factorial2, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_build_instance(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.build_instance, [])
        # result should be a snippet.C instance
        assert s.knowntype == snippet.C

    def test_set_attr(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.set_attr, [])
        # result should be an integer
        assert s.knowntype == int

    def test_merge_setattr(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.merge_setattr, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_inheritance1(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.inheritance1, [])
        # result should be exactly:
        assert s == annmodel.SomeTuple([
                                a.bookkeeper.immutablevalue(()),
                                annmodel.SomeInteger()
                                ])

    def test_inheritance2(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet._inheritance_nonrunnable, [])
        # result should be exactly:
        assert s == annmodel.SomeTuple([
                                annmodel.SomeInteger(),
                                annmodel.SomeObject()
                                ])

    def test_poor_man_range(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.poor_man_range, [int])
        # result should be a list of integers
        assert listitem(s).knowntype == int

    def test_methodcall1(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet._methodcall1, [int])
        # result should be a tuple of (C, positive_int)
        assert s.knowntype == tuple
        assert len(s.items) == 2
        assert s.items[0].knowntype == snippet.C
        assert s.items[1].knowntype == int
        assert s.items[1].nonneg == True

    def test_classes_methodcall1(self):
        a = self.RPythonAnnotator()
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
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.knownkeysdict, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_generaldict(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.generaldict, [str, int, str, int])
        # result should be an integer
        assert s.knowntype == int

    def test_somebug1(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet._somebug1, [int])
        # result should be a built-in method
        assert isinstance(s, annmodel.SomeBuiltin)

    def test_with_init(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.with_init, [int])
        # result should be an integer
        assert s.knowntype == int

    def test_with_more_init(self):
        a = self.RPythonAnnotator()
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
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.global_instance, [])
        # currently this returns the constant 42.
        # XXX not sure this is the best behavior...
        assert s == a.bookkeeper.immutablevalue(42)

    def test_call_five(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.call_five, [])
        # returns should be a list of constants (= 5)
        assert listitem(s) == a.bookkeeper.immutablevalue(5)

    def test_call_five_six(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.call_five_six, [])
        # returns should be a list of positive integers
        assert listitem(s) == annmodel.SomeInteger(nonneg=True)

    def test_constant_result(self):
        a = self.RPythonAnnotator()
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
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.call_cpbc, [])
        assert s == a.bookkeeper.immutablevalue(42)

    def test_flow_type_info(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.flow_type_info, [object])
        a.translator.simplify()
        a.simplify()
        #a.translator.view()
        assert s.knowntype == int

    def test_flow_type_info_2(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.flow_type_info,
                          [annmodel.SomeInteger(nonneg=True)])
        # this checks that isinstance(i, int) didn't loose the
        # actually more precise information that i is non-negative
        assert s == annmodel.SomeInteger(nonneg=True)

    def test_flow_usertype_info(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.flow_usertype_info, [object])
        #a.translator.view()
        assert s.knowntype == snippet.WithInit

    def test_flow_usertype_info2(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.flow_usertype_info, [snippet.WithMoreInit])
        #a.translator.view()
        assert s.knowntype == snippet.WithMoreInit

    def test_flow_identity_info(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.flow_identity_info, [object, object])
        a.translator.simplify()
        a.simplify()
        #a.translator.view()
        assert s == a.bookkeeper.immutablevalue((None, None))

    def test_mergefunctions(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.mergefunctions, [int])
        # the test is mostly that the above line hasn't blown up
        # but let's at least check *something*
        assert isinstance(s, annmodel.SomePBC)

    def test_func_calls_func_which_just_raises(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.funccallsex, [])
        # the test is mostly that the above line hasn't blown up
        # but let's at least check *something*
        #self.assert_(isinstance(s, SomeCallable))

    def test_tuple_unpack_from_const_tuple_with_different_types(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.func_arg_unpack, [])
        assert isinstance(s, annmodel.SomeInteger) 
        assert s.const == 3 

    def test_pbc_attr_preserved_on_instance(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.preserve_pbc_attr_on_instance, [bool])
        #a.simplify()
        #a.translator.view()
        assert s == annmodel.SomeInteger(nonneg=True) 
        #self.assertEquals(s.__class__, annmodel.SomeInteger) 

    def test_is_and_knowntype_data(self): 
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.is_and_knowntype, [bool])
        #a.simplify()
        #a.translator.view()
        assert s == a.bookkeeper.immutablevalue(None)

    def test_isinstance_and_knowntype_data(self): 
        a = self.RPythonAnnotator()
        x = annmodel.SomePBC({snippet.apbc: True}) 
        s = a.build_types(snippet.isinstance_and_knowntype, [x]) 
        #a.simplify()
        #a.translator.view()
        assert s == x

    def test_somepbc_simplify(self):
        a = self.RPythonAnnotator()
        # this example used to trigger an AssertionError
        a.build_types(snippet.somepbc_simplify, [])

    def test_builtin_methods(self):
        a = self.RPythonAnnotator()
        iv = a.bookkeeper.immutablevalue
        # this checks that some built-in methods are really supported by
        # the annotator (it doesn't check that they operate property, though)
        for example, methname, s_example in [
            ('', 'join',    annmodel.SomeString()),
            ([], 'append',  somelist()), 
            ([], 'extend',  somelist()),           
            ([], 'reverse', somelist()),
            ([], 'insert',  somelist()),
            ([], 'pop',     somelist()),
            ]:
            constmeth = getattr(example, methname)
            s_constmeth = iv(constmeth)
            assert isinstance(s_constmeth, annmodel.SomeBuiltin)
            s_meth = s_example.getattr(iv(methname))
            assert isinstance(s_constmeth, annmodel.SomeBuiltin)

    def test_simple_slicing0(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.simple_slice, [list])
        g = a.translator.getflowgraph(snippet.simple_slice)
        for thing in flatten(g):
            if isinstance(thing, Block):
                for op in thing.operations:
                    if op.opname == "newslice":
                        assert isinstance(a.binding(op.result),
                                          annmodel.SomeSlice)

    def test_simple_slicing(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.simple_slice, [list])
        assert isinstance(s, annmodel.SomeList)

    def test_simple_iter_list(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.simple_iter, [list])
        assert isinstance(s, annmodel.SomeIterator)
        
    def test_simple_iter_dict(self):
        a = self.RPythonAnnotator()
        t = somedict(annmodel.SomeInteger(), annmodel.SomeInteger())
        s = a.build_types(snippet.simple_iter, [t])
        assert isinstance(s, annmodel.SomeIterator)

    def test_simple_zip(self):
        a = self.RPythonAnnotator()
        x = somelist(annmodel.SomeInteger())
        y = somelist(annmodel.SomeString())
        s = a.build_types(snippet.simple_zip, [x,y])
        assert s.knowntype == list
        assert listitem(s).knowntype == tuple
        assert listitem(s).items[0].knowntype == int
        assert listitem(s).items[1].knowntype == str
        
    def test_dict_copy(self):
        a = self.RPythonAnnotator()
        t = somedict(annmodel.SomeInteger(), annmodel.SomeInteger())
        s = a.build_types(snippet.dict_copy, [t])
        assert isinstance(dictkey(s), annmodel.SomeInteger)
        assert isinstance(dictvalue(s), annmodel.SomeInteger)

    def test_dict_update(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.dict_update, [int])
        assert isinstance(dictkey(s), annmodel.SomeInteger)
        assert isinstance(dictvalue(s), annmodel.SomeInteger)

        a = self.RPythonAnnotator()
        s = a.build_types(snippet.dict_update, [str])
        assert not isinstance(dictkey(s), annmodel.SomeString)
        assert not isinstance(dictvalue(s), annmodel.SomeString)

    def test_dict_keys(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.dict_keys, [])
        assert isinstance(listitem(s), annmodel.SomeString)

    def test_dict_keys2(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.dict_keys2, [])
        assert not isinstance(listitem(s), annmodel.SomeString)

    def test_dict_values(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.dict_values, [])
        assert isinstance(listitem(s), annmodel.SomeString)
    
    def test_dict_values2(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.dict_values2, [])
        assert not isinstance(listitem(s), annmodel.SomeString)

    def test_dict_items(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.dict_items, [])
        assert isinstance(listitem(s), annmodel.SomeTuple)
        s_key, s_value = listitem(s).items
        assert isinstance(s_key, annmodel.SomeString)
        assert isinstance(s_value, annmodel.SomeInteger)

    def test_exception_deduction(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.exception_deduction, [])
        assert isinstance(s, annmodel.SomeInstance)
        assert s.knowntype is snippet.Exc
        
    def test_exception_deduction_we_are_dumb(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.exception_deduction_we_are_dumb, [])
        assert isinstance(s, annmodel.SomeInstance)
        assert s.knowntype is snippet.Exc
        
    def test_nested_exception_deduction(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.nested_exception_deduction, [])
        assert isinstance(s, annmodel.SomeTuple)
        assert isinstance(s.items[0], annmodel.SomeInstance)
        assert isinstance(s.items[1], annmodel.SomeInstance)
        assert s.items[0].knowntype is snippet.Exc
        assert s.items[1].knowntype is snippet.Exc2

    def test_exc_deduction_our_exc_plus_others(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.exc_deduction_our_exc_plus_others, [])
        assert isinstance(s, annmodel.SomeInteger)

    def test_exc_deduction_our_excs_plus_others(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.exc_deduction_our_excs_plus_others, [])
        assert isinstance(s, annmodel.SomeInteger)

    def test_operation_always_raising(self):
        def operation_always_raising(n):
            lst = []
            try:
                return lst[n]
            except IndexError:
                return 24
        a = self.RPythonAnnotator()
        s = a.build_types(operation_always_raising, [int])
        assert s == a.bookkeeper.immutablevalue(24)

    def test_slice_union(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.slice_union, [int])
        assert isinstance(s, annmodel.SomeSlice)

    def test_bltin_code_frame_confusion(self):
        a = self.RPythonAnnotator()
        a.build_types(snippet.bltin_code_frame_confusion,[])
        f_flowgraph = a.translator.getflowgraph(snippet.bltin_code_frame_f)
        g_flowgraph = a.translator.getflowgraph(snippet.bltin_code_frame_g)
        # annotator confused by original bltin code/frame setup, we just get SomeObject here
        assert a.binding(f_flowgraph.getreturnvar()).__class__ is annmodel.SomeObject
        assert a.binding(g_flowgraph.getreturnvar()).__class__ is annmodel.SomeObject

    def test_bltin_code_frame_reorg(self):
        a = self.RPythonAnnotator()
        a.build_types(snippet.bltin_code_frame_reorg,[])
        f_flowgraph = a.translator.getflowgraph(snippet.bltin_code_frame_f)
        g_flowgraph = a.translator.getflowgraph(snippet.bltin_code_frame_g)
        assert isinstance(a.binding(f_flowgraph.getreturnvar()),
                            annmodel.SomeInteger)
        assert isinstance(a.binding(g_flowgraph.getreturnvar()),
                          annmodel.SomeString)

    def test_propagation_of_fresh_instances_through_attrs(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.propagation_of_fresh_instances_through_attrs, [int])
        assert s is not None

    def test_propagation_of_fresh_instances_through_attrs_rec_0(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.make_r, [int])
        assert s.knowntype == snippet.R
        Rdef = a.getuserclasses()[snippet.R]
        assert Rdef.attrs['r'].s_value.knowntype == snippet.R
        assert Rdef.attrs['n'].s_value.knowntype == int
        assert Rdef.attrs['m'].s_value.knowntype == int
    
        
    def test_propagation_of_fresh_instances_through_attrs_rec_eo(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.make_eo, [int])
        assert s.knowntype == snippet.B
        Even_def = a.getuserclasses()[snippet.Even]
        Odd_def = a.getuserclasses()[snippet.Odd]
        assert listitem(Even_def.attrs['x'].s_value).knowntype == snippet.Odd
        assert listitem(Even_def.attrs['y'].s_value).knowntype == snippet.Even
        assert listitem(Odd_def.attrs['x'].s_value).knowntype == snippet.Even
        assert listitem(Odd_def.attrs['y'].s_value).knowntype == snippet.Odd        

    def test_flow_rev_numbers(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.flow_rev_numbers, [])
        assert s.knowntype == int
        assert not s.is_constant() # !

    def test_methodcall_is_precise(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.methodcall_is_precise, [])
        classes = a.bookkeeper.userclasses
        assert 'x' not in classes[snippet.CBase].attrs
        assert (classes[snippet.CSub1].attrs['x'].s_value ==
                a.bookkeeper.immutablevalue(42))
        assert (classes[snippet.CSub2].attrs['x'].s_value ==
                a.bookkeeper.immutablevalue('world'))
        assert s == a.bookkeeper.immutablevalue(42)

    def test_class_spec(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.class_spec, [])
        assert s.items[0].knowntype == int
        assert s.items[1].knowntype == str

    def test_exception_deduction_with_raise1(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.exception_deduction_with_raise1, [bool])
        assert isinstance(s, annmodel.SomeInstance)
        assert s.knowntype is snippet.Exc


    def test_exception_deduction_with_raise2(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.exception_deduction_with_raise2, [bool])
        assert isinstance(s, annmodel.SomeInstance)
        assert s.knowntype is snippet.Exc

    def test_exception_deduction_with_raise3(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.exception_deduction_with_raise3, [bool])
        assert isinstance(s, annmodel.SomeInstance)
        assert s.knowntype is snippet.Exc

    def test_type_is(self):
        class C(object):
            pass
        def f(x):
            if type(x) is C:
                return x
            raise Exception
        a = self.RPythonAnnotator()
        s = a.build_types(f, [object])
        assert s.knowntype is C

    def test_ann_assert(self):
        def assert_(x):
            assert x,"XXX"
        a = self.RPythonAnnotator()
        s = a.build_types(assert_, [])
        assert s.const is None

    def test_string_and_none(self):
        def f(n):
            if n:
                return 'y'
            else:
                return 'n'
        def g(n):
            if n:
                return 'y'
            else:
                return None
        a = self.RPythonAnnotator()
        s = a.build_types(f, [bool])
        assert s.knowntype == str
        assert not s.can_be_None
        s = a.build_types(g, [bool])
        assert s.knowntype == str
        assert s.can_be_None

    def test_implicit_exc(self):
        def f(l):
            try:
                l[0]
            except (KeyError, IndexError),e:
                return e
            return None

        a = self.RPythonAnnotator()
        s = a.build_types(f, [list])
        assert s.knowntype is LookupError

    def test_overrides(self):
        import sys
        excs = []
        def record_exc(e):
            """NOT_RPYTHON"""
            excs.append(sys.exc_info)
        def g():
            pass
        def f():
            try:
                g()
            except Exception, e:
                record_exc(e)
        def ann_record_exc(s_e):
            return a.bookkeeper.immutablevalue(None)
        a = self.RPythonAnnotator(overrides={record_exc: ann_record_exc})
        s = a.build_types(f, [])
        assert s.const is None

    def test_freeze_protocol(self):
        class Stuff:
            def __init__(self, flag):
                self.called = False
                self.flag = flag
            def _freeze_(self):
                self.called = True
                return self.flag
        myobj = Stuff(True)
        a = self.RPythonAnnotator()
        s = a.build_types(lambda: myobj, [])
        assert myobj.called
        assert s == annmodel.SomePBC({myobj: True})
        myobj = Stuff(False)
        a = self.RPythonAnnotator()
        s = a.build_types(lambda: myobj, [])
        assert myobj.called
        assert isinstance(s, annmodel.SomeInstance)
        assert s.classdef is a.bookkeeper.getclassdef(Stuff)

    def test_circular_mutable_getattr(self):
        class C:
            pass
        c = C()
        c.x = c
        def f():
            return c.x
        a = self.RPythonAnnotator()
        s = a.build_types(f, [])
        assert s.knowntype == C

    def test_circular_list_type(self):
        def f(n):
            lst = []
            for i in range(n):
                lst = [lst]
            return lst
        a = self.RPythonAnnotator()
        s = a.build_types(f, [int])
        assert listitem(s) == s

    def test_harmonic(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.harmonic, [int])
        assert s.knowntype == float

    def test_bool(self):
        def f(a,b):
            return bool(a) or bool(b)
        a = self.RPythonAnnotator()
        s = a.build_types(f, [int,list])
        assert s.knowntype == bool

    def test_float(self):
        def f(n):
            return float(n)
        a = self.RPythonAnnotator()
        s = a.build_types(f, [int])
        assert s.knowntype == float

    def test_r_uint(self):
        def f(n):
            return n + constant_unsigned_five
        a = self.RPythonAnnotator()
        s = a.build_types(f, [r_uint])
        assert s == annmodel.SomeInteger(nonneg = True, unsigned = True)

    def test_pbc_getattr(self):
        class C:
            def __init__(self, v1, v2):
                self.v2 = v2
                self.v1 = v1

            def _freeze_(self):
                return True

        c1 = C(1,'a')
        c2 = C(2,'b')
        c3 = C(3,'c')

        def f1(l, c):
            l.append(c.v1)
        def f2(l, c):
            l.append(c.v2)

        def g():
            l1 = []
            l2 = []
            f1(l1, c1)
            f1(l1, c2)
            f2(l2, c2)
            f2(l2, c3)
            return l1,l2

        a = self.RPythonAnnotator()
        s = a.build_types(g,[])
        l1, l2 = s.items
        assert listitem(l1).knowntype == int
        assert listitem(l2).knowntype == str

        access_sets = a.getpbcaccesssets()

        ign, rep1,acc1 = access_sets.find(c1)
        ign, rep2,acc2 = access_sets.find(c2)
        ing, rep3,acc3 = access_sets.find(c3)

        assert rep1 is rep2 is rep3
        assert acc1 is acc2 is acc3

        assert len(acc1.objects) == 3
        assert acc1.attrs == {'v1': True, 'v2': True}

        assert access_sets[c1] is acc1
        py.test.raises(KeyError, "access_sets[object()]")
        
    def test_isinstance_usigned(self):
        def f(x):
            return isinstance(x, r_uint)
        def g():
            v = r_uint(1)
            return f(v)
        a = self.RPythonAnnotator()
        s = a.build_types(g, [])
        assert s.const == True

    def test_alloc_like(self):
        class C1(object):
            pass
        class C2(object):
            pass

        def inst(cls):
            return cls()

        def alloc(cls):
            i = inst(cls)
            assert isinstance(i, cls)
            return i
        alloc._specialize_ = "location"

        def f():
            c1 = alloc(C1)
            c2 = alloc(C2)
            return c1,c2
        a = self.RPythonAnnotator()
        s = a.build_types(f, [])
        assert s.items[0].knowntype == C1
        assert s.items[1].knowntype == C2

    def test_assert_list_doesnt_lose_info(self):
        class T(object):
            pass
        def g(l):
            assert isinstance(l, list)
            return l
        def f():
            l = [T()]
            return g(l)
        a = self.RPythonAnnotator()
        s = a.build_types(f, [])
        assert listitem(s).knowntype == T
          
    def test_assert_type_is_list_doesnt_lose_info(self):
        class T(object):
            pass
        def g(l):
            assert type(l) is list
            return l
        def f():
            l = [T()]
            return g(l)
        a = self.RPythonAnnotator()
        s = a.build_types(f, [])
        assert listitem(s).knowntype == T

    def test_int_str_mul(self):
        def f(x,a,b):
            return a*x+x*b
        a = self.RPythonAnnotator()
        s = a.build_types(f, [str,int,int])
        assert s.knowntype == str

    def test_list_tuple(self):
        def g0(x):
            return list(x)
        def g1(x):
            return list(x)
        def f(n):
            l1 = g0(())
            l2 = g1((1,))
            if n:
                t = (1,)
            else:
                t = (2,)
            l3 = g1(t)
            return l1, l2, l3
        a = self.RPythonAnnotator()
        s = a.build_types(f, [bool])
        assert listitem(s.items[0]) == annmodel.SomeImpossibleValue()
        assert listitem(s.items[1]).knowntype == int
        assert listitem(s.items[2]).knowntype == int

    def test_empty_list(self):
        def f():
            l = []
            return bool(l)
        def g():
            l = []
            x = bool(l)
            l.append(1)
            return x, bool(l)
        
        a = self.RPythonAnnotator()
        s = a.build_types(f, [])
        assert s.const == False

        a = self.RPythonAnnotator()
        s = a.build_types(g, [])

        assert s.items[0].knowntype == bool and not s.items[0].is_constant()
        assert s.items[1].knowntype == bool and not s.items[1].is_constant()
        
    def test_empty_dict(self):
        def f():
            d = {}
            return bool(d)
        def g():
            d = {}
            x = bool(d)
            d['a'] = 1
            return x, bool(d)
        
        a = self.RPythonAnnotator()
        s = a.build_types(f, [])
        assert s.const == False

        a = self.RPythonAnnotator()
        s = a.build_types(g, [])

        assert s.items[0].knowntype == bool and not s.items[0].is_constant()
        assert s.items[1].knowntype == bool and not s.items[1].is_constant()

    def test_call_two_funcs_but_one_can_only_raise(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.call_two_funcs_but_one_can_only_raise,
                          [int])
        assert s == a.bookkeeper.immutablevalue(None)

    def test_reraiseKeyError(self):
        def f(dic):
            try:
                dic[5]
            except KeyError:
                raise
        a = self.RPythonAnnotator()
        a.build_types(f, [dict])
        fg = a.translator.getflowgraph(f)
        et, ev = fg.exceptblock.inputargs
        t = annmodel.SomeObject()
        t.knowntype = type
        t.const = KeyError
        t.is_type_of = [ev]
        assert a.binding(et) == t
        assert isinstance(a.binding(ev), annmodel.SomeInstance) and a.binding(ev).classdef.cls == KeyError

    def test_reraiseAnything(self):
        def f(dic):
            try:
                dic[5]
            except:
                raise
        a = self.RPythonAnnotator()
        a.build_types(f, [dict])
        fg = a.translator.getflowgraph(f)
        et, ev = fg.exceptblock.inputargs
        t = annmodel.SomeObject()
        t.knowntype = type
        t.is_type_of = [ev]
        assert a.binding(et) == t
        assert isinstance(a.binding(ev), annmodel.SomeInstance) and a.binding(ev).classdef.cls == LookupError

    def test_exception_mixing(self):
        def h():
            pass

        def g():
            pass

        class X(Exception):
            def __init__(self, x=0):
                self.x = x

        def f(a, l):
            if a==1:
                raise X
            elif a==2:
                raise X(1)
            elif a==3:
                raise X,4
            else:
                try:
                    l[0]
                    x,y = l
                    g()
                finally:
                    h()
        a = self.RPythonAnnotator()
        a.build_types(f, [int, list])
        fg = a.translator.getflowgraph(f)
        et, ev = fg.exceptblock.inputargs
        t = annmodel.SomeObject()
        t.knowntype = type
        t.is_type_of = [ev]
        assert a.binding(et) == t
        assert isinstance(a.binding(ev), annmodel.SomeInstance) and a.binding(ev).classdef.cls == Exception

    def test_try_except_raise_finally1(self):
        def h(): pass
        def g(): pass
        class X(Exception): pass
        def f():
            try:
                try:
                    g()
                except X:
                    h()
                    raise
            finally:
                h()
        a = self.RPythonAnnotator()
        a.build_types(f, [])
        fg = a.translator.getflowgraph(f)
        et, ev = fg.exceptblock.inputargs
        t = annmodel.SomeObject()
        t.knowntype = type
        t.is_type_of = [ev]
        assert a.binding(et) == t
        assert isinstance(a.binding(ev), annmodel.SomeInstance) and a.binding(ev).classdef.cls == Exception

    def test_sys_attrs(self):
        import sys
        def f():
            return sys.argv[0]
        a = self.RPythonAnnotator()
        try:
            oldvalue = sys.argv
            sys.argv = []
            s = a.build_types(f, [])
        finally:
            sys.argv = oldvalue
        assert s is not None
            


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

constant_unsigned_five = r_uint(5)
