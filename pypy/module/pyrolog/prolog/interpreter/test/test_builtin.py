import py
from prolog.interpreter.parsing import parse_file, TermBuilder
from prolog.interpreter.parsing import parse_query_term, get_engine
from prolog.interpreter.error import UnificationFailed
from prolog.interpreter.continuation import Heap, Engine
from prolog.interpreter import error
from prolog.interpreter.test.tool import collect_all, assert_false, assert_true
from prolog.interpreter.test.tool import prolog_raises

def test_or():
    assert_false("fail;fail.")
    e = get_engine("""
        f(X, Y) :-
               ( fail
               ; X \== Y
               ).
    """)
    assert_false("f(X,X).", e)

def test_fail():
    e = get_engine("""
        g(a).
        f(X) :- g(X), fail.
        f(a).
    """)
    heaps = collect_all(e, "f(X).")
    assert len(heaps) == 1

def test_not():
    assert_true("not(fail).")
    assert_false("not(true).")
    e = get_engine("""
        g(a, a).
        g(b, a).
        g(b, b).

        m(o, a).
        m(o, b).
        m(o, c).
        same(X, X).

        sibling(X, Y) :- m(Z, X), m(Z, Y), \\+same(X, Y).
    """)
    assert_true("not(g(b, c)).", e)
    assert_false("not(g(a, a)).", e)
    assert_true("\\+(g(b, c)).", e)
    assert_false("\\+(g(a, a)).", e)

    heaps = collect_all(e, "sibling(a, X).")
    assert len(heaps) == 2

def test_and():
    assert_false("fail, X.")
    prolog_raises("type_error(callable, 1)", "(fail, 1)")

def test_nonvar():
    e = get_engine("""
        g(X) :- nonvar(X).
        g(x, X) :- nonvar(x), nonvar(X).
        f(X, Y) :- nonvar(X), nonvar(Y).
    """)
    assert_true("g(a).", e)
    assert_false("g(X).", e)
    assert_true("g(x).", e)
    assert_true("g(x, a).", e)
    assert_true("g(X, X).", e)
    assert_false("f(X, X).", e)

def test_consult():
    p = py.test.ensuretemp("prolog")
    f = p.join("test.pl")
    f.write("g(a, a). g(a, b).")
    e = get_engine("g(c, c).")
    assert_true("g(c, c).", e)
    assert_true("consult('%s')." % (f, ), e)
    assert_true("g(c, c).", e)
    assert_true("g(a, a).", e)
    assert_true("g(a, b).", e)
    prolog_raises("_", "consult('/hopefully/does/not/exist')")

def test_assert_retract():
    e = get_engine("g(b, b).")
    assert_true("g(B, B).", e)
    assert_true("assert(g(c, d)).", e)
    assert_true("assert(g(a, b)).", e)
    assert_true("assert(g(a, b)).", e) # assert the same rule multiple times
    assert_true("g(B, B).", e)
    assert_true("g(a, b).", e)
    assert_true("g(c, d).", e)
    assert_true("retract(g(B, B)).", e)
    assert_false("g(B, B).", e)
    assert_true("retract(g(a, b)).", e)
    assert_true("g(a, b).", e)
    assert_true("retract(g(a, b)).", e)
    assert_false("retract(g(a, b)).", e)
    assert_false("g(a, b).", e)
    assert_true("g(c, d).", e)
    e = get_engine("""
        g(b, b).
        f(X) :- g(X, b).
        f(a).
    """)
    assert_true("f(b).", e)
    assert_true("f(a).", e)
    assert_true("retract(f(X) :- g(X, Y)), Y == b.", e)
    assert_false("f(b).", e)
    assert_true("f(a).", e)
    prolog_raises("permission_error(X, Y, Z)", "retract(atom(X))")

def test_assert_at_right_end():
    e = get_engine("g(b, b). f(b, b). h(b, b).")
    assert_true("assert(g(a, a)).", e)
    assert_true("assertz(f(a, a)).", e)
    assert_true("A = a, asserta(h(A, A)).", e)
    f = assert_true("g(B, B).", e)
    assert f['B'].name()== "b"
    f = assert_true("f(B, B).", e)
    assert f['B'].name()== "b"
    assert_false("h(c, c).", e)
    f = assert_true("h(B, B).", e)
    assert f['B'].name()== "a"

