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

    def test_iterator(self):
        import unipycation as u

        e = u.Engine("f(666, 667). f(222, 334). f(777, 778).")
        vs = [X, Y] = [u.Var(), u.Var()]

        t = u.Term('f', vs)
        it = e.query_iter(t, vs)

        s1 = it.next()
        s2 = it.next()
        s3 = it.next()

        assert(s1[X] == 666 and s1[Y] == 667)
        assert(s2[X] == 222 and s2[Y] == 334)
        assert(s3[X] == 777 and s3[Y] == 778)
        raises(StopIteration, lambda: it.next())

    def test_functors(self):
        import unipycation as u

        e = u.Engine("f(a(1, 2), b(3, 4)).")
        vs = [X, Y] = [u.Var(), u.Var()]

        t1 = u.Term('a', [1, X])
        t = u.Term('f', [t1, Y])

        sol = e.query_single(t, vs)
        expect_y = u.Term('b', [3, 4])
        not_expect_y = u.Term('zzz', ["oh", "no"])

        assert sol[X] == 2
        assert sol[Y]  == expect_y
        assert sol[Y] != not_expect_y # inequal terms
        assert sol[Y] != 1337         # term vs. number

    def test_anonymous(self):
        import unipycation
        pass

    def test_tautology(self):
        import unipycation
        pass

    def test_false(self):
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
