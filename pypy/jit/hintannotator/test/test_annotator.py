import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.jit.hintannotator.annotator import HintAnnotator
from pypy.jit.hintannotator.policy import StopAtXPolicy, HintAnnotatorPolicy
from pypy.jit.hintannotator.bookkeeper import HintBookkeeper
from pypy.jit.hintannotator.model import *
from pypy.rpython.lltypesystem import lltype
from pypy.rlib.jit import hint, we_are_jitted
from pypy.annotation import model as annmodel
from pypy.objspace.flow import model as flowmodel
from pypy.translator.backendopt.inline import auto_inlining
from pypy import conftest

P_DEFAULT = HintAnnotatorPolicy(entrypoint_returns_red=False)
P_OOPSPEC = HintAnnotatorPolicy(oopspec=True,
                                entrypoint_returns_red=False)
P_OOPSPEC_NOVIRTUAL = HintAnnotatorPolicy(oopspec=True,
                                          novirtualcontainer=True,
                                          entrypoint_returns_red=False)
P_NOVIRTUAL = HintAnnotatorPolicy(novirtualcontainer=True,
                                  entrypoint_returns_red=False)


def setup_for_indirect_call(h, g):
    def call(fn, x):
        return fn(x)
    return call, [h, g]

def setup_for_oosend(h, g):
    def call(obj, x):
        return obj.call(x)
    
    class A:
        def call(self, x):
            return h(x)
    class B(A):
        def call(self, x):
            return g(x)
        
    return call, [A(), B()]

def test_setup_for_indirect_call_oosend():
    def h(x):
        return x+1
    def g(x):
        return x*2
    call, lst = setup_for_indirect_call(h, g)
    assert call(lst[0], 41) == 42
    assert call(lst[1], 41) == 82

    call, lst = setup_for_oosend(h, g)
    assert call(lst[0], 41) == 42
    assert call(lst[1], 41) == 82

class AbstractAnnotatorTest:
    type_system = None
    
    def hannotate(self, func, argtypes, policy=P_DEFAULT, annotator=False, inline=None,
                  backendoptimize=False):
        # build the normal ll graphs for ll_function
        t = TranslationContext()
        a = t.buildannotator()
        a.build_types(func, argtypes)
        rtyper = t.buildrtyper(type_system = self.type_system)
        rtyper.specialize()
        if inline:
            auto_inlining(t, threshold=inline)
        if backendoptimize:
            from pypy.translator.backendopt.all import backend_optimizations
            backend_optimizations(t)
        graph1 = graphof(t, func)

        # build hint annotator types
        hannotator = HintAnnotator(base_translator=t, policy=policy)
        hs = hannotator.build_types(graph1, [SomeLLAbstractConstant(v.concretetype,
                                                                    {OriginFlags(): True})
                                             for v in graph1.getargs()])
        hannotator.simplify()
        t = hannotator.translator
        if conftest.option.view:
            t.view()
        if annotator:
            return hs, hannotator
        else:
            return hs