def test_assert_logical_update_view():
    e = get_engine("""
        g(a).
        g(c) :- assertz(g(d)).
        g(b).
    """)
    heaps = collect_all(e, "g(X).")
    assert len(heaps) == 3
    e = get_engine("""
        p :- assertz(p), fail.
        p :- fail.
    """)
    assert_false("p.", e)
    e = get_engine("""
        q :- fail.
        q :- assertz(q), fail.
    """)
    assert_false("q.", e)

def test_assert_retract_colon():
    e = get_engine("""
    :(1, 2, 3).
    :(a).
    """)
    assert_true(":(1, 2, 3), :(a).", e)
    assert_true("assert(:(a, b, c, d)).", e)
    assert_true(":(a, b, c, d).", e)
    assert_true("retract(:(a, b, c, d)).", e)
    prolog_raises("existence_error(_, _)", ":(a, b, c, d)", e)

def test_abolish_colon():
    e = get_engine("""
    :(a).
    :(1, 2, 3).
    """)
    assert_true("abolish(:/1).", e)
    prolog_raises("existence_error(_, _)", ":(a)", e)
    assert_true(":(1, 2, 3).", e)
    assert_true("abolish(:/3).", e)
    prolog_raises("existence_error(_, _)", ":(1, 2, 3)", e)

def test_retract_logical_update_view():
    e = get_engine("""
        p :- retract(p :- true), fail.
        p :- true.
    """)
    assert_true("p.", e)
    assert_false("p.", e)

def test_abolish():
    e = get_engine("g(b, b). g(c, c). g(a). f(b, b). h(b, b).")
    assert_true("abolish(g/2).", e)
    assert_true("g(a).", e)
    prolog_raises("existence_error(X, Y)", "g(A, B)", e)
    prolog_raises("type_error(predicate_indicator, a)", "abolish(a)", e)

def test_unify():
    assert_true("g(b, B) = g(b, b).")
    assert_true("X = Y.")
    assert_true("X = f(X).")
    assert_false("g(b, B) \\= g(b, b).")
    assert_false("X \\= Y.")
    assert_false("X \\= f(X).")
    assert_true("x \\= y.")
    assert_true("f(X, b) \\= f(a, c), X = c.")
    assert_true("unify_with_occurs_check(X, Y).")
    assert_true("unify_with_occurs_check(X, X).")
    assert_false("unify_with_occurs_check(X, f(X)).")
    assert_false("unify_with_occurs_check(X, f(g(h(a, b, c, d(X, e), e)))).")
    assert_false("unify_with_occurs_check(g(X), X).")
    assert_false("X = Y, unify_with_occurs_check(X, f(d(Y), Y)).")

def test_call():
    e = get_engine("g(b, b).")
    assert_true("call(g(X, X)).", e)
    assert_true("X =.. [g, b, b], call(X).", e)
    e = get_engine("""
        g(X) :- call(f(X)).
        g(a).
        g(b).
        f(X) :- !, h(X).
        f(a).
        f(b).
        h(X) :- fail.
        withcut(X) :- call(!), fail.
        withcut(a).
        """)
    heaps = collect_all(e, "g(X).")
    assert len(heaps) == 2
    assert_true("withcut(a).", e)
    assert_true("call((!, true)).")

def test_cut():
    e = get_engine("""
        f(0).
        f(X) :- Y is X - 1, !, f(Y).
        f(X) :- Y is X - 2, !, f(Y).
    """)
    assert_true("f(20).", e)

def test_cut_with_throw():
    e = get_engine("""
        raise_if_var(X) :-
            var(X), !, throw(unbound).
        raise_if_var(X) :- X = a.
        c(X, Y) :- catch((raise_if_var(X), Y = b), E, Y = a).
    """)
    assert_true("c(_, Y), Y == a.", e)

