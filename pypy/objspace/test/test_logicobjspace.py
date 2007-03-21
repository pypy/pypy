try:
    from pypy.conftest import gettestobjspace, option
    from py.test import skip
except ImportError:
    pass
    # we might be called from _test_logic_build
    # if not, check your paths


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
        raises(RebindingError, bind, X, 2)

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
        raises(AllBlockedError, f, X)

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
        # this tests fails with compiled pypy-logic
        # for no apparent reason
        # seems like we block in the wait call
        # from X == x (where at least one var
        # looks free then)
        X = newvar()
        x = (newvar(), newvar())
        unify(X, x)
        unify(X[1], (newvar(), newvar()))
        # passes
        assert not is_free(X)
        assert not is_free(x)
        assert X is x
        assert X[1] == x[1]
        # fails 
        assert X == x
        unify(X, (1, (2, None)))
        assert X == (1, (2, None))
        unify(X, (1, (2, None)))
        raises(UnificationError, unify, X, (1, 2))

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
        raises(UnificationError, unify, f1.b, 24)


    def test_entail(self):
        X, Y = newvar(), newvar()
        entail(X, Y)
        unify(42, X)
        assert X == Y == 42

        X, Y = newvar(), newvar()
        entail(X, Y)
        unify(42, Y)
        assert is_free(X)
        assert Y == 42
        unify(X, 42)
        assert X == Y == 42

        X, Y = newvar(), newvar()
        entail(X, Y)
        unify(42, Y)
        assert is_free(X)
        assert Y == 42
        raises(UnificationError, unify, X, True)

        X, Y = newvar(), newvar()
        entail(X, Y)
        unify(X, Y)
        assert is_free(X)
        assert is_free(Y)
        unify(Y, 42)
        assert X == Y == 42

        X, Y, O = newvar(), newvar(), newvar()
        entail(X, O)
        entail(Y, O)
        unify(Y, 42)
        assert is_free(X)
        assert Y == O == 42
        