class BaseAnnotatorTest(AbstractAnnotatorTest):
    
    def test_simple(self):
        def ll_function(x, y):
            return x + y
        hs = self.hannotate(ll_function, [int, int])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert len(hs.origins) == 3
        assert hs.concretetype == lltype.Signed

    def test_join(self):
        def ll_function(cond, x,y):
            if cond:
                z = x+y
            else:
                z = x-y
            return z
        hs = self.hannotate(ll_function, [bool, int, int])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert len(hs.origins) == 4
        assert hs.concretetype == lltype.Signed

    def test_simple_hint_result(self):
        def ll_function(cond, x,y):
            if cond:
                z = x+y
            else:
                z = x-y
            z = hint(z, concrete=True)
            return z
        hs = self.hannotate(ll_function, [bool, int, int])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.eager_concrete
        assert hs.concretetype == lltype.Signed

    def test_deepfreeze(self):

        A = lltype.GcArray(lltype.Signed)

        def ll_function(a, i):
            a = hint(a, deepfreeze=True)
            res = a[i]
            res = hint(res, concrete=True)

            res = hint(res, variable=True)
            return res

        hs = self.hannotate(ll_function, [annmodel.SomePtr(lltype.Ptr(A)), int])
        assert type(hs) is SomeLLAbstractVariable
        assert hs.concretetype == lltype.Signed

    def test_lists_deepfreeze(self):

        l1 = [1,2,3,4,5]
        l2 = [6,7,8,9,10]

        def getlist(n):
            if n:
                return l1
            else:
                return l2

        def ll_function(n, i):
            l = getlist(n)
            l = hint(l, deepfreeze=True)

            res = l[i]
            res = hint(res, concrete=True)

            res = hint(res, variable=True)
            return res

        hs = self.hannotate(ll_function, [int, int], policy=P_NOVIRTUAL)
        assert hs.concretetype == lltype.Signed

    def test_dicts_deepfreeze(self):

        d1 = {1:2, 2:3}
        d2 = {2:3, 3:4}

        def getdict(n):
            if n:
                return d1
            else:
                return d2

        def ll_function(n, i):
            d = getdict(n)
            d = hint(d, deepfreeze=True)

            res = d[i]
            res = hint(res, concrete=True)

            res = hint(res, variable=True)
            return res

        # must backendoptimize to remove the mallocs related to the interior ptrs
        hs = self.hannotate(ll_function, [int, int], policy=P_NOVIRTUAL,
                       backendoptimize=True)
        assert hs.concretetype == lltype.Signed


    def test_simple_hint_origins(self):
        def ll_function(cond, x,y):
            if cond:
                z = x+y
            else:
                z = x-y
            z1 = hint(z, concrete=True)
            return z # origin of z1
        hs, ha = self.hannotate(ll_function, [bool, int, int], annotator=True)
        assert isinstance(hs, SomeLLAbstractConstant)
        assert len(hs.origins) == 4
        assert hs.is_fixed()
        assert hs.concretetype == lltype.Signed
        ll_function_graph = graphof(ha.base_translator, ll_function)
        gdesc = ha.bookkeeper.getdesc(ll_function_graph)
        _, x_v, y_v = gdesc._cache[None].getargs()
        assert ha.binding(x_v).is_fixed()
        assert ha.binding(y_v).is_fixed()

    def test_simple_variable(self):
        def ll_function(x,y):
            x = hint(x, variable=True) # special hint only for testing purposes!!!
            return x + y
        hs = self.hannotate(ll_function, [int, int])
        assert type(hs) is SomeLLAbstractVariable
        assert hs.concretetype == lltype.Signed

    def test_simple_concrete_propagation(self):
        def ll_function(x,y):
            x = hint(x, concrete=True)
            return x + y
        hs = self.hannotate(ll_function, [int, int])
        assert type(hs) is SomeLLAbstractConstant
        assert hs.eager_concrete
        assert hs.concretetype == lltype.Signed

    def test_union(self):
        unionof = annmodel.unionof
        av1, av2 = SomeLLAbstractVariable(lltype.Signed), SomeLLAbstractVariable(lltype.Signed)
        cv1, cv2 = SomeLLAbstractConstant(lltype.Signed, {}, eager_concrete=True), SomeLLAbstractConstant(lltype.Signed, {}, eager_concrete=True)
        ac1, ac2 = SomeLLAbstractConstant(lltype.Signed, {}), SomeLLAbstractConstant(lltype.Signed, {})
        ac3 = SomeLLAbstractConstant(lltype.Signed, {})
        ac3.const = 3
        ac4 = SomeLLAbstractConstant(lltype.Signed, {})
        ac4.const = 4
        assert unionof(av1, av2) == av1
        assert unionof(cv1, cv2) == cv2
        assert unionof(ac1, ac2) == ac1
        assert unionof(ac3, ac3) == ac3
        assert unionof(ac3, ac2) == ac1
        assert unionof(ac4, ac3) == ac1
        # degenerating cases
        py.test.raises(annmodel.UnionError, "unionof(cv1, av1)")
        py.test.raises(annmodel.UnionError, "unionof(av1, cv1)")

        # MAYBE...
        #py.test.raises(annmodel.UnionError, "unionof(ac1, cv1)")
        #py.test.raises(annmodel.UnionError, "unionof(cv1, ac1)")
        assert unionof(cv1, ac1) == ac1
        assert unionof(ac1, cv1) == ac1

        # constant with values
        assert unionof(av1, ac1) == av1
        assert unionof(ac1, av1) == av1
        assert unionof(ac3, av1) == av1
        assert unionof(av2, ac4) == av1

    def test_op_meet(self):
        def meet(hs1, hs2):
            bk = HintBookkeeper(None)
            block = flowmodel.Block([])
            block.operations.append(flowmodel.SpaceOperation('x', [],
                                                             flowmodel.Variable()))
            bk.enter(("graph", block, 0))
            bk.current_op_concretetype = lambda: lltype.Signed     # hack
            return pair(hs1, hs2).int_add()
        av1, av2 = SomeLLAbstractVariable(lltype.Signed), SomeLLAbstractVariable(lltype.Signed)
        cv1, cv2 = SomeLLAbstractConstant(lltype.Signed, {}, True), SomeLLAbstractConstant(lltype.Signed, {}, True)
        ac1, ac2 = SomeLLAbstractConstant(lltype.Signed, {}), SomeLLAbstractConstant(lltype.Signed, {})
        assert meet(av1, av2) == av1
        res = meet(cv1, cv2)
        assert res.eager_concrete
        assert isinstance(meet(ac1, ac2), SomeLLAbstractConstant)
        assert meet(ac1, cv1).eager_concrete
        assert meet(cv1, ac1).eager_concrete
        assert meet(av1, cv1) == av1
        assert meet(cv1, av1) == av1
        assert meet(ac1, av1) == av1
        assert meet(av1, ac1) == av1

    def test_loop(self):
        def ll_function(x, y):
            while x > 0:
                y += x
                x -= 1
            return y
        hs = self.hannotate(ll_function, [int, int])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 4

    def test_loop1(self):
        def ll_function(x, y):
            while x > 0:
                x1 = hint(x, concrete=True)
                if x1 == 7:
                    y += x
                x -= 1
            return y
        hs = self.hannotate(ll_function, [int, int])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 4

    def test_simple_struct(self):
        S = self.make_struct('helloworld', ('hello', lltype.Signed),
                                           ('world', lltype.Signed),
                             hints={'immutable': True})
        def ll_function(s):
            return s.hello * s.world
        hs = self.hannotate(ll_function, [self.annotate_struct(S)])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 4

    def test_simple_struct_malloc(self):
        S = self.make_struct('helloworld', ('hello', lltype.Signed),
                                           ('world', lltype.Signed))
        malloc = self.malloc
        def ll_function(x):
            s = malloc(S)
            s.hello = x
            return s.hello + s.world

        hs = self.hannotate(ll_function, [int])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 2

    def test_container_union(self):
        S = self.make_struct('helloworld', ('hello', lltype.Signed),
                                           ('world', lltype.Signed))
        malloc = self.malloc
        def ll_function(cond, x, y):
            if cond:
                s = malloc(S)
                s.hello = x
            else:
                s = malloc(S)
                s.world = y
            return s.hello + s.world

        hs = self.hannotate(ll_function, [bool, int, int])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 3

    def test_simple_call(self):
        def ll2(x, y, z):
            return x + (y + 42)
        def ll1(x, y, z):
            return ll2(x, y - z, x + y + z)
        hs = self.hannotate(ll1, [int, int, int])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 5

    def test_simple_method_call(self):
        class A:
            def ll2(self, x, y, z):
                return x + (y + 42)
        obj = A()
        def ll1(x, y, z):
            return obj.ll2(x, y - z, x + y + z)
        hs = self.hannotate(ll1, [int, int, int], policy=P_NOVIRTUAL)
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 5

    def test_simple_method_call_var(self):
        class A:
            def ll2(self, x, y, z):
                return x + (y + 42)
        def ll1(x, y, z):
            obj = A()
            return obj.ll2(x, y - z, x + y + z)
        hs = self.hannotate(ll1, [int, int, int], policy=P_NOVIRTUAL)
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 5

    def test_simple_list_operations(self):
        def ll_function(x, y, index):
            l = [x]
            l.append(y)
            return l[index]
        hs = self.hannotate(ll_function, [int, int, int], policy=P_OOPSPEC)
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 4

    def test_some_more_list_operations(self):
        def ll_function(x, y, index):
            l = []
            l.append(x)
            l[0] = y
            return (l+list(l))[index]
        hs = self.hannotate(ll_function, [int, int, int], policy=P_OOPSPEC)
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed
        assert len(hs.origins) == 4

    def test_make_a_list(self):
        def ll_function(x, y):
            return [x, y]
        hs = self.hannotate(ll_function, [int, int], policy=P_OOPSPEC)
        assert isinstance(hs, SomeLLAbstractContainer)

    def test_frozen_list(self):
        lst = [5, 7, 9]
        def ll_function(x):
            mylist = hint(lst, deepfreeze=True)
            z = mylist[x]
            hint(z, concrete=True)
            return z
        hs = self.hannotate(ll_function, [int], policy=P_OOPSPEC_NOVIRTUAL)
        assert hs.is_green()

    def test_prebuilt_structure(self):
        S = self.make_struct('S', ('n', lltype.Signed))
        s = self.malloc(S)
        def ll1(n):
            s.n = n
            return s.n
        hs = self.hannotate(ll1, [int])
        assert isinstance(hs, SomeLLAbstractVariable)

    def test_simple_fixed_call(self):
        def ll_help(cond, x, y):
            if cond:
                z = x+y
            else:
                z = x-y
            return z
        def ll_function(cond, x,y, x1, y1):
            z1 = ll_help(cond, x1, y1)
            z = ll_help(cond, x, y)
            z = hint(z, concrete=True)
            return z
        hs, ha  = self.hannotate(ll_function, [bool, int, int, int, int], annotator=True)
        assert hs.eager_concrete
        assert hs.concretetype == lltype.Signed
        ll_help_graph = graphof(ha.base_translator, ll_help)
        gdesc = ha.bookkeeper.getdesc(ll_help_graph)
        assert not ha.binding(gdesc._cache[None].getreturnvar()).is_fixed()
        assert len(gdesc._cache) == 2
        assert ha.binding(gdesc._cache['fixed'].getreturnvar()).is_fixed()    

    def test_specialize_calls(self):
        def ll_add(x, y):
            return x+y
        def ll_function(x,y):
            z0 = ll_add(y, 2)
            z1 = ll_add(x, y)
            x1 = hint(x, concrete=True)
            z2 = ll_add(x1, y)
            return z2
        hs, ha  = self.hannotate(ll_function, [int, int], annotator=True)
        assert hs.eager_concrete
        assert hs.concretetype == lltype.Signed
        ll_add_graph = graphof(ha.base_translator, ll_add)
        gdesc = ha.bookkeeper.getdesc(ll_add_graph)    
        assert len(gdesc._cache) == 2
        assert 'Exxx' in gdesc._cache
        v1, v2 = gdesc._cache['Exxx'].getargs()

        assert isinstance(ha.binding(v1), SomeLLAbstractConstant)
        assert isinstance(ha.binding(v2), SomeLLAbstractConstant)
        assert ha.binding(v1).eager_concrete
        assert not ha.binding(v2).is_fixed()

    def test_specialize_deepfreeze_calls(self):

        l1 = [1,2,3,4,5]
        l2 = [6,7,8,9,10]

        def getlist(n):
            if n:
                return l1
            else:
                return l2

        def ll_get(l, i):
            return l[i]

        def ll_function(n, i):
            l = getlist(n)

            l2 = ll_get(l, 0)

            l = hint(l, deepfreeze=True)
            res = ll_get(l, i)
            return res

        hs, ha = self.hannotate(ll_function, [int, int], annotator=True, policy=P_NOVIRTUAL)
        assert hs.deepfrozen
        assert hs.concretetype == lltype.Signed
        ll_get_graph = graphof(ha.base_translator, ll_get)
        gdesc = ha.bookkeeper.getdesc(ll_get_graph)    
        assert len(gdesc._cache) == 2
        assert 'xDxx' in gdesc._cache
        v1, v2 = gdesc._cache['xDxx'].getargs()

        assert isinstance(ha.binding(v1), SomeLLAbstractConstant)
        assert isinstance(ha.binding(v2), SomeLLAbstractConstant)
        assert ha.binding(v1).deepfrozen

    def test_deepfreeze_variables(self):
        l1 = [[1], [2, 3], [4], []]
        def ll_function(i):
            i = hint(i, variable=True)
            l = hint(l1, deepfreeze=True)
            return l[i]

        hs, ha = self.hannotate(ll_function, [int], annotator=True, policy=P_NOVIRTUAL)
        assert isinstance(hs, SomeLLAbstractVariable)
        assert hs.deepfrozen

    def test_propagate_fixing_across_func_arguments(self):
        def ll_func2(z):
            z = hint(z, concrete=True)
            return z + 1
        def ll_function(cond, x,y):
            if cond:
                z = x+y
            else:
                z = x-y
            z = ll_func2(z)
            return z
        hs, ha = self.hannotate(ll_function, [bool, int, int], annotator=True)
        assert hs.eager_concrete
        assert hs.concretetype == lltype.Signed
        ll_function_graph = graphof(ha.base_translator, ll_function)
        gdesc = ha.bookkeeper.getdesc(ll_function_graph)
        _, x_v, y_v = gdesc._cache[None].getargs()
        assert ha.binding(x_v).is_fixed()
        assert ha.binding(y_v).is_fixed()

    def test_hannotate_plus_minus(self):
        def ll_plus_minus(s, x, y):
            acc = x
            n = len(s)
            pc = 0
            while pc < n:
                op = s[pc]
                op = hint(op, concrete=True)
                if op == '+':
                    acc += y
                elif op == '-':
                    acc -= y
                pc += 1
            return acc
        assert ll_plus_minus("+-+", 0, 2) == 2
        self.hannotate(ll_plus_minus, [str, int, int])
        self.hannotate(ll_plus_minus, [str, int, int], inline=100000)

    def test_invalid_hint_1(self):
        S = self.make_struct('S', ('x', lltype.Signed))
        def ll_getitem_switch(s):
            n = s.x    # -> variable
            return hint(n, concrete=True)
        py.test.raises(HintError, self.hannotate,
                       ll_getitem_switch, [self.annotate_struct(S)])

    def undecided_relevance_test_invalid_hint_2(self):
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        def ll_getitem_switch(s):
            if s.x > 0:   # variable exitswitch
                sign = 1
            else:
                sign = -1
            return hint(sign, concrete=True)
        py.test.skip("in-progress: I think we expect a HintError here, do we?")
        py.test.raises(HintError, hannotate,
                       ll_getitem_switch, [annmodel.SomePtr(lltype.Ptr(S))])


    def test_raise_exc(self):
        class E(Exception):
            pass
        def f1():
            raise E
        self.hannotate(f1, [], policy=P_OOPSPEC_NOVIRTUAL)

        def f2():
            e = E()
            e.a = 3
            raise e
        self.hannotate(f2, [], policy=P_OOPSPEC_NOVIRTUAL)    


    def test_raise_and_catch_exc(self):
        class E(Exception):
            pass
        def f(flag):
            if flag:
                raise E

        def g(flag):
            try:
                f(flag)
            except E:
                return -1
            return 0

        hs = self.hannotate(g, [bool], policy=P_OOPSPEC_NOVIRTUAL)
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed

        def f(flag):
            if flag:
                e = E()
                e.a = 3
                raise e

        hs = self.hannotate(g, [bool], policy=P_OOPSPEC_NOVIRTUAL)    
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.concretetype == lltype.Signed    


    def test_more_green(self):
        def f(x):
            z = x + 1
            x2 = hint(x, concrete=True)
            return z

        hs = self.hannotate(f, [int])
        assert isinstance(hs, SomeLLAbstractConstant)
        assert hs.is_green()
        assert not hs.is_fixed()

    def test_blue_simple_meth(self):
        py.test.skip("with abstract containers this test explode in the cast_pointer annotation logic")
        class Base(object):

            def m(self):
                raise NotImplementedError

        class Concrete(Base):

            def m(self):
                return 42

        def f(flag):
            if flag:
                o = Base()
            else:
                o = Concrete()
            return o.m()

        hs = self.hannotate(f, [bool], policy=P_OOPSPEC)


    def test_simple_meth(self):
        class Base(object):
            def m(self):
                raise NotImplementedError
            pass  # for inspect.getsource() bugs

        class Concrete(Base):
            def m(self):
                return 42
            pass  # for inspect.getsource() bugs

        def f(flag):
            if flag:
                o = Base()
            else:
                o = Concrete()
            return o.m()

        hs = self.hannotate(f, [bool], policy=P_OOPSPEC_NOVIRTUAL)


    def test_green_isinstance(self):
        class Base(object):
            pass
        class Concrete(Base):
            pass

        def f(o):
            hint(o, concrete=True)
            return isinstance(o, Concrete)

        hs = self.hannotate(f, [Base], policy=P_OOPSPEC_NOVIRTUAL)
        assert hs.is_green()


    def test_cast_pointer_keeps_deepfreeze(self):

        class A(object):
            pass
        class B(A):
            pass

        def getinstance(n):
            if n:
                return A()
            else:
                return B()

        def ll_function(n):
            a = getinstance(n)
            a = hint(a, promote=True)
            a = hint(a, deepfreeze=True)

            if isinstance(a, B):
                return a
            return None

        hs = self.hannotate(ll_function, [int], policy=P_NOVIRTUAL)
        assert hs.deepfrozen


    def test_concrete_fnptr_for_green_call(self, setup=setup_for_indirect_call):
        def h1(n):
            return n * 10
        def h2(n):
            return n + 20
        call, lst = setup(h1, h2)

        def ll_function(n, m):
            h = hint(lst, deepfreeze=True)[m]
            res = call(h, n)
            hint(res, concrete=True)   # so 'h' gets green, so 'm' gets green
            return m

        hs = self.hannotate(ll_function, [int, int], policy=P_NOVIRTUAL)
        assert hs.is_green()

    def test_concrete_fnptr_for_green_call_oosend(self):
        self.test_concrete_fnptr_for_green_call(setup_for_oosend)

    def test_indirect_yellow_call(self, setup=setup_for_indirect_call):
        def h1(n):
            return 123
        def h2(n):
            return 456
        call, lst = setup(h1, h2)
        def ll_function(n, m):
            h = hint(lst, deepfreeze=True)[m]
            return call(h, n)

        hs = self.hannotate(ll_function, [int, int], policy=P_NOVIRTUAL)
        assert not hs.is_green()

    def test_indirect_yellow_call_oosend(self):
        self.test_indirect_yellow_call(setup_for_oosend)

    def test_indirect_sometimes_residual_pure_red_call(self, setup=setup_for_indirect_call):
        def h1(x):
            return x-2
        def h2(x):
            return x*4
        call, lst = setup(h1, h2)
        def f(n, x):
            frozenl = hint(lst, deepfreeze=True)
            h = frozenl[n&1]
            return call(h, x)

        P = StopAtXPolicy(h1)
        P.oopspec = True
        P.entrypoint_returns_red = False
        hs, hannotator = self.hannotate(f, [int, int], policy=P, annotator=True)
        assert not hs.is_green()
        assert isinstance(hs, SomeLLAbstractConstant)

        tsgraph = graphof(hannotator.translator, h2)
        hs = hannotator.binding(tsgraph.getargs()[0])
        assert not hs.is_green()

    def test_indirect_sometimes_residual_pure_red_call_oosend(self):
        self.test_indirect_sometimes_residual_pure_red_call(setup_for_oosend)

    def test_indirect_sometimes_residual_red_call(self, setup=setup_for_indirect_call):
        class Stuff:
            pass
        stuff = Stuff()
        def h1(x):
            stuff.hello = 123
            return x-2
        def h2(x):
            return x*4
        call, lst = setup(h1, h2)
        def f(n, x):
            frozenl = hint(lst, deepfreeze=True)
            h = frozenl[n&1]
            return call(h, x)

        P = StopAtXPolicy(h1)
        P.oopspec = True
        P.entrypoint_returns_red = False
        hs, hannotator = self.hannotate(f, [int, int], policy=P, annotator=True)
        assert not hs.is_green()

        tsgraph = graphof(hannotator.translator, h2)
        hs = hannotator.binding(tsgraph.getargs()[0])
        assert not hs.is_green()

    def test_indirect_sometimes_residual_red_call_oosend(self):
        self.test_indirect_sometimes_residual_red_call(setup_for_oosend)

    def test_indirect_sometimes_residual_pure_but_fixed_red_call(self, setup=setup_for_indirect_call):
        def h1(x):
            return x-2
        def h2(x):
            return x*4
        call, lst = setup(h1, h2)
        def f(n, x):
            frozenl = hint(lst, deepfreeze=True)
            h = frozenl[n&1]
            z = call(h, x)
            hint(z, concrete=True)
            return z

        P = StopAtXPolicy(h1)
        P.oopspec = True
        P.entrypoint_returns_red = False
        hs, hannotator = self.hannotate(f, [int, int], policy=P, annotator=True)
        assert hs.is_green()

        #tsgraph = graphof(hannotator.translator, h2)
        #hs = hannotator.binding(tsgraph.getargs()[0])
        #assert hs.is_green()

        tsgraph = graphof(hannotator.translator, f)
        hs = hannotator.binding(tsgraph.getargs()[0])
        assert hs.is_green()
        hs = hannotator.binding(tsgraph.getargs()[1])
        assert hs.is_green()

    def test_indirect_sometimes_residual_pure_but_fixed_red_call_oosend(self):
        self.test_indirect_sometimes_residual_pure_but_fixed_red_call(setup_for_oosend)
        
    def test_ignore_nonjitted_path(self):
        def f(n):
            if we_are_jitted():
                return 5
            else:
                return n
        hs = self.hannotate(f, [int])
        assert hs.is_green()

        def g(n):
            if not we_are_jitted():
                return n
            else:
                return 5
        hs = self.hannotate(g, [int])
        assert hs.is_green()

        def g(n):
            if not we_are_jitted():
                return n
            else:
                return 5
        hs = self.hannotate(g, [int], backendoptimize=True)
        assert hs.is_green()


    def test_substitute_graph(self):
        class MetaG:
            pass    # the details are only used by the timeshifter

        def g(m):
            return m * 17

        def f(n, m):
            x = g(n)
            y = g(m)
            hint(y, concrete=True)
            return g(m)

        class MyPolicy(HintAnnotatorPolicy):
            entrypoint_returns_red = False
            def look_inside_graph(self, graph):
                if graph.func is g:
                    return MetaG   # replaces g with a meta-call to metafunc()
                else:
                    return True

        hs, hannotator = self.hannotate(f, [int, int], policy=MyPolicy(),
                                   annotator=True)
        assert hs.is_green()
        for graph in hannotator.translator.graphs:
            assert 'int_mul' not in flowmodel.summary(graph)

    def test_strange_green_result_after_red_switch(self):
        py.test.skip("is this right?")
        class LinkedRules(object):
            _immutable_ = True
            def __init__(self, data, next=None):
                self.data = data
                self.next = next

            def find_applicable_rule(self, query):
                # self is green, query isn't
                # should the result really be green?
                while self:
                    data = self.data
                    hint(data, concrete=True)
                    j = 0
                    if self.data == query:
                        return self
                    self = self.next
                return None

        chain = LinkedRules(1, LinkedRules(2, LinkedRules(0)))
        def f(x):
            rulechain = chain.find_applicable_rule(x)
            return rulechain
        hs = self.hannotate(f, [int], policy=P_OOPSPEC_NOVIRTUAL)
        assert isinstance(hs, SomeLLAbstractVariable)

    def test_manual_marking_of_pure_functions(self):
        d = {}
        def h1(s):
            try:
                return d[s]
            except KeyError:
                d[s] = r = hash(s)
                return r
        h1._pure_function_ = True
        def f(n):
            hint(n, concrete=True)
            if n == 0:
                s = "abc"
            else:
                s = "123"
            a = h1(s)
            return a

        P = StopAtXPolicy(h1)
        P.oopspec = True
        P.entrypoint_returns_red = False
        hs = self.hannotate(f, [int], policy=P)
        assert hs.is_green()

