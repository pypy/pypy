#import pypy.module.unipycation.engine as eng
import pytest

class AppTestEngine(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_basic(self):
        import unipycation as u

        e = u.Engine("f(666).")
        X = u.Var()
        t = u.Term('f', [X])
        sol = e.query_single(t, [X])

        assert sol[X] == 666

    def test_anonymous(self):
        import unipycation
        pass

    def test_tautology(self):
        import unipycation
        pass

    def test_false(self):
        import unipycation
        pass

    def test_iterator(self):
        import unipycation
        pass

    def test_iterator_no_result(self):
        import unipycation
        pass

    def test_iterator_tautology(self):
        import unipycation
        pass

    def test_iterator_infty(self):
        import unipycation
        pass

    def test_iter_nonexisting_predicate(self):
        import unipycation
        pass

    def test_query_nonexisting_predicate(self):
        import unipycation
        pass