class AppTest_LogicFutures(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_future_value(self):
        from cclp import future
        
        def poop(X):
            return X + 1

        X = newvar()
        Y = future(poop, X)
        unify(X, 42)
        assert Y == 43

        X = newvar()
        T = future(poop, X)
        raises(FutureBindingError, unify, T, 42)
        bind(X, 42)

        X, Y, Z = newvar(), newvar(), newvar()
        bind(Z, 42)
        T = future(poop, X)
        raises(FutureBindingError, unify, T, Z)
        raises(FutureBindingError, unify, Z, T)
        raises(FutureBindingError, unify, Y, T)
        raises(FutureBindingError, unify, T, Y)
        bind(X, 42)

    def test_one_future_exception(self):
        from cclp import future
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

    def test_exception_in_chain(self):
        from cclp import future
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

    def test_exception_in_group(self):
        from cclp import future
        class FooException(Exception): pass

        def loop_or_raise(Canary, crit, Bomb_signal):
            "Canary will be untouched there ..."
            while(1):
                if is_bound(Bomb_signal):
                    if Bomb_signal == crit:
                        raise FooException
                    else: # but returned
                        return Canary
            return 42

        B, C = newvar(), newvar()
        T = future(loop_or_raise, C, 'foo', B)
        U = future(loop_or_raise, C, 'bar', B)
        unify(B, 'foo')
        try:
            wait(T)
        except FooException:
            try:
                # and contaminated
                wait(U)
            except FooException:
                return
        assert False
        
    def test_nested_threads(self):
        """check that a wait nested in a tree of
           threads works correctly
        """
        from cclp import future
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
        from cclp import future
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
        from cclp import stacklet

        def generate(n, limit, R):
            if n < limit:
                Tail = newvar()
                unify(R, (n, Tail))
                return generate(n + 1, limit, Tail)
            bind(R, None)
            return

        def sum(L, a, R):
            Head, Tail = newvar(), newvar()
            unify(L, (Head, Tail))
            if Tail != None:
                return sum(Tail, Head + a, R)
            bind(R, a + Head)
            return

        X = newvar()
        S = newvar()
        stacklet(sum, X, 0, S)
        stacklet(generate, 0, 10, X)
        assert S == 45

    def test_problematic_eager_producer_consummer(self):
        """
        straight from CRM
        BUG:a way (not to) keep the generator live forever
        """
        from cclp import future

        def generate(n, Xs):
            Xr = newvar()
            wait(Xs)
            unify((n, Xr), Xs)
            generate(n+1, Xr)

        def sum(Xs, a, limit):
            if limit > 0:
                X, Xr = newvar(), newvar()
                unify((X, Xr), Xs)
                return sum(Xr, a+X, limit-1)
            else:
                unify(None, Xs) # -> to release the generator
                                #    with a unification error
                                # Oz code does not suffer from this
                return a

        Xs = newvar()
        S = future(sum, Xs, 0, 10)
        future(generate, 0, Xs)
        assert S == 45

    def test_lazy_producer_consummer(self):
        from cclp import future, stacklet, sched_info, reset_scheduler

        def lgenerate(n, L):
            """wait-needed version of generate"""
            #XXX how is this ever collected ?
            #    should be when L becomes unreferenced from
            #    outside this thread ... But this can't
            #    happen right now because we keep
            #    references also of this thread in the
            #    scheduler. 
            wait_needed(L)
            Tail = newvar()
            bind(L, (n, Tail))
            lgenerate(n+1, Tail)

        def lsum(L, a, limit, R):
            """this summer controls the generator"""
            if limit > 0:
                Head, Tail = newvar(), newvar()
                wait(L) # send needed signal to generator
                unify(L, (Head, Tail))
                return lsum(Tail, a+Head, limit-1, R)
            else:
                bind(R, a)

        Y = newvar()
        T = newvar()

        future(lgenerate, 0, Y)
        stacklet(lsum, Y, 0, 10, T)

        assert T == 45
        assert len(sched_info()['blocked_byneed']) == 1
        reset_scheduler()
        assert len(sched_info()['blocked_byneed']) == 0
        sp_info = [y for x, y in sched_info().items()
                   if isinstance(x, int)][0]
        assert len(sp_info['threads']) == 1

    def test_wait_two(self):
        from cclp import future, sched_info

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
        sp_info = [y for x, y in sched_info().items()
                   if isinstance(x, int)][0]
        assert len(sp_info['threads']) == 1
        
    def test_fib(self):
        from cclp import future
        def fib(X):
            if X<2:
                return 1
            else:
                return future(fib, X-1) + fib(X-2)
                
        X = newvar()
        F = future(fib, X)
        # values > 10 triggers exhaustion of the cpython stack
        unify(10, X)
        assert F == 89

    def test_stacklet(self):
        from cclp import stacklet, sched_info, reset_scheduler

        reset_scheduler()
        count = [0]

        def inc_and_greet(count, max_, Finished, Failed):
            if count[0] >= max_:
                count[0] += 1
                bind(Finished, count[0])
                return
            count[0] += 1

        Finished, Failed = newvar(), newvar()
        max_spawn = 2
        erring = 3
        for i in range(max_spawn + erring):
            stacklet(inc_and_greet, count, max_spawn, Finished, Failed)

        wait(Finished)
        assert count[0] == max_spawn + erring
        try:
            wait(Failed)
        except RebindingError, e:
            sp_info = [y for x, y in sched_info().items()
                       if isinstance(x, int)][0]
            assert len(sp_info['threads']) == 1
            return
        assert False
                                           

    def test_stream_merger(self):
        """this is a little cheesy, due to threads not
        being preemptively scheduled
        """
        from cclp import future, stacklet, schedule
        
        def _sleep(X, Barrier):
            wait(X)
            unify(Barrier, True)
        
        def wait_two(X, Y):
            Barrier = newvar()
            stacklet(_sleep, X, Barrier)
            stacklet(_sleep, Y, Barrier)
            wait(Barrier)
            if is_free(Y):
                return 1
            return 2

        def stream_merger(S1, S2):
            F = newvar()
            unify(F, wait_two(S1, S2))
            if F==1:
                if S1 is None:
                    return S2
                else:
                    M, NewS1 = newvar(), newvar()
                    unify((M, NewS1), S1)
                    return (M, stream_merger(S2, NewS1))
            elif F==2:
                if S2 is None:
                    return S1
                else:
                    M, NewS2 = newvar(), newvar()
                    unify((M, NewS2), S2)
                    return (M, stream_merger(NewS2, S1))
        

        def feed_stream(S, values):
            for v in values:
                N = newvar()
                bind(S, (v, N))
                S = N # yeah, tail recursion is cooler
                schedule()
            bind(S, None)

        S1, S2 = newvar(), newvar()
        
        O = future(stream_merger, S1, S2)
        
        stacklet(feed_stream, S2, ['foo', 'bar', 'quux', 'spam', 'eggs'])
        stacklet(feed_stream, S1, range(10))
        
        assert O == ('foo', (0, ('bar', (1, ('quux', (2, ('spam',
                    (3, ('eggs', (4, (5, (6, (7, (8, (9, None)))))))))))))))
        

    def test_digital_logic(self):
        from cclp import stacklet, reset_scheduler
        
        def print_stream(S):
            elts = []
            while is_bound(S):
                if S is None:
                    break
                elts.append(str(S[0]))
                S = S[1]
            print '[%s]' % ','.join(elts)

        def bound_part(S):
            elts = []
            while is_bound(S):
                if S is None:
                    break
                elts.append(S[0])
                S = S[1]
            return elts
            
        
        def gatemaker(Fun):
            def _(X, Y):
                def gateloop(X, Y, R):
                    Xs, Ys, Xr, Yr = newvar(), newvar(), newvar(), newvar()
                    unify((X,        Y),
                          ((Xs, Xr), (Ys, Yr)))
                    Rs = newvar()
                    unify(R, (Fun(Xs, Ys), Rs))
                    gateloop(Xr, Yr, Rs)
                R = newvar()
                stacklet(gateloop, X, Y, R)
                return R
            return _

        andg  = gatemaker(lambda X, Y: X*Y,)
        org   = gatemaker(lambda X, Y: X+Y-X*Y)
        xorg  = gatemaker(lambda X, Y: X+Y-2*X*Y)
        
        def full_adder(X, Y, Z, C, S):
            K, L, M = newvar(), newvar(), newvar()
            unify(K, andg(X, Y))
            unify(L, andg(Y, Z))
            unify(M, andg(X, Z))
            unify(C, org(K, org(L, M)))
            unify(S, xorg(Z, xorg(X, Y)))

        X, Y, Z, C, S = newvar(), newvar(), newvar(), newvar(), newvar()

        unify(X, (1, (1, (0, newvar()))))
        unify(Y, (0, (1, (0, newvar()))))
        unify(Z, (1, (1, (1, newvar()))))


        stacklet(full_adder, X, Y, Z, C, S)
        wait(C); wait(S)
        assert bound_part(C) == [1, 1, 0]
        assert bound_part(S) == [0, 1, 1]

        reset_scheduler() # free all the hanging threads
        

class AppTest_CompSpace(object):

    def setup_class(cls):
        cls.space = gettestobjspace('logic')

    def test_cvar(self):
        from cclp import newspace

        def in_space(X):
            d = domain([1, 2, 4], '')

            raises(UnificationError, bind, d, 42)
            bind(d, 2)
            assert d == 2

            class Foo(object):
                pass

            f = Foo()
            d = domain([Foo(), f, Foo()], '')
            raises(UnificationError, bind, d, Foo())
            bind(d, f)
            assert d == f

            d1 = domain([1, 2, 3], '')
            d2 = domain([2, 3, 4], '')
            d3 = domain([5, 6], '')
            raises(UnificationError, unify, d1, d3)
            unify(d1, d2)
            assert alias_of(d1, d2)
            assert domain_of(d1) == domain_of(d2)

            d1 = domain([1, 2, 3], '')
            d4 = domain([3, 4], '')
            unify(d1, d4)
            assert d1 == d4 == 3

            d1 = domain([1, 2], '')
            x = newvar()
            unify(d1, x)
            assert alias_of(x, d1)
            raises(UnificationError, unify, x, 42)

            d1 = domain([1, 2], '')
            x = newvar()
            unify(d1, x)
            assert alias_of(x, d1)
            unify(x, 2)
            assert d1 == x == 2
            #XXX and a bunch of app-level functions
            #raises(TypeError, domain_of, x)

            bind(X, True)
            return []

        X = newvar()

        newspace(in_space, X)
        wait(X)

    def test_ask_choose(self):
        from cclp import stacklet, newspace, choose

        def chooser(X):
            choice = choose(3)
            unify(X, choice)

        def asker(cspace):
            choices = cspace.ask()
            cspace.commit(2)

        X = newvar()
        s = newspace(chooser, X)
        stacklet(asker, s)
        wait(X)
        assert X == 2

    def test_more_ask_choose(self):
        from cclp import stacklet, newspace, choose, sched_info

        def chooser(vec, X):
            for v in vec:
                choice = choose(v)
                assert choice == v
            unify(X, 'done')
            return []

        def asker(cspace):
            while 1:
                choices = cspace.ask()
                cspace.commit(choices)
                if choices == 8: # success !
                    break

        v = range(2, 9)
        X = newvar()
        s = newspace(chooser, v, X)
        stacklet(asker, s)

        assert len(sched_info()[interp_id(s)]['asking']) == 1
        assert X == 'done'


    def test_tell_ask_choose_commit(self):
        from constraint.examples import conference_scheduling
        from cclp import stacklet, newspace, dorkspace, choose
        
        def solve(spc, commitment, Sol):
            while 1:
                status = spc.ask()
                if status > 1:
                    spc.commit(commitment)
                elif status in (0, 1):
                    break
            if status:
                unify(Sol, spc.merge())
                raises(AssertionError, spc.merge)
            else:
                unify(Sol, False)

        for somespace in (dorkspace, newspace):
            for commit_to in (1, 2):
                s = somespace(conference_scheduling)
                Solution = newvar()
                stacklet(solve, s, commit_to, Solution)

                # well, depending on dict key linear order, we get different
                # results -- possibly failed spaces
                assert len(Solution) == 10
        

    def test_logic_program(self):
        from cclp import newspace, dorkspace, choose
        
        def soft():
            choice = choose(2)
            if choice == 1:
                return 'beige'
            else:
                return 'coral'

        def hard():
            choice = choose(2)
            if choice == 1:
                return 'mauve'
            else:
                return 'ochre'

        def contrast(C1, C2):
            choice = choose(2)
            if choice == 1:
                unify(C1, soft())
                unify(C2, hard())
            else:
                unify(C1, hard())
                unify(C2, soft())

        def suit():
            Shirt, Pants, Socks = newvar(), newvar(), newvar()
            contrast(Shirt, Pants)
            contrast(Pants, Socks)
            if Shirt == Socks: fail()
            return (Shirt, Pants, Socks)

        def solve(spc, commitment, Sol):
            while 1:
                status = spc.ask()
                if status > 1:
                    spc.commit(commitment.next())
                elif status in (0, 1):
                    break
            if status:
                unify(Sol, spc.merge())
            else:
                unify(Sol, False)

        def lazily(lst):
            for e in lst:
                yield e

        for somespace in (dorkspace, newspace):
            for commit_to in (lazily([1, 1, 1, 1, 1, 1]),
                              lazily([1, 1, 1, 2, 1, 2])):
                s = somespace(suit)
                Solution = newvar()
                solve(s, commit_to, Solution)
                assert Solution in (False, ('beige', 'mauve', 'coral'))

    def test_queens(self):
        skip("success depends on dict order")
        from constraint.examples import queens1, queens2
        from cclp import newspace

        def solve(spc, commitment, Sol):
            while 1:
                status = spc.ask()
                if status > 1:
                    spc.commit(commitment.next())
                elif status in (0, 1):
                    break
            if status:
                unify(Sol, spc.merge())
            else:
                unify(Sol, False)

        def lazily(lst):
            for e in lst:
                yield e

        def all_paths(length):
            number = 2 ** length
            for i in range(number):
                res = []
                k = i
                for j in range(length):
                    res.append((k & 1) + 1)
                    k = k >> 1
                yield res

        for queen in (queens1, queens2):
            sols = set()
            for commitment in all_paths(3):
                s = newspace(queen, 4)
                Solution = newvar()
                commit = lazily(commitment)
                solve(s, commit, Solution)
                if Solution:
                    sols.add(tuple(Solution))
            assert len(sols) == 2


