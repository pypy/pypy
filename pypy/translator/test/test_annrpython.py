
import autopath
from pypy.tool import testit
from pypy.tool.udir import udir

from pypy.translator.annrpython import RPythonAnnotator, annmodel
from pypy.translator.translator import Translator
from pypy.objspace.flow.model import *

from pypy.annotation.model import SomeCallable

from pypy.translator.test import snippet

class AnnonateTestCase(testit.IntTestCase):
    def setUp(self):
        self.space = testit.objspace('flow')

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
        self.assertEquals(a.gettype(fun.getreturnvar()), int)

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
        self.assertEquals(a.gettype(fun.getreturnvar()), int)

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
        self.assertEquals(a.gettype(fun.getreturnvar()), int)

    def test_f_calls_g(self):
        a = RPythonAnnotator()
        s = a.build_types(f_calls_g, [int])
        # result should be an integer
        self.assertEquals(s.knowntype, int)

    def test_lists(self):
        fun = self.make_fun(snippet.poor_man_rev_range)
        a = RPythonAnnotator()
        a.build_types(fun, [int])
        # result should be a list of integers
        self.assertEquals(a.gettype(fun.getreturnvar()), list)
        end_cell = a.binding(fun.getreturnvar())
        self.assertEquals(end_cell.s_item.knowntype, int)

    def test_factorial(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.factorial, [int])
        # result should be an integer
        self.assertEquals(s.knowntype, int)

    def test_factorial2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.factorial2, [int])
        # result should be an integer
        self.assertEquals(s.knowntype, int)

    def test_build_instance(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.build_instance, [])
        # result should be a snippet.C instance
        self.assertEquals(s.knowntype, snippet.C)

    def test_set_attr(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.set_attr, [])
        # result should be an integer
        self.assertEquals(s.knowntype, int)

    def test_merge_setattr(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.merge_setattr, [int])
        # result should be an integer
        self.assertEquals(s.knowntype, int)

    def test_inheritance1(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.inheritance1, [])
        # result should be exactly:
        self.assertEquals(s, annmodel.SomeTuple([
                                a.bookkeeper.immutablevalue(()),
                                annmodel.SomeInteger()
                                ]))

    def test_inheritance2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet._inheritance_nonrunnable, [])
        # result should be exactly:
        self.assertEquals(s, annmodel.SomeTuple([
                                annmodel.SomeInteger(),
                                annmodel.SomeObject()
                                ]))

    def test_poor_man_range(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.poor_man_range, [int])
        # result should be a list of integers
        self.assertEquals(s.knowntype, list)
        self.assertEquals(s.s_item.knowntype, int)

    def test_methodcall1(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet._methodcall1, [int])
        # result should be a tuple of (C, positive_int)
        self.assertEquals(s.knowntype, tuple)
        self.assertEquals(len(s.items), 2)
        self.assertEquals(s.items[0].knowntype, snippet.C)
        self.assertEquals(s.items[1].knowntype, int)
        self.assertEquals(s.items[1].nonneg, True)

    def test_classes_methodcall1(self):
        a = RPythonAnnotator()
        a.build_types(snippet._methodcall1, [int])
        # the user classes should have the following attributes:
        classes = a.bookkeeper.userclasses
        self.assertEquals(classes[snippet.F].attrs.keys(), ['m'])
        self.assertEquals(classes[snippet.G].attrs.keys(), ['m2'])
        self.assertEquals(classes[snippet.H].attrs.keys(), ['attr']) 
        self.assertEquals(classes[snippet.H].about_attribute('attr'),
                          a.bookkeeper.immutablevalue(1))
       

    def test_knownkeysdict(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.knownkeysdict, [int])
        # result should be an integer
        self.assertEquals(s.knowntype, int)

    def test_somebug1(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet._somebug1, [int])
        # result should be a built-in method
        self.assert_(isinstance(s, annmodel.SomeBuiltin))

    def test_with_init(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.with_init, [int])
        # result should be an integer
        self.assertEquals(s.knowntype, int)

    def test_with_more_init(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.with_more_init, [int, bool])
        # the user classes should have the following attributes:
        classes = a.bookkeeper.userclasses
        # XXX on which class should the attribute 'a' appear?  We only
        #     ever flow WithInit.__init__ with a self which is an instance
        #     of WithMoreInit, so currently it appears on WithMoreInit.
        self.assertEquals(classes[snippet.WithMoreInit].about_attribute('a'),
                          annmodel.SomeInteger())
        self.assertEquals(classes[snippet.WithMoreInit].about_attribute('b'),
                          annmodel.SomeBool())

    def test_global_instance(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.global_instance, [])
        # currently this returns the constant 42.
        # XXX not sure this is the best behavior...
        self.assertEquals(s, a.bookkeeper.immutablevalue(42))

    def test_call_five(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.call_five, [])
        # returns should be a list of constants (= 5)
        self.assert_(isinstance(s, annmodel.SomeList))
        self.assertEquals(s.s_item, a.bookkeeper.immutablevalue(5))

    def test_call_five_six(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.call_five_six, [])
        # returns should be a list of positive integers
        self.assert_(isinstance(s, annmodel.SomeList))
        self.assertEquals(s.s_item, annmodel.SomeInteger(nonneg=True))

    def test_constant_result(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.constant_result, [])
        #a.translator.simplify()
        # must return "yadda"
        self.assertEquals(s, a.bookkeeper.immutablevalue("yadda"))
        keys = a.translator.flowgraphs.keys()
        keys.sort()
        expected = [snippet.constant_result,
                    snippet.forty_two,
                    # and not snippet.never_called
                    ]
        expected.sort()
        self.assertEquals(keys, expected)
        a.simplify()
        #a.translator.view()

    def test_call_pbc(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.call_cpbc, [])
        self.assertEquals(s, a.bookkeeper.immutablevalue(42))

    def test_flow_type_info(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_type_info, [object])
        a.translator.simplify()
        a.simplify()
        #a.translator.view()
        self.assertEquals(s.knowntype, int)

    def test_flow_type_info_2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_type_info,
                          [annmodel.SomeInteger(nonneg=True)])
        # this checks that isinstance(i, int) didn't loose the
        # actually more precise information that i is non-negative
        self.assertEquals(s, annmodel.SomeInteger(nonneg=True))

    def test_flow_usertype_info(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_usertype_info, [object])
        #a.translator.view()
        self.assertEquals(s.knowntype, snippet.WithInit)

    def test_flow_usertype_info2(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_usertype_info, [snippet.WithMoreInit])
        #a.translator.view()
        self.assertEquals(s.knowntype, snippet.WithMoreInit)

    def test_flow_identity_info(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.flow_identity_info, [object, object])
        a.translator.simplify()
        a.simplify()
        #a.translator.view()
        self.assertEquals(s, a.bookkeeper.immutablevalue((None, None)))

    def test_mergefunctions(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.mergefunctions, [int])
        # the test is mostly that the above line hasn't blown up
        # but let's at least check *something*
        self.assert_(isinstance(s, SomeCallable))

    def test_func_calls_func_which_just_raises(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.funccallsex, [])
        # the test is mostly that the above line hasn't blown up
        # but let's at least check *something*
        #self.assert_(isinstance(s, SomeCallable))

    def test_tuple_unpack_from_const_tuple_with_different_types(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.func_arg_unpack, [])
        self.assert_(isinstance(s, annmodel.SomeInteger)) 
        self.assertEquals(s.const, 3) 

    def test_pbc_attr_preserved_on_instance(self):
        a = RPythonAnnotator()
        s = a.build_types(snippet.preserve_pbc_attr_on_instance, [bool])
        #a.simplify()
        #a.translator.view()
        self.assertEquals(s, annmodel.SomeInteger(nonneg=True)) 
        #self.assertEquals(s.__class__, annmodel.SomeInteger) 

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


if __name__ == '__main__':
    testit.main()
