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

    def test_from_file(self):
        import unipycation as u
        import os, tempfile as t

        (fd, fname) = t.mkstemp(prefix="unipycation-")
        os.write(fd, "f(1,2,3).")
        os.close(fd)

        e = u.Engine.from_file(fname)
        os.unlink(fname)

        vs = [X, Y, Z] = [ u.Var() for x in range(3) ]

        t = u.Term('f', vs)
        sol = e.query_single(t, vs)

        assert sol[X] == 1
        assert sol[Y] == 2
        assert sol[Z] == 3

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

    def test_tautology(self):
        import unipycation as u

        e = u.Engine("eat(cheese, bread). eat(egg, salad).")

        t = u.Term('eat', ['cheese', 'bread'])
        sol = e.query_single(t, [])

        assert sol == {}

    def test_contradicion(self):
        import unipycation as u

        e = u.Engine("eat(cheese, bread). eat(egg, salad).")
        t = u.Term('eat', ['cheese', 'egg'])
        raises(StopIteration, lambda : e.query_single(t, []))

    def test_iterator_tautology(self):
        import unipycation as u

        e = u.Engine("eat(cheese, bread). eat(egg, salad).")
        t = u.Term('eat', ['cheese', 'bread'])
        it = e.query_iter(t, [])
        sols = [ x for x in it ]
        assert sols == [{}]

    def test_iterator_contradiction(self):
        import unipycation as u

        e = u.Engine("eat(cheese, bread). eat(egg, salad).")
        t = u.Term('eat', ['cheese', 'egg'])
        it = e.query_iter(t, [])
        raises(StopIteration, lambda : it.next())

    def test_iterator_infty(self):
        import unipycation as u

        e = u.Engine("""
                f(0).
                f(X) :- f(X0), X is X0 + 1.
        """)

        X = u.Var()
        t = u.Term('f', [X])
        it = e.query_iter(t, [X])

        first_ten = []
        for i in range(10):
            first_ten.append(it.next()[X])

        assert first_ten == range(0, 10)

    def test_query_nonexisting_predicate(self):
        import unipycation as u

        e = u.Engine("f(666). f(667). f(668).")
        X = u.Var()
        t = u.Term("g", [X])

        raises(u.GoalError, lambda: e.query_single(t, [X]))

    def test_iter_nonexisting_predicate(self):
        import unipycation as u

        e = u.Engine("f(666). f(667). f(668).")
        X = u.Var()
        t = u.Term("g", [X])

        raises(u.GoalError, lambda: e.query_iter(t, [X]).next())

    def test_parse_db_incomplete(self):
        import unipycation

        raises(unipycation.ParseError, lambda: unipycation.Engine("f(1)")) # missing dot on db
