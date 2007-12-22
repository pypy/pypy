import py
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.backendopt.all import INLINE_THRESHOLD_FOR_TEST
from pypy.translator.backendopt.support import md5digest
from pypy.translator.backendopt.test.test_malloc import TestLLTypeMallocRemoval as LLTypeMallocRemovalTest
from pypy.translator.backendopt.test.test_malloc import TestOOTypeMallocRemoval as OOTypeMallocRemovalTest
from pypy.translator.translator import TranslationContext, graphof
from pypy.objspace.flow.model import Constant
from pypy.annotation import model as annmodel
from pypy.rpython.llinterp import LLInterpreter
from pypy.rlib.rarithmetic import intmask
from pypy import conftest

class A:
    def __init__(self, x, y):
        self.bounds = (x, y)
    def mean(self, percentage=50):
        x, y = self.bounds
        total = x*percentage + y*(100-percentage)
        return total//100

def condition(n):
    return n >= 100

def firstthat(function, condition):
    for n in range(101):
        if condition(function(n)):
            return n
    else:
        return -1

def myfunction(n):
    a = A(117, n)
    return a.mean()

def big():
    """This example should be turned into a simple 'while' loop with no
    malloc nor direct_call by back-end optimizations, given a high enough
    inlining threshold.
    """
    return firstthat(myfunction, condition)

LARGE_THRESHOLD  = 10*INLINE_THRESHOLD_FOR_TEST
HUGE_THRESHOLD  = 100*INLINE_THRESHOLD_FOR_TEST

class BaseTester(object):
    type_system = None

    def translateopt(self, func, sig, **optflags):
        t = TranslationContext()
        t.buildannotator().build_types(func, sig)
        t.buildrtyper(type_system=self.type_system).specialize()
        if conftest.option.view:
            t.view()
        backend_optimizations(t, **optflags)
        if conftest.option.view:
            t.view()
        return t

    def test_big(self):
        assert big() == 83

        t = self.translateopt(big, [], inline_threshold=HUGE_THRESHOLD,
                              mallocs=True) 

        big_graph = graphof(t, big)
        self.check_malloc_removed(big_graph)

        interp = LLInterpreter(t.rtyper)
        res = interp.eval_graph(big_graph, [])
        assert res == 83


    def test_for_loop(self):
        def f(n):
            total = 0
            for i in range(n):
                total += i
            return total

        t  = self.translateopt(f, [int], mallocs=True)
        # this also checks that the BASE_INLINE_THRESHOLD is enough
        # for 'for' loops

        f_graph = graph = graphof(t, f)
        self.check_malloc_removed(f_graph)

        interp = LLInterpreter(t.rtyper)
        res = interp.eval_graph(f_graph, [11])
        assert res == 55

    def test_premature_death(self):
        import os
        from pypy.annotation.listdef import s_list_of_strings

        inputtypes = [s_list_of_strings]

        def debug(msg):
            os.write(2, "debug: " + msg + '\n')

        def entry_point(argv):
            #debug("entry point starting")
            for arg in argv:
                #debug(" argv -> " + arg)
                r = arg.replace('_', '-')
                #debug(' replaced -> ' + r)
                a = r.lower()
                #debug(" lowered -> " + a)
            return 0

        t  = self.translateopt(entry_point, inputtypes, mallocs=True)

        entry_point_graph = graphof(t, entry_point)

        argv = t.rtyper.getrepr(inputtypes[0]).convert_const(['./pypy-c'])

        interp = LLInterpreter(t.rtyper)
        interp.eval_graph(entry_point_graph, [argv])


    def test_idempotent(self):
        def s(x):
            res = 0
            i = 1
            while i <= x:
                res += i
                i += 1
            return res

        def g(x):
            return s(100) + s(1) + x 

        def idempotent(n1, n2):
            c = [i for i in range(n2)]
            return 33 + big() + g(10)

        t  = self.translateopt(idempotent, [int, int],
                               raisingop2direct_call=True,
                               constfold=False)
        #backend_optimizations(t, raisingop2direct_call=True,
        #                      inline_threshold=0, constfold=False)

        digest1 = md5digest(t)

        digest2 = md5digest(t)
        def compare(digest1, digest2):
            diffs = []
            assert digest1.keys() == digest2.keys()
            for name in digest1:
                if digest1[name] != digest2[name]:
                    diffs.append(name)
            assert not diffs

        compare(digest1, digest2)

        #XXX Inlining and constfold are currently non-idempotent.
        #    Maybe they just renames variables but the graph changes in some way.
        backend_optimizations(t, raisingop2direct_call=True,
                              inline_threshold=0, constfold=False)
        digest3 = md5digest(t)
        compare(digest1, digest3)

    def test_bug_inlined_if(self):
        def f(x, flag):
            if flag:
                y = x
            else:
                y = x+1
            return y*5
        def myfunc(x):
            return f(x, False) - f(x, True)

        assert myfunc(10) == 5

        t = self.translateopt(myfunc, [int], inline_threshold=HUGE_THRESHOLD)
        interp = LLInterpreter(t.rtyper)
        res = interp.eval_graph(graphof(t, myfunc), [10])
        assert res == 5

    def test_range_iter(self):
        def fn(start, stop, step):
            res = 0
            if step == 0:
                if stop >= start:
                    r = range(start, stop, 1)
                else:
                    r = range(start, stop, -1)
            else:
                r = range(start, stop, step)
            for i in r:
                res = res * 51 + i
            return res
        t = self.translateopt(fn, [int, int, int], merge_if_blocks=True)
        interp = LLInterpreter(t.rtyper)
        for args in [2, 7, 0], [7, 2, 0], [10, 50, 7], [50, -10, -3]:
            assert interp.eval_graph(graphof(t, fn), args) == intmask(fn(*args))

    def test_constant_diffuse(self):
        def g(x,y):
            if x < 0:
                return 0
            return x + y

        def f(x):
            return g(x,7)+g(x,11)

        t = self.translateopt(f, [int])
        fgraph = graphof(t, f)

        for link in fgraph.iterlinks():
            assert Constant(7) not in link.args
            assert Constant(11) not in link.args

