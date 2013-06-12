import sys
from rpython import conftest
class o:
    view = False
    viewloops = True
conftest.option = o
from rpython.jit.metainterp.test.test_ajit import LLJitMixin

from prolog.interpreter.parsing import parse_query_term, get_engine
from prolog.interpreter.parsing import get_query_and_vars
from prolog.interpreter.continuation import jitdriver

class TestLLtype(LLJitMixin):
    def test_append(self):
        e = get_engine("""
        :- use_module(mod1).

        app([], X, X).
        app([H | T1], T2, [H | T3]) :-
            app(T1, T2, T3).
        loop(0, []).
        loop(X, [H|T]) :- X > 0, X0 is X - 1, loop(X0, T).
        loop1(0, []).
        loop1(N, [H|T]) :- N > 0, N1 is N - 1, !, loop1(N1, T).
        loop1(N, [H|T]) :- N > 0, N1 is N - 1, loop1(N1, T).
        nrev([],[]).
        nrev([X|Y],Z) :- nrev(Y,Z1),
                         app(Z1,[X],Z).

        run(X) :- solve([X]).
        solve([]).
        solve([A | T]) :-
            my_pred(A, T, T1),
            solve(T1).

        my_pred(app([], X, X), T, T).
        my_pred(app([H | T1], T2, [H | T3]), T, [app(T1, T2, T3) | T]).
        my_pred(nrev([], []), T, T).
        my_pred(nrev([X | Y], Z), Rest, [nrev(Y, Z1), app(Z1, [X], Z) | Rest]).

        add1(X, X1) :- X1 is X + 1.
        map(_, [], []).
        map(Pred, [H1 | T1], [H2 | T2]) :-
            C =.. [Pred, H1, H2],
            call(C),
            map(Pred, T1, T2).

        partition([],_,[],[]).
        partition([X|L],Y,[X|L1],L2) :-
            X =< Y, !,
            partition(L,Y,L1,L2).
        partition([X|L],Y,L1,[X|L2]) :-
            partition(L,Y,L1,L2).

        loop_mod(0).
        loop_mod(N) :-
            N > 0,
            f(N, N1),
            loop_mod(N1).

        loop_when(0).
        loop_when(N) :-
            N > 0,
            when(nonvar(X), loop_when(X)),
            X is N - 1.

        freeze_list(Num, Millis) :-
            make_varlist(Num, List),
            statistics(walltime, [T1, _]),
            freeze_list_inner(List),
            statistics(walltime, [T2, _]),
            Millis is T2 - T1.

        freeze_list_inner(List) :-
            freeze_list_inner_2(List),
            melt_list(List).

        freeze_list_inner_2([]).
        freeze_list_inner_2([H|Rest]) :-
            freeze(H, true),
            freeze_list_inner_2(Rest).

        melt_list([]).
        melt_list([H|Rest]) :-
            H = 1,
            melt_list(Rest).

        make_varlist(0, []).
        make_varlist(Num, [_|R]) :-
            Num > 0,
            Num1 is Num - 1,
            make_varlist(Num1, R).

        when_ground_list(Num, Millis) :-
            make_varlist(Num, List),
            statistics(walltime, [T1, _]),
            when(ground(List), Z = 1),
            when_ground_list_inner(List),
            statistics(walltime, [T2, _]),
            Z == 1,
            Millis is T2 - T1.

        when_ground_list_inner([]).
        when_ground_list_inner([H|R]) :-
            H = a,
            when_ground_list_inner(R).
        """, load_system=True,
        mod1 = """
        :- module(mod1, [f/2]).

        f(N, N1) :-
            mod2:g(N, N1).
        """, 
        mod2 = """
        :- module(mod2, [g/2]).

        g(N, N1) :-
            N1 is N - 1.
        """
        )

        t1 = parse_query_term("app([1, 2, 3, 4, 5, 6], [8, 9], X), X == [1, 2, 3, 4, 5, 6, 8, 9].")
        #t2 = parse_query_term("loop_when(100).")
        t2 = parse_query_term("freeze_list(15, T).")
        t3 = parse_query_term("nrev([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], X), X == [10, 9, 8, 7, 6, 5, 4, 3, 2, 1].")
        t4 = parse_query_term("run(app([1, 2, 3, 4, 5, 6, 7], [8, 9], X)), X == [1, 2, 3, 4, 5, 6, 7, 8, 9].")
        t5 = parse_query_term("map(add1, [1, 2, 3, 4, 5, 6, 7], X), X == [2, 3, 4, 5, 6, 7, 8].")
        t6 = parse_query_term("partition([6, 6, 6, 6, 6, 6, 66, 3, 6, 1, 2, 6, 8, 9, 0,4, 2, 5, 1, 106, 3, 6, 1, 2, 6, 8, 9, 0,4, 2, 5, 1, 10, 3, 6, 1, 2, 6, 8, 9, 0,4, 2, 5, 1, 10], 5, X, Y).")
        t7 = parse_query_term("findall(X+Y, app([X|_], [Y|_], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]), L).")
        def interp_w(c):
            jitdriver.set_param("inlining", True)
            if c == 1:
                t = t1
            elif c == 2:
                t = t2
            elif c == 3:
                t = t3
            elif c == 4:
                t = t4
            elif c == 5:
                t = t5
            elif c == 6:
                t = t6
            elif c == 7:
                t = t7
            else:
                raise ValueError
            e.run(t, e.modulewrapper.user_module)
        # XXX
        #interp_w(2)

        self.meta_interp(interp_w, [2], listcomp=True, backendopt=True,
                         listops=True)
        #self.meta_interp(interp_w, [3], listcomp=True,
        #                 listops=True)
