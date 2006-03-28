from pypy.conftest import gettestobjspace

class UnificationFailure(Exception):  pass

class AppTest_Logic(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_bind_var_val(self):
        X = newvar()
        assert is_free(X)
        assert not is_bound(X)
        bind(X, 1)
        assert X == 1
        assert not is_free(X)
        assert is_bound(X)
        assert is_bound(1)
        # FIXME : propagate proper
        #         FailureException
        raises(Exception, bind, X, 2)

    def test_bind_to_self(self):
        X = newvar()
        assert is_free(X)
        bind(X, X)
        assert is_free(X)
        assert alias_of(X, X)
        bind(X, 1)
        assert X == 1

    def test_unify_to_self(self):
        X = newvar()
        assert is_free(X)
        unify(X, X)
        assert is_free(X)
        assert alias_of(X, X)
        unify(X, 1)
        assert X == 1

    def test_unify_circular(self):
        X, Y = newvar(), newvar()
        unify(X, [Y])
        unify(Y, [X])
        assert X == [Y]
        assert Y == [X]

    def test_unify_alias(self):
        X = newvar()
        Y = newvar()
        unify(X, Y)
        assert alias_of(X, Y)
        assert alias_of(X, Y)
        unify(X, 1)
        # what about is_alias, then ?
        assert X == 1
        assert Y == 1

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
        Y = newvar()
        x = 1
        assert 1 is 1
        assert not(2 is 1)
        assert X is X
        assert X is X
        bind(X, x)
        bind(Y, X)
        assert X is 1
        assert 1 is X
        assert Y is X
        assert X is X
        assert X is x
        assert not(X is 2)

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

    def test_merge_aliases(self):
        X, Y = newvar(), newvar()
        Z, W = newvar(), newvar()
        unify(X, Y)
        assert alias_of(X, Y)
        assert alias_of(Y, X)
        unify(Z, W)
        assert alias_of(Z, W)
        assert alias_of(W, Z)
        unify(X, W)
        vars_ = [X, Y, Z, W]
        for V1 in vars_:
            assert is_free(V1)
            assert is_aliased(V1)
            for V2 in vars_:
                assert alias_of(V1, V2)
        unify(Y, 42)
        for V in vars_:
            assert V == 42

    def test_big_alias(self):
        l = [newvar() for i in range(20)]
        for i in range(19):
            bind(l[i], l[i+1])
        for i in range(19):
            assert alias_of(l[i], l[i+1])
        bind(l[10], 1)
        for i in range(20):
            assert l[i] == 1

    def test_use_unbound_var(self):
        X = newvar()
        def f(x):
            return x + 1
        raises(RuntimeError, f, X)

    def test_eq_unifies_simple(self):
        X = newvar()
        Y = newvar()
        bind(X, Y)
        assert alias_of(Y, X)
        unify(X, 1)
        assert X == 1
        assert is_bound(Y)
        assert Y == 1
        assert X is Y
        assert X == Y

    def test_ne_of_unified_unbound_vars(self):
        X = newvar()
        Y = newvar()
        bind(X, Y)
        assert is_free(X)
        assert is_free(Y)
        assert alias_of(X, Y)
        assert X == Y
        assert not X != Y

    def test_unify_tuple(self):
        X = newvar()
        unify(X, (1, (2, None)))
        assert X == (1, (2, None))

    def test_unify_list(self):
        X = newvar()
        x = (newvar(), newvar())
        unify(X, x)
        unify(X[1], (newvar(), newvar()))
        assert is_bound(X)
        assert X == x
        assert X[1] == x[1]
        unify(X, (1, (2, None)))
        assert X == (1, (2, None))
        unify(X, (1, (2, None)))
        raises(Exception, unify, X, (1, 2))

    def test_unify_dict(self):
        Z, W = newvar(), newvar()
        unify({'a': 42, 'b': Z},
              {'a':  Z, 'b': W})
        assert Z == W == 42


class AppTest_LogicThreads(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_wait_needed(self):
        X = newvar()

        def binder(V):
            wait_needed(V)
            unify(V, 42)

        def reader(V):
            wait(V)
            return V

        uthread(reader, X)
        uthread(binder, X)

        assert X == 42

    def test_eager_producer_consummer(self):

        def generate(n, limit):
            #print "generate", n, limit
            if n < limit:
                return (n, generate(n + 1, limit))
            return None

        def sum(L, a):
            #print "sum", a
            Head, Tail = newvar(), newvar()
            unify(L, (Head, Tail))
            if Tail != None:
                return sum(Tail, Head + a)
            return a + Head

        X = newvar()
        S = newvar()
        
        unify(S, uthread(sum, X, 0))
        unify(X, uthread(generate, 0, 10))

        assert S == 45


    def test_lazy_producer_consummer(self):

        def lgenerate(n, L):
            """wait-needed version of generate"""
            wait_needed(L)
            Tail = newvar()
            bind(L, (n, Tail))
            lgenerate(n+1, Tail)

        def lsum(L, a, limit):
            """this summer controls the generator"""
            if limit > 0:
                Head, Tail = newvar(), newvar()
                wait(L)
                unify(L, (Head, Tail))
                return lsum(Tail, a+Head, limit-1)
            else:
                return a

        Y = newvar()
        T = newvar()

        uthread(lgenerate, 0, Y)
        unify(T, uthread(lsum, Y, 0, 10))

        wait(T)
        assert T == 45
        
    def notest_wait_two(self):
        def sleep(X, Barrier):
            print "sleep"
            wait(X)
            bind(Barrier, True)
        
        def wait_two(X, Y):
            print "wait two"
            Z = newvar()
            uthread(sleep, X, Z)
            uthread(sleep, Y, Z)
            print "on barrier"
            wait(Z)
            if is_free(Y):
                return 1
            return 2
        
        X, Y = newvar(), newvar()
        disp(X)
        disp(Y)
        o = uthread(wait_two, X, Y)
        unify(X, Y)
        unify(Y, 42)
        assert X == Y == 42
        assert o == 2
