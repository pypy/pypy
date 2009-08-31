"""
Description
_____________________________

This test is almost a copy of test_genc.py
The setup code is slightly different:
Instead of compiling single functions from
snippets.py, almost all of snippets is translated,
up to the point where they are untranslatable.
snippets has been slightly re-ordered for that.

The idea was to create a couple of tests without much
extra work, in a sense derived from the test_genc.

A problem with that is, that the tests actually should
be run at application level. The test code checks real
Python values,so we have to do tricks to unwrap things.
This is limited:
Some tests cannot work, since they mutate their arguments.
Some tests operate with un-unwrappable things.
Those are disabled for the moment by an 'needapp_' prefix.

XXX think about a way to produce more tests from a common
XXX basis. Should we write generators for such tests like this?
"""
import autopath
import py
from pypy.tool.udir import udir
from pypy.objspace.flow.model import *
from pypy.translator.geninterplevel import translate_as_module
from pypy.translator.test import snippet 
from pypy.interpreter.error import OperationError
from py.code import Source

class TestGenRpyTestCase:
    objspacename = 'std'

    snippet_ad = """if 1:
        def import_func():
            import copy_reg
            return copy_reg._reconstructor.func_code.co_name

        def import_sys_func():
            import sys
            return sys.__name__

        def unicode_test(x):
            return unicode(x, 'ascii')
"""

    def setup_class(cls): 
        # simply compile snippets just once
        src = str(Source(snippet))
        # truncate non-compilable stuff for now:
        p = src.index('Non compilable Functions')
        src = src[:p] + '\n'
        # put our ad into snippet
        exec cls.snippet_ad in snippet.__dict__
        src += cls.snippet_ad
        # just in case of trouble, we produce a tempfile
        ini, newsrc = translate_as_module(src, tmpname = str(
            udir.join("_geninterp_test.py")))
        cls.w_glob = ini(cls.space)

    def build_interpfunc(self, func, *morefuncs):
        # we ignore morefuncs, since they live in snippets
        space = self.space
        func = space.getitem(self.w_glob, space.wrap(func.__name__))
        def wrapunwrap(*args):
            w_args = space.wrap(args)
            try:
                w_res = space.call(func, w_args)
            except OperationError, e:
                w_typ = e.w_type
                # XXX how to unwrap an exception?
                name = space.unwrap(space.getattr(w_typ, space.wrap('__name__')))
                exc = __builtins__[name]
                raise exc
            return space.unwrap(w_res)
        return wrapunwrap

    # small addition to see whether imports look fine
    def test_import(self):
        import copy_reg
        impfunc = self.build_interpfunc(snippet.import_func)
        assert impfunc() == '_reconstructor'

    def test_import_sys(self):
        impfunc = self.build_interpfunc(snippet.import_sys_func)
        assert impfunc() == 'sys'
        
    def test_simple_func(self):
        cfunc = self.build_interpfunc(snippet.simple_func)
        assert cfunc(1) == 2

    def test_while_func(self):
        while_func = self.build_interpfunc(snippet.while_func)
        assert while_func(10) == 55

    def test_nested_whiles(self):
        nested_whiles = self.build_interpfunc(snippet.nested_whiles)
        assert nested_whiles(111, 114) == (
                          '...!...!...!...!...!')

    def test_poor_man_range(self):
        poor_man_range = self.build_interpfunc(snippet.poor_man_range)
        assert poor_man_range(10) == range(10)

    def poor_man_rev_range(self):
        poor_man_rev_range = self.build_interpfunc(snippet.poor_man_rev_range)
        assert poor_man_rev_range(10) == range(9,-1,-1)

    def test_simple_id(self):
        #we just want to see, if renaming of parameter works correctly
        #if the first branch is the end branch
        simple_id = self.build_interpfunc(snippet.simple_id)
        assert simple_id(9) == 9

    def test_branch_id(self):
        branch_id = self.build_interpfunc(snippet.branch_id)
        assert branch_id(1, 2, 3) == 2
        assert branch_id(0, 2, 3) == 3

    def test_int_id(self):
        int_id = self.build_interpfunc(snippet.int_id)
        assert int_id(3) == 3

    def dont_test_attrs(self):
        attrs = self.build_interpfunc(snippet.attrs)
        assert attrs() == 9

    def test_builtinusage(self):
        fun = self.build_interpfunc(snippet.builtinusage)
        assert fun() == 4

    def xpensive_test_sieve(self):
        sieve = self.build_interpfunc(snippet.sieve_of_eratosthenes)
        assert sieve() == 1028

    def test_slice(self):
        half = self.build_interpfunc(snippet.half_of_n)
        assert half(10) == 5

    def test_poly_branch(self):
        poly_branch = self.build_interpfunc(snippet.poly_branch)
        assert poly_branch(10) == [1,2,3]*2
        assert poly_branch(0) == ['a','b','c']*2

    def test_and(self):
        sand = self.build_interpfunc(snippet.s_and)
        assert sand(5, 6) == "yes"
        assert sand(5, 0) == "no"
        assert sand(0, 6) == "no"
        assert sand(0, 0) == "no"

    def test_yast(self):
        yast = self.build_interpfunc(snippet.yast)
        assert yast([1000,100,10,1]) == 1111
        assert yast(range(100)) == (99*100)/2

    def test_with_init(self):
        with_init = self.build_interpfunc(snippet.with_init)
        assert with_init(0) == 0
        assert with_init(-100) == -100

    def test_with_more_init(self):
        with_more_init = self.build_interpfunc(snippet.with_more_init)
        assert with_more_init(10, False) == -10
        assert with_more_init(20, True) == 20

    def needapp_test_global_instance(self):
        global_instance = self.build_interpfunc(snippet.global_instance)
        assert global_instance() == 42

    def needapp_test_global_newstyle_instance(self):
        global_newstyle_instance = self.build_interpfunc(snippet.global_newstyle_instance)
        assert global_newstyle_instance().a == 1

    def needapp_test_global_recursive_list(self):
        global_recursive_list = self.build_interpfunc(snippet.global_recursive_list)
        lst = global_recursive_list()
        assert len(lst) == 1
        assert lst[0] is lst

