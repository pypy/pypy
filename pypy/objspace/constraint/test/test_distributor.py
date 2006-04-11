from pypy.conftest import gettestobjspace


class AppTest_Distributor(object):
    
    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_instantiate(self):
        d1 = NaiveDistributor()
        d2 = SplitDistributor(4)
        d3 = DichotomyDistributor()

        
