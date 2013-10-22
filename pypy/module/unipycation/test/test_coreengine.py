#import pypy.module.unipycation.engine as eng
import tempfile
import pytest

class AppTestCoreEngine(object):
    spaceconfig = dict(usemodules=('unipycation', ))

    def setup_class(cls):
        space = cls.space
        (fd, fname) = tempfile.mkstemp(prefix="unipycation-")
        cls.w_fd = space.wrap(fd)
        cls.w_fname = space.wrap(fname)

    def test_basic(self):
        import unipycation as u

        e = u.CoreEngine("f(666).")
        X = u.Var()
        t = u.CoreTerm('f', [X])
        sol = e.query_single(t, [X])

        assert sol[X] == 666

    def test_from_file(self):
        import unipycation as u
        import os
        fd = self.fd
        fname = self.fname

        os.write(fd, "f(1,2,3).")
        os.fsync(fd)

        e = u.CoreEngine.from_file(fname)

        vs = [X, Y, Z] = [ u.Var() for x in range(3) ]

        t = u.CoreTerm('f', vs)
        sol = e.query_single(t, vs)

        assert sol[X] == 1
        assert sol[Y] == 2
        assert sol[Z] == 3

        # check parse error has file information
        os.write(fd, "\nf(1,2,3).\nf(1 + + - ^")
        os.close(fd)

        info = raises(u.ParseError, u.CoreEngine.from_file, fname)
        assert fname in str(info.value)
        os.unlink(fname)


    def test_from_file_nul(self):
        import unipycation
        raises(TypeError, unipycation.CoreEngine.from_file, "a\x00")

    def test_iterator(self):
        import unipycation as u

        e = u.CoreEngine("f(666, 667). f(222, 334). f(777, 778).")
        vs = [X, Y] = [u.Var(), u.Var()]

        t = u.CoreTerm('f', vs)
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

        e = u.CoreEngine("f(a(1, 2), b(3, 4)).")
        vs = [X, Y] = [u.Var(), u.Var()]

        t1 = u.CoreTerm('a', [1, X])
        t = u.CoreTerm('f', [t1, Y])

        sol = e.query_single(t, vs)
        expect_y = u.CoreTerm('b', [3, 4])
        not_expect_y = u.CoreTerm('zzz', ["oh", "no"])

        assert sol[X] == 2
        assert sol[Y]  == expect_y
        assert sol[Y] != not_expect_y # inequal terms
        assert sol[Y] != 1337         # term vs. number

    def test_tautology(self):
        import unipycation as u

        e = u.CoreEngine("eat(cheese, bread). eat(egg, salad).")

        t = u.CoreTerm('eat', ['cheese', 'bread'])
        sol = e.query_single(t, [])

        assert len(sol) == 0

    def test_contradicion(self):
        import unipycation as u

        e = u.CoreEngine("eat(cheese, bread). eat(egg, salad).")
        t = u.CoreTerm('eat', ['cheese', 'egg'])
        res = e.query_single(t, [])
        assert res is None

    def test_iterator_tautology(self):
        import unipycation as u

        e = u.CoreEngine("eat(cheese, bread). eat(egg, salad).")
        t = u.CoreTerm('eat', ['cheese', 'bread'])
        it = e.query_iter(t, [])
        sols = [ x for x in it ]
        sol, = sols
        assert len(sol) == 0

    def test_iterator_contradiction(self):
        import unipycation as u

        e = u.CoreEngine("eat(cheese, bread). eat(egg, salad).")
        t = u.CoreTerm('eat', ['cheese', 'egg'])
        it = e.query_iter(t, [])
        raises(StopIteration, lambda : it.next())

    def test_iterator_infty(self):
        import unipycation as u

        e = u.CoreEngine("""
                f(0).
                f(X) :- f(X0), X is X0 + 1.
        """)

        X = u.Var()
        t = u.CoreTerm('f', [X])
        it = e.query_iter(t, [X])

        first_ten = []
        for i in range(10):
            first_ten.append(it.next()[X])

        assert first_ten == range(0, 10)

    def test_query_nonexisting_predicate(self):
        import unipycation as u

        e = u.CoreEngine("f(666). f(667). f(668).")
        X = u.Var()
        t = u.CoreTerm("g", [X])

        raises(u.PrologError, lambda: e.query_single(t, [X]))

    def test_iter_nonexisting_predicate(self):
        import unipycation as u

        e = u.CoreEngine("f(666). f(667). f(668).")
        X = u.Var()
        t = u.CoreTerm("g", [X])

        raises(u.PrologError, lambda: e.query_iter(t, [X]).next())

    def test_parse_db_incomplete(self):
        import unipycation

        raises(unipycation.ParseError, lambda: unipycation.CoreEngine("f(1)")) # missing dot on db

    def test_types_query(self):
        import unipycation

        e = unipycation.CoreEngine("eat(cheese, bread). eat(egg, salad).")
        v = unipycation.Var()
        raises(TypeError, lambda : e.query_single(v, []))

    def test_types_query2(self):
        import unipycation

        e = unipycation.CoreEngine("eat(cheese, bread). eat(egg, salad).")
        t = unipycation.CoreTerm('eat', ['cheese', 'bread'])
        raises(TypeError, lambda : e.query_single(t, [t]))

    def test_type_error_passed_up(self):
        import unipycation

        e = unipycation.CoreEngine("test(X) :- X is unlikely_to_ever_exist_ever(9).")
        X = unipycation.Var()
        t = unipycation.CoreTerm('test', [X])
        raises(unipycation.PrologError, lambda : e.query_single(t, [X]))

    # (Pdb) p exc
    # Generic1(error, [Generic2(existence_error, [Atom('procedure'), Generic2(/, [Atom('select'), Number(3)])])])
    # This does not belong here XXX
    def test_select(self):
        import uni

        e = uni.Engine("f(X) :- select(1, [1,2,3], X).")
        (res, ) = e.db.f(None)
        assert res == [2, 3]

    def test_variable_sharing_bug(self):
        import unipycation as u

        e = u.CoreEngine("f(1). g(2).")
        X = u.Var()
        t = u.CoreTerm('f', [X])
        sol = e.query_single(t, [X])
        assert sol[X] == 1

        t = u.CoreTerm('g', [X])
        sol = e.query_single(t, [X])
        assert sol == None # because X retains it's binding of 1

    def test_unbound(self):
        import unipycation as u

        e = u.CoreEngine("f(X) :- X = g(_).")
        X = u.Var()
        t = u.CoreTerm('f', [X])
        sol = e.query_single(t, [X])
        assert type(sol[X] == u.CoreTerm)
        assert len(sol[X].args) == 1
        assert type(sol[X].args[0] == u.Var)

    def test_error_in_database(self):
        import unipycation
        raises(unipycation.PrologError, 'unipycation.CoreEngine(":- foo, !.")')

