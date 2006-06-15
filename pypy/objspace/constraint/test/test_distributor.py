from pypy.conftest import gettestobjspace


class AppTest_Distributor(object):
    
    def setup_class(cls):
        cls.space = gettestobjspace('logic', usemodules=('_stackless', ))

    def test_instantiate(self):
        d1 = NaiveDistributor()
        d2 = SplitDistributor(4)
        d3 = DichotomyDistributor()
        assert d1.fanout() == 2
        assert d2.fanout() == 4
        assert d3.fanout() == 2
    
    def test_naive_distribute(self):
        spc = newspace()
        x = spc.var('x', FiniteDomain([1]))
        y = spc.var('y', FiniteDomain([1, 2]))
        z = spc.var('z', FiniteDomain([1, 2, 3]))
        d = NaiveDistributor()
        d.distribute(spc, 2)
        skip("XXX fix this test?")
        assert spc.dom(y) == FiniteDomain([2])
        d.distribute(spc, 1)
        assert spc.dom(y) == FiniteDomain([2])
        assert spc.dom(z) == FiniteDomain([1])
        

    def test_split_distributor(self):
        spc = newspace()
        x = spc.var('x', FiniteDomain([1]))
        y = spc.var('y', FiniteDomain([1, 2]))
        z = spc.var('z', FiniteDomain([1, 2, 3]))
        w = spc.var('w', FiniteDomain([1, 2, 3, 4, 5, 6]))
        d = SplitDistributor(3)
        d.distribute(spc, 2)
        assert spc.dom(y).size() == 1
        d.distribute(spc, 1)
        assert spc.dom(z).size() == 1
        d.distribute(spc, 3)
        assert spc.dom(w).size() == 2