def test_cut_with_throw_direct():
    e = get_engine("""
        c(X, Y) :- catch(((X = a; X = b), !, X = b, Y = b), E, Y = a); X = c.
    """)
    assert_true("c(X, Y), X == c.", e)

def test_call_cut():
    e = get_engine("""
        f(X) :- call(X).
        f(!).
    """)
    heaps = collect_all(e, "f(!).")
    assert len(heaps) == 2
    assert_true("call(((X = a; X = b), !, X = b)); X = c.")
    assert_false("(((X = a; X = b), !, X = b)); X = c.")

def test_bug_or_exposing_problem_of_cyclic_term_support():
    e = get_engine("""
        f(X) :- (X = 1; X = 2), X = 2.
    """)
    assert_true("f(X).", e)

def test_or_and_call_with_cut():
    e = get_engine("""
        f :- (!, fail); true.
        g :- (call(!), fail); true.
    """)
    assert_false("f.", e)
    assert_true("g.", e)

def test_or_with_cut():
    e = get_engine("""
        f(X) :- ((X = 1, !); X = 2), X = 2.
        g(X) :- ((X = 1, !); X = 2), X = 1.
    """)
    assert_false("f(X).", e)
    assert_true("g(X).", e)


def test_cut1():
    e = get_engine("""
        g(a).
        g(b).
        a(a).
        b(b).
        f(X) :- g(X),!,b(X).
        f(x).
        f(y).
    """)
    heaps = collect_all(e, "f(X).")
    assert len(heaps) == 0
    assert_true("!.")

def test_cut2():
    e = get_engine("""
        g(a).
        g(b).
        h(a, x).
        h(a, y).
        f(X, Y) :- g(X), !, !, !, !, !, h(X, Y).
    """)
    heaps = collect_all(e, "f(X, Y).")
    assert len(heaps) == 2

def test_cut3():
    e = get_engine("""
        member(H, [H | _]).
        member(H, [_ | T]) :- member(H, T).

        s(a, L) :- !, fail.
        s(b, L).
        s(X, L) :-
            member(Y, L),
            L = [_| S],
            s(Y, S).
    """)
    #    import pdb; pdb.set_trace()
    assert_true("s(d, [a, b]).", e)


def test_rule_with_cut_calling_rule_with_cut():
    e = get_engine("""
        e(a).
        e(b).
        f(b) :- e(_), !.
        f(c).
        g(X) :- f(X), !.
        g(a).
    """)
    heaps = collect_all(e, "g(X).")
    assert len(heaps) == 1

def test_not_with_cut():
    assert_true("not((!, fail)).")
    assert_false("not(!).")

    e = get_engine("""
    p1 :- \\+ q1.
    q1 :- fail.
    q1 :- true.
    
    p2:- \\+ q2.
    q2 :- !, fail.
    q2 :- true.
    """)
    assert_false("p1.", e)
    assert_true("p2.", e)

def test_not_stops_cut():
    e = get_engine("""
        f(X) :- (X = a; X = b), not((!, fail)).
        """)
    assert_true("f(X), X = b.", e)
    assert_true("not(((X = 1; X = 2), !, X=2)).", e)



def test_two_cuts():
    e = get_engine("""
        f(>, X) :- X > 0, !.
        f(=, X) :- X = 0, !.
        f(<, _).
    """)
    assert_true("f(X, 1), X = '>'.", e)
    assert_true("f(X, 0), X = '='.", e)
    assert_true("f(X, -1), X = '<'.", e)

def test_listify():
    e = get_engine("""
        listify(_X, _X) :-
            (var(_X); atomic(_X)), !.
        listify(_Expr, [_Op|_LArgs]) :-
            functor(_Expr, _Op, N),
            listify_list(1, N, _Expr, _LArgs).

        listify_list(I, N, _, []) :- I>N, !.
        listify_list(I, N, _Expr, [_LA|_LArgs]) :- I=<N, !,
            arg(I, _Expr, _A),
            listify(_A, _LA),
            I1 is I+1,
            listify_list(I1, N, _Expr, _LArgs).
    """)
    assert_true("listify(f(X), Y), Y = [f, X].", e)
    assert_true("listify(f(X, g(1)), Y).", e)
    assert_true("listify(f(X, 1, g(1)), Y), Y = [f, X, 1, [g, 1]].", e)


