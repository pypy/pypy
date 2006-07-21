from pypy.conftest import gettestobjspace
from py.test import skip
 
class AppTest_Logic(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic', usemodules=("_stackless",))

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
        raises(Exception, f, X)

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


    def test_unify_instances(self):
        class Foo(object):
            def __init__(self, a):
                self.a = a
                self.b = newvar()

        f1 = Foo(newvar())
        f2 = Foo(42)
        unify(f1, f2)
        assert f1.a == f2.a == 42
        assert alias_of(f1.b, f2.b)
        unify(f2.b, 'foo')
        assert f1.b == f2.b == 'foo'
        raises(Exception, unify, f1.b, 24)


class AppTest_LogicThreads(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic', usemodules=("_stackless",))

    def test_future_value(self):
        
        def poop(X):
            return X + 1

        X = newvar()
        Y = future(poop, X)
        unify(X, 42)
        assert Y == 43
        assert sched_stats()['threads'] == 1

        X = newvar()
        T = future(poop, X)
        raises(Exception, unify, T, 42)
        print sched_stats()
        assert sched_stats()['threads'] == 2

        X, Y = newvar(), newvar()
        T = future(poop, X)
        raises(Exception, unify, T, Y)
        assert sched_stats()['threads'] == 3

        assert is_free(Y)
        X = newvar()
        T = future(poop, X)
        unify(Y, T)
        unify(X, 42)
        assert Y == 43
        assert sched_stats()['threads'] == 3

    def test_one_future_exception(self):
        class FooException(Exception): pass
        
        def poop(X):
            wait(X)
            raise FooException

        X=newvar()
        Y=future(poop, X)
        unify(X, 42)
        try:
            assert Y == 43
        except FooException:
            return
        assert False

    def test_exceptions_harder(self):
        class FooException(Exception): pass

        def raise_foo():
            raise FooException

        def spawn(X, n):
            if n>0:
                F = future(spawn, X, n-1)
                wait(X)
            else:
                raise_foo()
            return F

        X = newvar()
        Y = future(spawn, X, 5)
        unify(X, 42)
        try:
            assert Y == 1
        except FooException:
            return
        assert False

    def test_nested_threads(self):
        """check that a wait nested in a tree of
           threads works correctly
        """
        def sleep(X):
            wait(X)
            return X

        def call_sleep(X):
            return future(sleep, X)

        X = newvar()
        v = future(call_sleep, X)
        bind(X, 42)
        assert X == 42
        assert is_free(v)
        assert v == 42

    def test_wait_needed(self):
        X = newvar()

        def binder(V):
            wait_needed(V)
            unify(V, 42)

        def reader(V):
            wait(V)
            return V

        future(reader, X)
        future(binder, X)

        assert X == 42

    def test_eager_producer_consummer(self):

        def generate(n, limit):
            if n < limit:
                return (n, generate(n + 1, limit))
            return None

        def sum(L, a):
            Head, Tail = newvar(), newvar()
            unify(L, (Head, Tail))
            if Tail != None:
                return sum(Tail, Head + a)
            return a + Head

        X = newvar()
        S = newvar()
        unify(S, future(sum, X, 0))
        unify(X, future(generate, 0, 10))
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

        future(lgenerate, 0, Y)
        unify(T, future(lsum, Y, 0, 10))

        wait(T)
        assert T == 45

    def test_wait_two(self):
        def sleep(X, Barrier):
            wait(X)
            bind(Barrier, True)
        
        def wait_two(X, Y):
            Barrier = newvar()
            future(sleep, X, Barrier)
            future(sleep, Y, Barrier)
            wait(Barrier)
            if is_free(Y):
                return 1
            return 2

        X, Y = newvar(), newvar()
        o = future(wait_two, X, Y)
        unify(X, Y)
        unify(Y, 42)
        assert X == Y == 42
        assert o == 2
        
    def test_fib(self):
        skip("recursion limits breakage")
        def fib(X):
            if X<2:
                return 1
            else:
                return future(fib, X-1) + fib(X-2)

        X = newvar()
        F = future(fib, X)
        unify(11, X)
        assert F == 144

        X = newvar()
        F = future(fib, X)

        try:
            unify(50, X)
            print F
        except Exception, e:
            print e
