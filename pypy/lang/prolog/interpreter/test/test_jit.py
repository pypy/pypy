import py
py.test.skip("JIT disabled for now")
from pypy.jit.timeshifter.test.test_portal import PortalTest, P_NOVIRTUAL
from pypy.lang.prolog.interpreter import portal
from pypy.lang.prolog.interpreter import engine, term
from pypy.lang.prolog.interpreter.parsing import parse_query_term, get_engine

POLICY = portal.PyrologHintAnnotatorPolicy()

py.test.skip()

class TestPortal(PortalTest):
    small = False

    def test_simple(self):
        e = get_engine("""
            f(x, y).
            f(a(X), b(b(Y))) :- f(X, Y).
        """)
        X = e.heap.newvar()
        Y = e.heap.newvar()
        larger = term.Term(
            "f", [term.Term("a", [X]), term.Term("b", [term.Term("b", [Y])])])

        def main(n):
            e.heap.reset()
            if n == 0:
                e.call(term.Term("f", [X, Y]))
                return isinstance(X.dereference(e.heap), term.Atom)
            if n == 1:
                e.call(larger)
                return isinstance(X.dereference(e.heap), term.Atom)
            else:
                return False

        res = main(0)
        assert res == True
        res = main(1)
        assert res == True


        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [1], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res == True
        
        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res == True

    def test_and(self):
        e = get_engine("""
            h(X) :- f(X).
            h(a).
            b(a).
            a(a).
            f(X) :- b(X), a(X).
            f(X) :- fail.
        """)
        X = e.heap.newvar()

        def main(n):
            e.heap.reset()
            if n == 0:
                e.call(term.Term("h", [X]))
                return isinstance(X.dereference(e.heap), term.Atom)
            else:
                return False

        res = main(0)
        assert res == True

        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res == True

    def test_append(self):
        e = get_engine("""
            append([], L, L).
            append([X|Y], L, [X|Z]) :- append(Y, L, Z).
        """)
        t = parse_query_term("append([a, b, c], [d, f, g], X).")
        X = e.heap.newvar()

        def main(n):
            if n == 0:
                e.call(t)
                return isinstance(X.dereference(e.heap), term.Term)
            else:
                return False

        res = main(0)
        assert res == True

        e.heap.reset()
        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res == True


    def test_user_call(self):
        e = get_engine("""
            h(X) :- f(X, b).
            f(a, a).
            f(X, b) :- g(X).
            g(b).
        """)
        X = e.heap.newvar()

        def main(n):
            e.heap.reset()
            if n == 0:
                e.call(term.Term("h", [X]))
                return isinstance(X.dereference(e.heap), term.Atom)
            else:
                return False

        res = main(0)
        assert res == True


        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res == True

    def test_loop(self):
        e = get_engine("""
            f(X) :- h(X, _).
            f(50).
            h(0, _).
            h(X, Y) :- Y is X - 1, h(Y, _).
        """)
        num = term.Number(50)

        def main(n):
            e.heap.reset()
            if n == 0:
                e.call(term.Term("f", [num]))
                return True
            else:
                return False

        res = main(0)
        assert res
        res = self.timeshift_from_portal(main, portal.PORTAL,
                                         [0], policy=POLICY,
                                         backendoptimize=True, 
                                         inline=0.0)
        assert res