def test_univ():
    assert_true("g(a, b, c) =.. [G, A, B, C].")
    assert_true("g(a, b, c) =.. [g, a, b, c].")
    assert_true("X =.. [g, a, b, c], X = g(a, b, c).")
    assert_true("L = [a|X], X = [], Z =.. L, Z == a.")
    assert_true("L = [X, 1, 2], X = a, Z =.. L, Z == a(1, 2).")

def test_arg():
    assert_true("arg(1, g(a, b, c), a).")
    assert_true("arg(2, g(a, b, c), b).")
    assert_true("arg(3, g(a, b, c), c).")
    assert_false("arg(3, g(a, b, c), d).")
    assert_false("arg(0, g(a, b, c), X).")
    assert_false("arg(10, g(a, b, c), X).")
    assert_true("arg(1, g(a, b, c), X), X = a.")
    assert_true("arg(2, f(a, b, c), X), X = b.")
    assert_true("arg(3, h(a, b, c), X), X = c.")
    e = get_engine("""
        f(1, a).
        f(2, b).
        f(3, c).
    """)
    heaps = collect_all(e, "arg(X, g(a, b, c), A), f(X, A).")
    assert len(heaps) == 3
    assert_true("arg(X, h(a, b, c), b), X = 2.")
    assert_true("arg(X, h(a, b, g(X, b)), g(3, B)), X = 3, B = b.")
    assert_false("arg(X, a, Y).")
    prolog_raises("_", "arg(X, 1, Y)")

def test_copy_term():
    assert_true("copy_term(X, Y), X = 1, Y = 2.")
    assert_true("copy_term(a, a).")
    assert_false("copy_term(f(X), g(X)).")
    assert_true("copy_term(f(X), f(a)), X = b.")


def test_type_checks():
    assert_true("integer(123).")
    assert_true("integer(1000000000000000000000000000000000000).")
    assert_true("integer(-1000000000000000000000000000000000000).")
    assert_false("integer(a).")
    assert_false("integer(X).")
    assert_true("float(123.12).")
    assert_false("float(a).")
    assert_false("float(12).")
    assert_true("number(123).")
    assert_true("number(1000000000000000000000000000000000000).")
    assert_true("number(-1000000000000000000000000000000000000).")
    assert_true("number(42.42).")
    assert_false("number(abc).")
    assert_false("integer(a).")
    assert_false("integer(X).")
    assert_true("var(X).")
    assert_false("X = a, var(X).")
    assert_true("compound(g(a)).")
    assert_false("compound(gxx).")
    assert_false("compound(123).")
    assert_false("compound([]).")
    assert_false("compound(X).")
    assert_true("atom(a).")
    assert_true("atom('asdf').")
    assert_false("atom(12).")
    assert_false("atom(X).")
    assert_true("atomic('asdf').")
    assert_true("atomic(12.5).")
    assert_false("atomic(f(1, 2, 3)).")
    assert_false("atomic(X).")
    assert_false("callable(X).")
    assert_false("callable(1).")
    assert_true("callable(asdf).")
    assert_true("callable(asdf(a, b, c, d, e, f)).")
    assert_true("ground(a).")
    assert_true("ground(t(a, b, f(a, b, g(a, b)))).")
    assert_false("ground(t(a, b, f(a, b, g(a, X)))).")
    assert_true("X = 13, ground(t(a, b, f(a, b, g(a, X)))).")
    assert_false("ground(X).")

def test_repeat():
    assert_true("repeat, true.")
    e = Engine()
    py.test.raises(UnificationFailed,
        e.run, parse_query_term("repeat, !, fail."), 
                e.modulewrapper.user_module)
    # hard to test repeat differently
    e = get_engine('f :- repeat, !, fail.')
    assert_false('f.', e)
    assert_true('f; true.', e)

