import autopath
from pypy.translator.tool.buildpyxmodule import skip_missing_compiler
from pypy.translator.translator import Translator

from pypy.translator.test import snippet 

# XXX this tries to make compiling faster for full-scale testing
from pypy.translator.tool import buildpyxmodule
buildpyxmodule.enable_fast_compilation()

class TestNoTypeCGenTestCase:
    objspacename = 'flow'

    def build_cfunc(self, func, *morefuncs):
        try: func = func.im_func
        except AttributeError: pass
        t = Translator(func)
        for fn in morefuncs:
            t.getflowgraph(fn)
        t.simplify()
        return skip_missing_compiler(t.ccompile)

    def test_simple_func(self):
        cfunc = self.build_cfunc(snippet.simple_func)
        assert cfunc(1) == 2

    def test_while_func(self):
        while_func = self.build_cfunc(snippet.while_func)
        assert while_func(10) == 55

    def test_nested_whiles(self):
        nested_whiles = self.build_cfunc(snippet.nested_whiles)
        assert nested_whiles(111, 114) == (
                          '...!...!...!...!...!')

    def test_poor_man_range(self):
        poor_man_range = self.build_cfunc(snippet.poor_man_range)
        assert poor_man_range(10) == range(10)

    def poor_man_rev_range(self):
        poor_man_rev_range = self.build_cfunc(snippet.poor_man_rev_range)
        assert poor_man_rev_range(10) == range(9,-1,-1)

    def test_simple_id(self):
        #we just want to see, if renaming of parameter works correctly
        #if the first branch is the end branch
        simple_id = self.build_cfunc(snippet.simple_id)
        assert simple_id(9) == 9

    def test_branch_id(self):
        branch_id = self.build_cfunc(snippet.branch_id)
        assert branch_id(1, 2, 3) == 2
        assert branch_id(0, 2, 3) == 3

    def test_int_id(self):
        int_id = self.build_cfunc(snippet.int_id)
        assert int_id(3) == 3

    def dont_test_attrs(self):
        attrs = self.build_cfunc(snippet.attrs)
        assert attrs() == 9

    def test_builtinusage(self):
        fun = self.build_cfunc(snippet.builtinusage)
        assert fun() == 4

    def test_sieve(self):
        sieve = self.build_cfunc(snippet.sieve_of_eratosthenes)
        assert sieve() == 1028

    def test_slice(self):
        half = self.build_cfunc(snippet.half_of_n)
        assert half(10) == 5

    def test_poly_branch(self):
        poly_branch = self.build_cfunc(snippet.poly_branch)
        assert poly_branch(10) == [1,2,3]*2
        assert poly_branch(0) == ['a','b','c']*2

    def test_and(self):
        sand = self.build_cfunc(snippet.s_and)
        assert sand(5, 6) == "yes"
        assert sand(5, 0) == "no"
        assert sand(0, 6) == "no"
        assert sand(0, 0) == "no"

    def test_yast(self):
        yast = self.build_cfunc(snippet.yast)
        assert yast([1000,100,10,1]) == 1111
        assert yast(range(100)) == (99*100)/2

    def test_with_init(self):
        with_init = self.build_cfunc(snippet.with_init)
        assert with_init(0) == 0
        assert with_init(-100) == -100

    def test_with_more_init(self):
        with_more_init = self.build_cfunc(snippet.with_more_init)
        assert with_more_init(10, False) == -10
        assert with_more_init(20, True) == 20

    def test_global_instance(self):
        global_instance = self.build_cfunc(snippet.global_instance)
        assert global_instance() == 42

    def test_global_newstyle_instance(self):
        global_newstyle_instance = self.build_cfunc(snippet.global_newstyle_instance)
        assert global_newstyle_instance().a == 1

    def test_global_recursive_list(self):
        global_recursive_list = self.build_cfunc(snippet.global_recursive_list)
        lst = global_recursive_list()
        assert len(lst) == 1
        assert lst[0] is lst

##     def test_global_badinit(self):
##         global_badinit = self.build_cfunc(snippet.global_badinit)
##         self.assertEquals(global_badinit(), 1)

    def test_multiple_inheritance(self):
        multiple_inheritance = self.build_cfunc(snippet.multiple_inheritance)
        assert multiple_inheritance() == 1+2+3+4

    def test_call_star_args(self):
        call_star_args = self.build_cfunc(snippet.call_star_args)
        assert call_star_args(42) == 52

    def test_call_default_args(self):
        call_default_args = self.build_cfunc(snippet.call_default_args)
        assert call_default_args(42) == 111+42+3

    def test_call_default_and_star_args(self):
        call_default_and_star_args = self.build_cfunc(
            snippet.call_default_and_star_args)
        assert call_default_and_star_args(42) == (
                          (111+42+3+0, -1000-2000-3000+2))

    def test_call_with_star(self):
        call_with_star = self.build_cfunc(snippet.call_with_star)
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
        call_with_keyword = self.build_cfunc(snippet.call_with_keyword)
        assert call_with_keyword(100) == 82

    def test_call_very_complex(self):
        call_very_complex = self.build_cfunc(snippet.call_very_complex,
                                             snippet.default_args)
        assert call_very_complex(5, (3,), {}) == -12
        assert call_very_complex(5, (), {'y': 3}) == -12
        raises(TypeError, call_very_complex, 5, (3,), {'y': 4})

    def test_finallys(self):
        finallys = self.build_cfunc(snippet.finallys)
        assert finallys(['hello']) == 8
        assert finallys('X') == 8
        assert finallys([]) == 6
        assert finallys('XY') == 6

    def test_finally2(self):
        finally2 = self.build_cfunc(snippet.finally2)
        lst = range(10)
        finally2(lst, 5)
        assert lst == [0,1,2,3,4, 6, 6,7,8, 'done']
        dic = {}
        raises(KeyError, finally2, dic, "won't find this key")
        assert dic == {-1: 'done'}

    def test_bare_raise(self):
        bare_raise = self.build_cfunc(snippet.bare_raise)
        assert bare_raise(range(0, 100, 10), False) == 50
        assert bare_raise(range(0, 100, 10), True) == 50
        raises(IndexError, bare_raise, range(0, 30, 10), False)
        assert bare_raise(range(0, 30, 10), True) == None

    def test_get_set_del_slice(self):
        fn = self.build_cfunc(snippet.get_set_del_slice)
        l = list('abcdefghij')
        result = fn(l)
        assert l == [3, 'c', 8, 11, 'h', 9]
        assert result == ([3, 'c'], [9], [11, 'h'])

    def test_global_const_w_init(self):
        fn = self.build_cfunc(snippet.one_thing1)
        assert fn().thingness == 1

    def test_global_const_w_new(self):
        fn = self.build_cfunc(snippet.one_thing2)
        assert fn() == 4

    def test_direct_loop(self):
        # check that remove_direct_loops() does its job correctly
        def direct_loop(n, m):
            x = False
            while 1:
                o = n; n = m; m = o
                n -= 10
                if n < 0:
                    return n, x
                x = True
        fn = self.build_cfunc(direct_loop)
        assert fn(117, 114) == (-6, True)
        assert fn(117, 124) == (-3, True)

    def test_do_try_raise_choose(self):
        fn = self.build_cfunc(snippet.do_try_raise_choose)
        result = fn()
        assert result == [-1,0,1,2]    
