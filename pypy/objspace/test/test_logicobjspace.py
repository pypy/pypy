from pypy.conftest import gettestobjspace

class AppTest_Logic(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_simple_bind(self):
        X = newvar()
        assert is_free(X)
        bind(X, 1)
        assert type(X) == int
        assert is_bound(X)
        assert is_bound(1)
        raises(TypeError, bind, 1, 2)

    def test_setitem_bind(self):
        x = newvar()
        d = {5: x}
        d[6] = x
        d[7] = []
        d[7].append(x)
        y = d[5], d[6], d.values(), d.items()
        for x in [d[5], d[6], d[7][0]]:
            assert is_free(d[5])
        bind(x, 1)
        for x in [d[5], d[6], d[7][0]]:
            assert is_bound(d[5])

    def test_bind_to_self(self):
        X = newvar()
        assert is_free(X)
        bind(X, X)
        bind(X, 1)
        assert X == 1

    def test_bind_aliased(self):
        X = newvar()
        Y = newvar()
        bind(X, Y)
        bind(X, 1)
        assert X == 1
        assert Y == 1

    def test_unbound_unification_long(self):
        l = [newvar() for i in range(40)]
        for i in range(39):
            bind(l[i], l[i + 1])
        bind(l[20], 1)
        for i in range(40):
            assert l[i] == 1

    def test_use_unbound_var(self):
        X = newvar()
        def f(x):
            return x + 1
        raises(RuntimeError, f, X)


    def test_eq_unifies_simple(self):
        X = newvar()
        Y = newvar()
        unify(X, Y)
        unify(X, 1)
        assert X == 1
        assert is_bound(Y)
        assert Y == 1
        assert X == Y

    def test_ne_of_unified_unbound_vars(self):
        X = newvar()
        Y = newvar()
        unify(X, Y)
        assert X == Y
        assert not X != Y

    def test_cmp(self):
        X = newvar()
        Y = newvar()
        unify(X, Y)
        assert cmp(X, Y) == 0
        assert is_free(X)
        assert is_free(Y)
        unify(X, 1)
        assert X == 1
        assert is_bound(Y)
        assert Y == 1

    def test_is(self):
        X = newvar()
        x = 1
        assert 1 is 1
        assert not(2 is 1)
        assert X is X
        bind(X, x)
        assert X == 1
        assert X is x
        assert not(X is 2)

    def test_unify_free(self):
        X, Y = newvar(), newvar()
        unify(X, Y)
        assert X == Y
        unify(X, 1)
        assert X == 1
        assert Y == 1
        
        

class AppTest_LogicThreads(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')


    def notest_eager_producer_consummer(self):

        def generate(n, limit):
            print "generate", n, limit
            if n < limit:
                return (n, generate(n + 1, limit))
            return (None, None)

        def sum(L, a):
            print "sum", a
            head, Tail = newvar(), newvar()
            unify(L, (head, Tail))
            if head != None:
                return sum(Tail, head + a)
            return a

        X = newvar()
        S = newvar()
        unify(S, uthread(sum, X, 0))
        unify(X, uthread(generate, 0, 10))

        assert S == 45


    def notest_lazy_producer_consummer(self):

        def lgenerate(n, L):
            """wait-needed version of generate"""
            print "generator waits on L being needed"
            wait_needed(L)
            Tail = newvar()
            L == (n, Tail)
            print "generator bound L to", L
            lgenerate(n+1, Tail)

        def lsum(L, a, limit):
            """this version of sum controls the generator"""
            print "sum", a
            if limit > 0:
                Head, Tail = newvar(), newvar()
                print "sum waiting on L"
                L == (Head, Tail) # or Head, Tail == L ?
                return lsum(Tail, a+Head, limit-1)
            else:
                return a

        print "lazy producer consummer"
        print "before"
        Y = newvar()
        T = newvar()
        uthread(lgenerate, 0, Y)
        T == uthread(lsum, Y, 0, 10)
        print "after"

        print T