def test_exception_handling():
    assert_true("catch(f, E, true).")
    assert_true("catch(throw(error), E, true).")
    prolog_raises("_", "catch(true, E, fail), f")
    prolog_raises("_", "catch(throw(error(x)), error(failure), fail)")
    assert_true("catch(catch(throw(error), failure, fail), error, true).")
    assert_true("catch((X = y, throw(X)), E, E == y).")

def test_exception_forces_backtracking():
    assert_true("catch((X = 1, throw(f(X))), Y, (var(X), Y == f(1))), var(X).")

def test_between():
    assert_true("between(12, 15, 12).")
    assert_true("between(-5, 15, 0).")
    assert_false("between(12, 15, 6).")
    assert_false("between(12, 15, 16).")
    heaps = collect_all(Engine(), "between(1, 4, X).")
    assert len(heaps) == 4
    assert heaps[0]['X'].num == 1
    assert heaps[-1]['X'].num == 4

def test_is():
    assert_true("5 is 1 + 1 + 1 + 1 + 1.")

@py.test.mark.xfail
def test_parser_access():
    assert_true("current_op(200, xfx, **).")
    f = collect_all(Engine(), "current_op(200, Form, X).")
    assert len(f) == 2
    e = get_engine("""
        foo(a, b).
    """)
    assert_true("op(450, xfy, foo).", e)
    assert_true("a foo b.", e)
    assert_true("op(0, xfy, foo).", e)
    # XXX really a ParseError
    py.test.raises(Exception, assert_false, "a foo b.", e) 
    # change precedence of + for funny results :-)
    assert_true("14 is 2 + 3 * 4.", e)
    assert_true("op(350, xfy, +).", e)
    assert_true("20 is 2 + 3 * 4.", e)
    assert_true("op(500, xfy, +).", e)

def test_functor():
    assert_true("functor(f(a, b, c), f, 3).")
    assert_true("functor(f(a, b, c), X, Y), X=f, Y=3.")
    assert_true("functor(f, X, Y), X=f, Y=0.")
    assert_true("functor(1, X, Y), X=1, Y=0.")
    assert_true("functor(F, a, 0), F=a.")
    assert_true("functor(F, 12, 0), F=12.")
    assert_true("functor(F, 12.5, 0), F=12.5.")
    assert_true("functor(F, f, 4), F=f(1, 2, 3, 4).")
    assert_true("functor(F, g, 1), F=g(asdf).")
    assert_true("functor(F, g, 3), F=g(X, Y, 1), X = 12, Y = 34, ground(F).")

def test_standard_comparison():
    assert_true("X = Y, f(X, Y, X, Y) == f(X, X, Y, Y).")
    assert_true("X = Y, f(X, Y, X, Z) \\== f(X, X, Y, Y).")
    assert_true("""X \\== Y, ((X @< Y, X @=< X, X @=< Y, Y @> X);
                              (X @> Y, X @>= X, X @>= Y, Y @< X)).""")
    assert_true("'\\\\=='(f(X, Y), 12).")
    assert_true("X = f(a), Y = f(b), Y @> X.")

def test_structural_comparison():
    assert_true("1.0 @< 1.")
    assert_true("2.0 @< 1.")
    assert_true("10000000000000000000000000000000000.0 @< 1.")
    assert_true("1.0 @< 10000000000000000000000000000000000000000.")
    assert_true("1000000000000000000000000000000 @< 1000000000000000000000000000001.")
    assert_true("@<(1.0, 1).")

    assert_false("1.0 @> 1.")
    assert_false("2.0 @> 1.")
    assert_false("10000000000000000000000000000000000.0 @> 1.")
    assert_false("1.0 @> 10000000000000000000000000000000000000000.")
    assert_false("1000000000000000000000000000000 @> 1000000000000000000000000000001.")
    assert_false("@>(1.0, 1).")

    assert_false("1.0 @>= 1.")
    assert_false("2.0 @>= 1.")
    assert_false("10000000000000000000000000000000000.0 @>= 1.")
    assert_false("1.0 @>= 10000000000000000000000000000000000000000.")
    assert_false("1000000000000000000000000000000 @>= 1000000000000000000000000000001.")
    assert_false("@>=(1.0, 1).")

    assert_true("1.0 @=< 1.")
    assert_true("2.0 @=< 1.")
    assert_true("10000000000000000000000000000000000.0 @=< 1.")
    assert_true("1.0 @=< 10000000000000000000000000000000000000000.")
    assert_true("1000000000000000000000000000000 @=< 1000000000000000000000000000001.")
    assert_true("@=<(1.0, 1).")

