import py
from prolog.interpreter.continuation import *

from prolog.interpreter.parsing import parse_query_term, get_engine
from prolog.interpreter.parsing import get_query_and_vars
from prolog.interpreter.error import UnificationFailed
from prolog.interpreter.test.tool import collect_all, assert_true, assert_false


def test_driver():
    order = []
    done = DoneFailureContinuation(None)
    class FakeC(object):
        rule = None
        def __init__(self, next, val):
            self.next = next
            self.val = val

        def is_done(self):
            return False
        
        def activate(self, fcont, heap):
            if self.val == -1:
                raise error.UnificationFailed
            order.append(self.val)
            return self.next, fcont, heap

        def fail(self, heap):
            order.append("fail")
            return self, done, heap
        def discard(self):
            pass

    c5 = FakeC(FakeC(FakeC(FakeC(FakeC(DoneSuccessContinuation(None), 1), 2), 3), 4), 5)
    driver(c5, done, Heap())
    assert order == [5, 4, 3, 2, 1]

    order = []
    ca = FakeC(FakeC(FakeC(FakeC(FakeC(done, -1), 2), 3), 4), 5)
    driver(ca, c5, Heap())
    assert order == [5, 4, 3, 2, "fail", 5, 4, 3, 2, 1]

def test_failure_continuation():
    order = []
    h = Heap()
    done = DoneFailureContinuation(None)
    class FakeC(object):
        rule = None
        def __init__(self, next, val):
            self.next = next
            self.val = val

        def is_done(self):
            return False
        def activate(self, fcont, heap):
            if self.val == -1:
                raise error.UnificationFailed
            order.append(self.val)
            return self.next, fcont, heap

    class FakeF(FailureContinuation):
        def __init__(self, next, count):
            self.next = next
            self.count = count
            self.engine = FakeE()

        def fail(self, heap):
            if self.count:
                fcont = FakeF(self.next, self.count - 1)
                heap = heap.branch()
            else:
                fcont = DoneFailureContinuation(None)
            res = self.count
            order.append(res)
            self.count -= 1
            return self.next, fcont, heap

    class FakeE(object):
        pass

    ca = FakeF(FakeC(FakeC(DoneSuccessContinuation(None), -1), 'c'), 10)
    py.test.raises(UnificationFailed, driver, FakeC(DoneSuccessContinuation(None), -1), ca, h)
    assert order == [10, 'c', 9, 'c', 8, 'c', 7, 'c', 6, 'c', 5, 'c', 4, 'c',
                     3, 'c', 2, 'c', 1, 'c', 0, 'c']

def test_full():
    from prolog.interpreter.term import BindingVar, Atom, Term
    all = []
    e = Engine()
    class CollectContinuation(object):
        rule = None
        module = e.modulewrapper.user_module
        def is_done(self):
            return False
        def discard(self):
            pass
        def activate(self, fcont, heap):
            all.append((X.dereference(heap).name(), Y.dereference(heap).name()))
            raise error.UnificationFailed
    e.add_rule(Callable.build("f", [Callable.build("x")]), True)
    e.add_rule(Callable.build("f", [Callable.build("y")]), True)
    e.add_rule(Callable.build("g", [Callable.build("a")]), True)
    e.add_rule(Callable.build("g", [Callable.build("b")]), True)

    X = BindingVar()
    Y = BindingVar()
    query = Callable.build(",", [Callable.build("f", [X]), Callable.build("g", [Y])])
    py.test.raises(error.UnificationFailed,
                   e.run_query, query, e.modulewrapper.user_module, CollectContinuation())
    assert all == [("x", "a"), ("x", "b"), ("y", "a"), ("y", "b")]


def test_cut_not_reached():
    class CheckContinuation(Continuation):
        def __init__(self):
            self.nextcont = None
            self.module = e.modulewrapper.user_module
        def is_done(self):
            return False
        def activate(self, fcont, heap):
            assert fcont.is_done()
            return DoneSuccessContinuation(e), DoneFailureContinuation(e), heap
    e = get_engine("""
        g(X, Y) :- X > 0, !, Y = a.
        g(_, b).
    """)
    e.run(parse_query_term("g(-1, Y), Y == b, g(1, Z), Z == a."), 
            e.modulewrapper.user_module, CheckContinuation())

# ___________________________________________________________________
# integration tests

def test_trivial():
    e = get_engine("""
        f(a).
    """)
    m = e.modulewrapper
    t, vars = get_query_and_vars("f(X).")
    e.run(t, m.user_module)
    assert vars['X'].dereference(None).name()== "a"

def test_and():
    e = get_engine("""
        g(a, a).
        g(a, b).
        g(b, c).
        f(X, Z) :- g(X, Y), g(Y, Z).
    """)
    m = e.modulewrapper
    e.run(parse_query_term("f(a, c)."), m.user_module)
    t, vars = get_query_and_vars("f(X, c).")
    e.run(t, m.user_module)
    assert vars['X'].dereference(None).name()== "a"

def test_and_long():
    e = get_engine("""
        f(x). f(y). f(z).
        g(a). g(b). g(c).
        h(d). h(e). h(f).
        f(X, Y, Z) :- f(X), g(Y), h(Z).
    """)
    heaps = collect_all(e, "f(X, Y, Z).")
    assert len(heaps) == 27  

