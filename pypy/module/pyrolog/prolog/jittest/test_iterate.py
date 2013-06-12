from prolog.jittest.test_00_model import BaseTestPyrologC

class TestIterate(BaseTestPyrologC):
    def test_call(self):
        code = """
        iterate_call(X) :- c(X, c).
        c(0, _).
        c(X, Pred) :-
            Y is X - 1, C =.. [Pred, Y, Pred], call(C).
        """
        log = self.run_and_check(code, "iterate_call(10000).")
        loop, = log.filter_loops("c")
        assert loop.match("""
            i6 = int_sub_ovf(i2, 1)
            guard_no_overflow(descr=<Guard2>)
            guard_not_invalidated(descr=<Guard3>)
            i9 = int_eq(i6, 0)
            guard_false(i9, descr=<Guard4>)
            jump(p0, p1, i6, p3, p4, descr=<Loop0>)
        """)

    def test_cut(self):
        py.test.skip("fix me later")
        code = """
            iterate_cut(0).
            iterate_cut(X) :- Y is X - 1, !, iterate_cut(Y).
            iterate_cut(X) :- Y is X - 2, iterate_cut(Y).
        """
        log = self.run_and_check(code, "iterate_cut(10000).")
        loop, = log.filter_loops("c")
        assert loop.match("""
            i6 = int_sub_ovf(i2, 1)
            guard_no_overflow(descr=<Guard2>)
            guard_not_invalidated(descr=<Guard3>)
            i9 = int_eq(i6, 0)
            guard_false(i9, descr=<Guard4>)
            jump(p0, p1, i6, p3, p4, descr=<Loop0>)
        """)

    def test_failure_driven(self):
        py.test.skip("fix me later")
        code = """
            g(X, Y, Out) :- Out is X - Y.
            g(X, Y, Out) :- Y > 0, Y0 is Y - 1, g(X, Y0, Out).
            iterate_failure(X) :- g(X, X, A), fail.
            iterate_failure(_).
        """
        log = self.run_and_check(code, "iterate_failure(10000).")
        loop, = log.filter_loops("g")
        assert loop.match("""
            i6 = int_sub_ovf(i2, 1)
            guard_no_overflow(descr=<Guard2>)
            guard_not_invalidated(descr=<Guard3>)
            i9 = int_eq(i6, 0)
            guard_false(i9, descr=<Guard4>)
            jump(p0, p1, i6, p3, p4, descr=<Loop0>)
        """)

    def test_ifthenelse(self):
        code = """
            equal(0, 0). equal(X, X).
            iterate_if(X) :- equal(X, 0) -> true ;
                             Y is X - 1, iterate_if(Y).
        """
        log = self.run_and_check(code, "iterate_if(10000).")
        loop, = log.filter_loops("iterate_if")
        assert loop.match("""
            guard_not_invalidated(descr=...)
            i5 = int_eq(i2, 0)
            guard_false(i5, descr=...)
            i7 = int_sub_ovf(i2, 1)
            guard_no_overflow(descr=...)
            jump(p0, p1, i7, p3, descr=<Loop0>)
        """)