def test_structural_comparison_2():
    e = Engine(load_system=True)
    assert_true("1 =@= 1.", e)
    assert_true("f(X) =@= f(A).", e)
    assert_false("f(X) =@= X.", e)
    assert_false("f(X, Y) =@= f(X, X).", e)
    assert_true("f(X, Y) =@= f(A, B).", e)
    assert_false("'=@='(1, 1.0).", e)
    assert_false("'=@='(a, b).", e)
    assert_true("'=@='(f(A, B), f(B, A)).", e)
    assert_true("'=@='(f(A, B), f(C, A)).", e)
    assert_false("a =@= A.", e)

def test_compare():
    assert_true("X = Y, compare(R, f(X, Y, X, Y), f(X, X, Y, Y)), R == '='.")
    assert_true("X = f(a), Y = f(b), compare(R, Y, X), R == '>'.")

def test_atom_length():
    assert_true("atom_length('abc', 3).")
    assert_true("atom_length('\\\\', 1).")
    assert_true("atom_length('abc', X), X = 3.")

def test_atom_concat():
    assert_true("atom_concat(ab, cdef, abcdef).")
    assert_true("atom_concat(ab, cdef, X), X = abcdef.")
    assert_true("atom_concat(ab, X, abcdef), X = cdef.")
    assert_true("atom_concat(X, cdef, abcdef), X = ab.")
    assert_true("atom_concat(1, Y, '1def'), Y = def.")
    heaps = collect_all(
        Engine(),
        "atom_concat(X, Y, abcd), atom(X), atom(Y).")
    assert len(heaps) == 5

@py.test.mark.xfail
def test_sub_atom():
    assert_true("sub_atom(abc, B, L, A, bc), B=1, L=2, A=0.")
@py.test.mark.xfail
def test_sub_atom2():
    assert_false("sub_atom(abc, B, 1, A, bc).")
@py.test.mark.xfail
def test_sub_atom3():
    assert_true("sub_atom(abcabcabc, 3, 3, A, abc), A=3.")
@py.test.mark.xfail
def test_sub_atom4():
    assert_true("sub_atom(abcabcabc, B, L, 3, abc), B=3, L=3.")

@py.test.mark.xfail
def test_sub_atom_with_non_var_sub():
    assert_true("sub_atom(abcabc, Before, Length, After, a), Before=3, Length=1, After=2.")
    assert_false("sub_atom(abcabc, Before, Length, After, b), Before==3, Length==1, After==2.")

@py.test.mark.xfail
def test_sub_atom_with_var_after():
    assert_true("sub_atom(abcabd, 2, 1, After, Sub), After=3, Sub=c.")
    assert_true("sub_atom(abcabc, Before, Length, After, Sub), Before=1, Length=3, After=2, Sub=bca.")
    assert_false("sub_atom(abcabc, 1, 3, After, Sub), Sub=abc.")

@py.test.mark.xfail
def test_sub_atom_var_sub_and_non_var_after():
    assert_true("sub_atom(abcabd, 2, 1, 3, Sub), Sub=c.")
    assert_true("sub_atom(abcabc, Before, Length, 2, Sub), Before=1, Length=3, Sub=bca.")
    assert_false("sub_atom(abcabc, 1, 3, 2, Sub), Sub=abc.")