##     def test_global_badinit(self):
##         global_badinit = self.build_interpfunc(snippet.global_badinit)
##         self.assertEquals(global_badinit(), 1)

    def test_multiple_inheritance(self):
        multiple_inheritance = self.build_interpfunc(snippet.multiple_inheritance)
        assert multiple_inheritance() == 1+2+3+4

    def test_call_star_args0(self):
        call_star_args = self.build_interpfunc(snippet.call_star_args0)
        assert call_star_args(42) == 21

    def test_call_star_args1(self):
        call_star_args = self.build_interpfunc(snippet.call_star_args1)
        assert call_star_args(30) == 40

    def test_call_star_args1def(self):
        call_star_args = self.build_interpfunc(snippet.call_star_args1def)
        assert call_star_args(7) == 45

    def test_call_star_args(self):
        call_star_args = self.build_interpfunc(snippet.call_star_args)
        assert call_star_args(42) == 52

    def test_call_default_args(self):
        call_default_args = self.build_interpfunc(snippet.call_default_args)
        assert call_default_args(42) == 111+42+3

    def test_call_default_and_star_args(self):
        call_default_and_star_args = self.build_interpfunc(
            snippet.call_default_and_star_args)
        assert call_default_and_star_args(42) == (
                          (111+42+3+0, -1000-2000-3000+2))

    def test_call_with_star(self):
        call_with_star = self.build_interpfunc(snippet.call_with_star)
        assert call_with_star(()) == -15L
        assert call_with_star((4,)) == -13L
        assert call_with_star((4,7)) == -9L
        assert call_with_star([]) == -15L
        assert call_with_star([4]) == -13L
        assert call_with_star([4,7]) == -9L
        raises(TypeError, call_with_star, (4,7,12))
        raises(TypeError, call_with_star, [4,7,12,63])
        raises(TypeError, call_with_star, 521)

    def test_call_with_keyword(self):
        call_with_keyword = self.build_interpfunc(snippet.call_with_keyword)
        assert call_with_keyword(100) == 82

    def test_call_very_complex(self):
        call_very_complex = self.build_interpfunc(snippet.call_very_complex,
                                             snippet.default_args)
        assert call_very_complex(5, (3,), {}) == -12
        assert call_very_complex(5, (), {'y': 3}) == -12
        raises(TypeError, call_very_complex, 5, (3,), {'y': 4})

    def test_finallys(self):
        finallys = self.build_interpfunc(snippet.finallys)
        assert finallys(['hello']) == 8
        assert finallys('X') == 8
        assert finallys([]) == 6
        assert finallys('XY') == 6

    def needapp_test_finally2(self):
        finally2 = self.build_interpfunc(snippet.finally2)
        lst = range(10)
        finally2(lst, 5)
        assert lst == [0,1,2,3,4, 6, 6,7,8, 'done']
        dic = {}
        raises(KeyError, finally2, dic, "won't find this key")
        assert dic == {-1: 'done'}

    def test_bare_raise(self):
        bare_raise = self.build_interpfunc(snippet.bare_raise)
        assert bare_raise(range(0, 100, 10), False) == 50
        assert bare_raise(range(0, 100, 10), True) == 50
        raises(IndexError, bare_raise, range(0, 30, 10), False)
        assert bare_raise(range(0, 30, 10), True) == None

    def needapp_test_get_set_del_slice(self):
        fn = self.build_interpfunc(snippet.get_set_del_slice)
        l = list('abcdefghij')
        result = fn(l)
        assert l == [3, 'c', 8, 11, 'h', 9]
        assert result == ([3, 'c'], [9], [11, 'h'])

    def test_do_try_raise_choose(self):
        fn = self.build_interpfunc(snippet.do_try_raise_choose)
        result = fn()
        assert result == [-1,0,1,2]


    def test_t_isinstance(self):
        fn = self.build_interpfunc(snippet.t_isinstance)
        result = fn(1, 2)
        assert result == True

    def test_t_issubclass(self):
        fn = self.build_interpfunc(snippet.t_issubclass)
        result = fn(1, 2)
        assert result == True        

    def test_negative_long(self):
        fn = self.build_interpfunc(snippet.t_neg_long)
        result = fn()
        assert result == -132L and type(result) is long

    def test_unicode_with_encoding(self):
        fn = self.build_interpfunc(snippet.unicode_test)
        result = fn("abc")
        assert result == u"abc" and type(result) is unicode

    def test_attributeerror(self):
        fn = self.build_interpfunc(snippet.t_attrerror)
        result = fn(42)
        assert result == 567

    def test_Exception_subclass(self):
        fn = self.build_interpfunc(snippet.exception_subclass_sanity)
        result = fn(7)
        assert result == 7

    def test_property(self):
        fn = self.build_interpfunc(snippet.run_prop)
        assert fn(23) == 23
