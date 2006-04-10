from pypy.conftest import gettestobjspace

class AppTest_FD(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_instantiate(self):
        fd = FiniteDomain([1, 2, 3])
        assert fd.size() == 3
        assert set(fd.get_values()) == set([1, 2, 3])

    def test_copy(self):
        fd = FiniteDomain([1, 2, 3])
        clone = fd.copy()
        assert set(clone.get_values()) == set([1, 2, 3])

    def test_remove_value(self):
        fd = FiniteDomain([1, 2, 3])
        fd.remove_value(2)
        assert fd.size() == 2
        assert set(fd.get_values()) == set([1, 3])
        assert fd.has_changed()

    def test_remove_all_values(self):
        fd = FiniteDomain([3])
        # FIXME: check this is a ConsistencyFailure
        raises(Exception, fd.remove_value, 3) 
        
    def test_remove_values(self):
        fd = FiniteDomain([1, 2, 3])
        fd.remove_values([1, 2])
        assert fd.size() == 1
        assert set(fd.get_values()) == set([3,])
        assert fd.has_changed()

    def test_remove_values_empty_list(self):
        fd = FiniteDomain([1, 2, 3])
        assert not(fd.has_changed())
        fd.remove_values([])
        assert fd.size() == 3
        assert not(fd.has_changed())


    def notest_logical_variable_in_domain(self):
        '''Logical variables do not play well with sets, skip for now'''
        X = newvar()
        fd = FiniteDomain([X, 2])
        assert fd.size() == 2
        unify(X,42)
        fd.remove_value(42) 
        assert fd.size() == 1
        assert fd.has_changed()

    def test_intersection(self):
        """not used for now"""
        fd1 = FiniteDomain([1, 2, 3])
        fd2 = FiniteDomain([2, 3, 4])
        assert intersection(fd1, fd2) == FiniteDomain([2, 3])
        assert intersection(fd2, fd1) == FiniteDomain([3, 2])