def test_findall():
    assert_true("findall(X, (X = a; X = b; X = c), L), L == [a, b, c].")
    assert_true("findall(X + Y, (X = 1; X = 2), [1+A, 2+B]), A \== B.")
    e = get_engine("""
        app([], X, X).
        app([H | T1], T2, [H | T3]) :-
            app(T1, T2, T3).
    """)
    assert_true("findall(X+Y, app(X, Y, [1, 2, 3]), L), L == [[]+[1, 2, 3], [1]+[2, 3], [1, 2]+[3], [1, 2, 3]+[]].", e)

def test_findall_and_exception_bug():
    prolog_raises("instantiation_error", "findall(1, 0 is X, _)")


def test_ifthenelse():
    assert_false("true -> fail.")
    assert_false("true -> fail ; true.")
    assert_true("fail -> fail ; true.")
    assert_true("fail -> true ; true.")
    assert_true("(true -> fail ; true) ; true.")

    e = get_engine("f(x). f(y). f(z).")
    assert_false("f(c) -> true.", e)
    assert_false("f(X) -> X \\= x; f(z).", e)
    assert_true("f(X) -> X == x; f(z).", e)

    assert_true("""
    L = [X, Y],
    (L = []
    ->
        true
    ;
        [Head|Tail] = L
    ).
    """)

def test_cut_in_ifthenelse():
    e = get_engine("""
        f(X) :- ! -> fail.
        f(0).
    """)
    assert_true("f(0).", e)


def test_once():
    assert_true("once(repeat).")

def test_write_term():
    py.test.skip("test behaves funnily")
    prolog_raises("domain_error(write_option, E)",
                  "write_term(a, [quoted(af)])")
    prolog_raises("type_error(list, E)",
                  "write_term(a, asdf)")

def test_number_chars():
    assert_true("number_chars(123, ['1', '2', '3']).")
    assert_true("number_chars(123, X), X = ['1', '2', '3'].")
    prolog_raises("type_error(text, E)", "number_chars(X, [f(a)])")
    prolog_raises("type_error(list, E)", "number_chars(X, a)")
    prolog_raises("syntax_error(E)", "number_chars(X, ['-', '-'])")
    prolog_raises("syntax_error(E)", "number_chars(X, ['1', '-'])")
    prolog_raises("syntax_error(E)", "number_chars(X, ['.', '1', '-'])")
    prolog_raises("syntax_error(E)", "number_chars(X, ['1', '.', '2', '.'])")
    assert_true("number_chars(X, ['1', '2', '3']), X = 123.")
    prolog_raises("type_error(list, E)", "number_chars(123, 123)")
    prolog_raises("type_error(list, E)", "number_chars(b, a)")
    assert_true("number_chars(-123, ['-', '1', '2', '3']).")
    assert_true("number_chars(123.1, ['1', '2', '3', '.', '1']).")
    assert_true("number_chars(1000000000000000, ['1','0','0','0','0','0','0','0','0','0','0','0','0','0','0','0']).")
    prolog_raises("instantiation_error", "number_chars(X, Y)")
    prolog_raises("type_error(list, E)", "number_chars(1, ['a'|2])")
    prolog_raises("type_error(number, a)", "number_chars(a, X)")
    prolog_raises("type_error(number, a)", "number_chars(a, X)")
    prolog_raises("syntax_error(E)", "number_chars(A, ['-', '.', '1'])")

def test_atom_chars():
    assert_true("atom_chars(abc, X), X = [a, b, c].")
    assert_true("atom_chars(a12, [a, '1', '2']).")
    assert_true("atom_chars('', []).")
    prolog_raises("instantiation_error", "atom_chars(X, Y)")
    assert_true("atom_chars(X, [a, b, '1']), X = ab1.")
    prolog_raises("type_error(text, E)", "atom_chars(X, [a, b, '10'])")
    prolog_raises("type_error(list, E)", "atom_chars(X, a)")
    prolog_raises("type_error(text, E)", "atom_chars(X, [f(a)])")
    prolog_raises("type_error(list, E)", "atom_chars(X, f(a))")
    prolog_raises("type_error(text, E)", "atom_chars(X, [[]])")

def test_atom_chars_2():
    assert_true("atom_chars(ab, [a|B]), B = [b].")
