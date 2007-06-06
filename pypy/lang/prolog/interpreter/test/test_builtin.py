import py
from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder
from pypy.lang.prolog.interpreter.parsing import parse_query_term, get_engine
from pypy.lang.prolog.interpreter.error import UnificationFailed
from pypy.lang.prolog.interpreter.engine import Heap, Engine
from pypy.lang.prolog.interpreter import error
from pypy.lang.prolog.interpreter.test.tool import collect_all, assert_false, assert_true
from pypy.lang.prolog.interpreter.test.tool import prolog_raises

def test_fail():
    e = get_engine("""
        g(a).
        f(X) :- g(X), fail.
        f(a).
    """)
    heaps = collect_all(e, "f(X).")
    assert len(heaps) == 1

def test_not():
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
    assert_true("not((!, fail)).", e)
    assert_true("not(g(b, c)).", e)
    assert_false("not(g(a, a)).", e)
    assert_true("\\+(g(b, c)).", e)
    assert_false("\\+(g(a, a)).", e)
    assert_false("not(!).", e)

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
    py.test.raises(
        error.CatchableError,
        assert_true, "consult('/hopefully/does/not/exist').")

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
    assert f['B'].name == "b"
    f = assert_true("f(B, B).", e)
    assert f['B'].name == "b"
    assert_false("h(c, c).", e)
    f = assert_true("h(B, B).", e)
    assert f['B'].name == "a"

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

def test_or_with_cut():
    assert_false("((X = 1, !); X = 2), X = 2.")
    assert_true("((X = 1, !); X = 2), X = 1.")

def test_cut():
    e = get_engine("""
        f(0).
        f(X) :- Y is X - 1, !, f(Y).
        f(X) :- Y is X - 2, !, f(Y).
    """)
    assert_true("f(20).", e)

def test_call_cut():
    py.test.skip("cuts don't work properly in the presence of calls right now")
    e = get_engine("""
        f(X) :- call(X).
        f(!).
    """)
    heaps = collect_all(e, "f(!).")
    assert len(heaps) == 1


def test_term_construction():
    assert_true("g(a, b, c) =.. [G, A, B, C].")
    assert_true("g(a, b, c) =.. [g, a, b, c].")
    assert_true("X =.. [g, a, b, c], X = g(a, b, c).")
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
    assert_true("copy_term(X, Y), X = 1, Y = 2.")
    assert_true("copy_term(a, a).")
    assert_false("copy_term(f(X), g(X)).")
    assert_true("copy_term(f(X), f(a)), X = b.")

def test_type_checks():
    assert_true("integer(123).")
    assert_false("integer(a).")
    assert_false("integer(X).")
    assert_true("float(123.12).")
    assert_false("float(a).")
    assert_false("float(12).")
    assert_true("number(123).")
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
    py.test.raises(UnificationFailed,
        Engine().run, parse_query_term("repeat, !, fail."))
    # hard to test repeat differently

def test_exception_handling():
    assert_true("catch(f, E, true).")
    assert_true("catch(throw(error), E, true).")
    py.test.raises(error.CatchableError,
                   assert_true, "catch(true, E, fail), f.")
    py.test.raises(error.CatchableError,
                   assert_true, "catch(throw(error), failure, fail).")
    assert_true("catch(catch(throw(error), failure, fail), error, true).")

def test_between():
    assert_true("between(12, 15, 12).")
    assert_true("between(-5, 15, 0).")
    assert_false("between(12, 15, 6).")
    assert_false("between(12, 15, 16).")
    heaps = collect_all(Engine(), "between(1, 4, X).")
    assert len(heaps) == 4
    assert heaps[0]['X'].num == 1

def test_is():
    assert_true("5 is 1 + 1 + 1 + 1 + 1.")

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

def test_sub_atom():
    assert_true("sub_atom(abc, B, L, A, bc), B=1, L=2, A=0.")
    assert_false("sub_atom(abc, B, 1, A, bc).")
    assert_true("sub_atom(abcabcabc, 3, 3, A, abc), A=3.")
    assert_true("sub_atom(abcabcabc, B, L, 3, abc), B=3, L=3.")

def test_findall():
    assert_true("findall(X, (X = a; X = b; X = c), L), L = [a, b, c].")
    assert_true("findall(X + Y, (X = 1), L), L = [1+_].")

def test_ifthenelse():
    e = get_engine("f(x). f(y). f(z).")
    assert_false("f(c) -> true.", e)
    assert_true("f(X) -> X \\= x; f(z).", e)
    assert_false("true -> fail.", e)

def test_once():
    assert_true("once(repeat).")

def test_write_term():
    prolog_raises("domain_error(write_option, E)",
                  "write_term(a, [quoted(af)])")
    prolog_raises("type_error(list, E)",
                  "write_term(a, asdf)")
