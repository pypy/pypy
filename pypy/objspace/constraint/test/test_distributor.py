from pypy.conftest import gettestobjspace


class AppTest_Distributor(object):
    
    def setup_class(cls):
        cls.space = gettestobjspace('logic')

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
        assert spc.dom(y) == FiniteDomain([2])