class TestLLType(BaseTester):
    type_system = 'lltype'
    check_malloc_removed = LLTypeMallocRemovalTest.check_malloc_removed

    def test_list_comp(self):
        def f(n1, n2):
            c = [i for i in range(n2)]
            return 33

        t  = self.translateopt(f, [int, int], inline_threshold=LARGE_THRESHOLD,
                               mallocs=True)

        f_graph = graphof(t, f)
        self.check_malloc_removed(f_graph)

        interp = LLInterpreter(t.rtyper)
        res = interp.eval_graph(f_graph, [11, 22])
        assert res == 33

    def test_secondary_backendopt(self):
        # checks an issue with a newly added graph that calls an
        # already-exception-transformed graph.  This can occur e.g.
        # from a late-seen destructor added by the GC transformer
        # which ends up calling existing code.
        def common(n):
            if n > 5:
                raise ValueError
        def main(n):
            common(n)
        def later(n):
            try:
                common(n)
                return 0
            except ValueError:
                return 1

        t = TranslationContext()
        t.buildannotator().build_types(main, [int])
        t.buildrtyper(type_system='lltype').specialize()
        exctransformer = t.getexceptiontransformer()
        exctransformer.create_exception_handling(graphof(t, common))
        from pypy.annotation import model as annmodel
        from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
        annhelper = MixLevelHelperAnnotator(t.rtyper)
        later_graph = annhelper.getgraph(later, [annmodel.SomeInteger()],
                                         annmodel.SomeInteger())
        annhelper.finish()
        annhelper.backend_optimize()
        # ^^^ as the inliner can't handle exception-transformed graphs,
        # this should *not* inline common() into later().
        if conftest.option.view:
            later_graph.show()
        common_graph = graphof(t, common)
        found = False
        for block in later_graph.iterblocks():
            for op in block.operations:
                if (op.opname == 'direct_call' and
                    op.args[0].value._obj.graph is common_graph):
                    found = True
        assert found, "cannot find the call (buggily inlined?)"
        from pypy.rpython.llinterp import LLInterpreter
        llinterp = LLInterpreter(t.rtyper)
        res = llinterp.eval_graph(later_graph, [10])
        assert res == 1


class TestOOType(BaseTester):
    type_system = 'ootype'
    check_malloc_removed = OOTypeMallocRemovalTest.check_malloc_removed
    