def test_numeral():
    e = get_engine("""
        num(0).
        num(succ(X)) :- num(X).
        add(X, 0, X).
        add(X, succ(Y), Z) :- add(succ(X), Y, Z).
        mul(X, 0, 0).
        mul(X, succ(0), X).
        mul(X, succ(Y), Z) :- mul(X, Y, A), add(A, X, Z).
        factorial(0, succ(0)).
        factorial(succ(X), Y) :- factorial(X, Z), mul(Z, succ(X), Y).
    """)
    m = e.modulewrapper
    def nstr(n):
        if n == 0:
            return "0"
        return "succ(%s)" % nstr(n - 1)
    e.run(parse_query_term("num(0)."), m.user_module)
    e.run(parse_query_term("num(succ(0))."), m.user_module)
    t, vars = get_query_and_vars("num(X).")
    e.run(t, m.user_module)
    assert vars['X'].dereference(None).num == 0
    e.run(parse_query_term("add(0, 0, 0)."), m.user_module)
    py.test.raises(UnificationFailed, e.run, parse_query_term("""
        add(0, 0, succ(0))."""), m.user_module)
    e.run(parse_query_term("add(succ(0), succ(0), succ(succ(0)))."), m.user_module)
    e.run(parse_query_term("mul(succ(0), 0, 0)."), m.user_module)
    e.run(parse_query_term("mul(succ(succ(0)), succ(0), succ(succ(0)))."), m.user_module)
    e.run(parse_query_term("mul(succ(succ(0)), succ(succ(0)), succ(succ(succ(succ(0)))))."), m.user_module)
    e.run(parse_query_term("factorial(0, succ(0))."), m.user_module)
    e.run(parse_query_term("factorial(succ(0), succ(0))."), m.user_module)
    e.run(parse_query_term("factorial(%s, %s)." % (nstr(5), nstr(120))), m.user_module)

def test_or_backtrack():
    e = get_engine("""
        a(a).
        b(b).
        g(a, b).
        g(a, a).
        f(X, Y, Z) :- (g(X, Z); g(X, Z); g(Z, Y)), a(Z).
        """)
    t, vars = get_query_and_vars("f(a, b, Z).")
    e.run(t, e.modulewrapper.user_module)
    assert vars['Z'].dereference(None).name()== "a"
    f = collect_all(e, "X = 1; X = 2.")
    assert len(f) == 2

def test_backtrack_to_same_choice_point():
    e = get_engine("""
        a(a).
        b(b).
        start(Z) :- Z = X, f(X, b), X == b, Z == b.
        f(X, Y) :- a(Y).
        f(X, Y) :- X = a, a(Y).
        f(X, Y) :- X = b, b(Y).
    """)
    assert_true("start(Z).", e)

def test_collect_all():
    e = get_engine("""
        g(a).
        g(b).
        g(c).
    """)
    heaps = collect_all(e, "g(X).")
    assert len(heaps) == 3
    assert heaps[0]['X'].name()== "a"
    assert heaps[1]['X'].name()== "b"
    assert heaps[2]['X'].name()== "c"

def test_lists():
    e = get_engine("""
        nrev([],[]).
        nrev([X|Y],Z) :- nrev(Y,Z1),
                         append(Z1,[X],Z).

        append([],L,L).
        append([X|Y],L,[X|Z]) :- append(Y,L,Z).
    """)
    e.run(parse_query_term("append(%s, %s, X)." % (range(30), range(10))),
            e.modulewrapper.user_module)
    return
    e.run(parse_query_term("nrev(%s, X)." % (range(15), )))
    e.run(parse_query_term("nrev(%s, %s)." % (range(8), range(7, -1, -1))))

def test_indexing():
    # this test is quite a lot faster if indexing works properly. hrmrm
    e = get_engine("g(a, b, c, d, e, f, g, h, i, j, k, l). " +
            "".join(["f(%s, g(%s)) :- g(A, B, C, D, E, F, G, H, I ,J, K, l). "
                      % (chr(i), chr(i + 1))
                                for i in range(97, 122)]))
    t = parse_query_term("f(x, g(y)).")
    for i in range(200):
        e.run(t, e.modulewrapper.user_module)
    t = parse_query_term("f(x, g(y, a)).")
    for i in range(200):
        py.test.raises(UnificationFailed, e.run, t, e.modulewrapper.user_module)

def test_indexing2():
    e = get_engine("""
        mother(o, j).
        mother(o, m).
        mother(o, b).

        sibling(X, Y) :- mother(Z, X), mother(Z, Y).
    """)
    heaps = collect_all(e, "sibling(m, X).")
    assert len(heaps) == 3

@py.test.mark.xfail
def test_runstring():
    e = get_engine("foo(a, c).")
    e.runstring("""
        :- op(450, xfy, foo).
        a foo b.
        b foo X :- a foo X.
    """)
    assert_true("foo(a, b).", e)

def test_call_atom():
    e = get_engine("""
        test(a).
        test :- test(_).
    """)
    assert_true("test.", e)


def test_metainterp():
    e = get_engine("""
        run(X) :- solve([X]).
        solve([]).
        solve([A | T]) :-
            my_pred(A, T, T1),
            solve(T1).

        my_pred(app([], X, X), T, T).
        my_pred(app([H | T1], T2, [H | T3]), T, [app(T1, T2, T3) | T]).

    """)
    assert_true("run(app([1, 2, 3, 4], [5, 6], X)), X == [1, 2, 3, 4, 5, 6].", e)