class TestLLType(BaseAnnotatorTest):
    type_system = 'lltype'

    malloc = property(lambda self: lltype.malloc)
    
    def make_struct(self, name, *fields, **kwds):
        return lltype.GcStruct(name, *fields, **kwds)

    def annotate_struct(self, S):
        return annmodel.SomePtr(lltype.Ptr(S))

    def test_simple_cast_pointer(self):
        GCS1 = lltype.GcStruct('s1', ('x', lltype.Signed))
        GCS2 = lltype.GcStruct('s2', ('sub', GCS1), ('y', lltype.Signed))
        PGCS1 = lltype.Ptr(GCS1)
        PGCS2 = lltype.Ptr(GCS2)
        def ll1():
            s2 = lltype.malloc(GCS2)
            return lltype.cast_pointer(PGCS1, s2)
        hs = self.hannotate(ll1, [])
        assert isinstance(hs, SomeLLAbstractContainer)
        assert hs.concretetype == PGCS1
        def ll1():
            s2 = lltype.malloc(GCS2)
            s1 = s2.sub
            return lltype.cast_pointer(PGCS2, s1)
        hs = self.hannotate(ll1, [])
        assert isinstance(hs, SomeLLAbstractContainer)
        assert hs.concretetype == PGCS2

    def test_getarrayitem(self):
        A = lltype.GcArray(lltype.Signed, hints={'immutable': True})
        a = lltype.malloc(A, 10)
        def ll1(n):
            v = a[n]
            v = hint(v, concrete=True)
            return v
        hs, ha = self.hannotate(ll1, [int], annotator=True)
        assert hs.eager_concrete
        g1 = graphof(ha.translator, ll1)
        hs_n = ha.binding(g1.getargs()[0])
        assert hs_n.origins.keys()[0].fixed

    def test_getvarrayitem(self):
        A = lltype.GcArray(lltype.Signed, hints={'immutable': True})
        def ll1(n):
            a = lltype.malloc(A, 10)
            v = a[n]
            v = hint(v, concrete=True)
            return v
        hs, ha = self.hannotate(ll1, [int], annotator=True)
        assert hs.eager_concrete
        g1 = graphof(ha.translator, ll1)
        hs_n = ha.binding(g1.getargs()[0])
        assert hs_n.origins.keys()[0].fixed

    def test_degenerated_merge_substructure(self):
        S = lltype.GcStruct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            s = lltype.malloc(S)
            s.n = 4
            if flag:
                s = t.s
            return s, t
        hs = self.hannotate(ll_function, [bool])
        assert isinstance(hs, SomeLLAbstractContainer)
        assert not hs.contentdef.degenerated
        assert len(hs.contentdef.fields) == 2
        hs0 = hs.contentdef.fields['item0'].s_value       # 's'
        assert isinstance(hs0, SomeLLAbstractContainer)
        assert hs0.contentdef.degenerated
        hs1 = hs.contentdef.fields['item1'].s_value       # 't'
        assert isinstance(hs1, SomeLLAbstractContainer)
        assert hs1.contentdef.degenerated

    def test_degenerated_merge_cross_substructure(self):
        py.test.skip("no longer a valid test")
        from pypy.rlib import objectmodel
        S = lltype.Struct('S', ('n', lltype.Signed))
        T = lltype.GcStruct('T', ('s', S), ('s1', S), ('n', lltype.Float))

        def ll_function(flag):
            t = lltype.malloc(T)
            t.s.n = 3
            t.s1.n = 3
            if flag:
                s = t.s
            else:
                s = t.s1
            objectmodel.keepalive_until_here(t)
            return s, t
        hs = self.hannotate(ll_function, [bool])    
        assert isinstance(hs, SomeLLAbstractContainer)
        assert not hs.contentdef.degenerated
        assert len(hs.contentdef.fields) == 2
        hs0 = hs.contentdef.fields['item0'].s_value       # 's'
        assert isinstance(hs0, SomeLLAbstractContainer)
        assert hs0.contentdef.degenerated
        hs1 = hs.contentdef.fields['item1'].s_value       # 't'
        assert isinstance(hs1, SomeLLAbstractContainer)
        assert hs1.contentdef.degenerated

    def test_cast_ptr_to_int(self):
        GCS1 = lltype.GcStruct('s1', ('x', lltype.Signed))
        def f():
            p = lltype.malloc(GCS1)
            return lltype.cast_ptr_to_int(p)

        hs = self.hannotate(f, [], policy=P_NOVIRTUAL)
        assert not hs.is_green()


class TestOOType(BaseAnnotatorTest):
    type_system = 'ootype'

    malloc = property(lambda self: ootype.new)

    def make_struct(self, name, *fields, **kwds):
        fields = dict(fields)
        hints = kwds.pop('hints', None)
        if hints:
            kwds['_hints'] = hints
        return ootype.Instance(name, ootype.ROOT, fields, **kwds)

    def annotate_struct(self, S):
        return annmodel.SomeOOInstance(S)

    def skip_policy(self):
        py.test.skip('fixme? (This policy is not relevant for now)')

    test_simple_list_operations = skip_policy
    test_some_more_list_operations = skip_policy
    test_make_a_list = skip_policy
    test_simple_struct_malloc = skip_policy
    test_container_union = skip_policy
    test_specialize_deepfreeze_calls = skip_policy
    test_deepfreeze_variables = skip_policy
    test_cast_pointer_keeps_deepfreeze = skip_policy

    def test_void_oosend(self):
        class Foo:
            def bar(self):
                pass

        def fn():
            f = Foo()
            f.bar()
        hs = self.hannotate(fn, [], policy=P_OOPSPEC_NOVIRTUAL)

    def test_simple_method_call_var(self):
        py.test.skip('fixme!')
