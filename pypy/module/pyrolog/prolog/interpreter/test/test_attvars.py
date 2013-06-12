import py
from prolog.interpreter.test.tool import prolog_raises, \
assert_true, assert_false
from prolog.interpreter.parsing import get_engine
from prolog.interpreter.continuation import Engine
from prolog.interpreter.term import AttMap, Callable, AttVar


def test_not_attvar():
    assert_false("attvar(1).")
    assert_false("attvar(X).")
    assert_false("attvar(a).")
    assert_false("attvar((a --> b)).")

def test_put_attr_and_get_attr():
    assert_true("put_attr(X, m, 1).")
    assert_true("put_attr(X, m, abc).")
    assert_true("put_attr(X, m, Y).")
    prolog_raises("type_error(A, B)", "put_attr(X, 1, 1)")
    assert_true("put_attr(X, m1, 1), put_attr(X, m2, 1), put_attr(X, m1, 2), get_attr(X, m1, 2), get_attr(X, m2, 1).")
    assert_true("put_attr(X, b, 1), (put_attr(X, b, 1), fail; get_attr(X, b, 1)).")
    assert_true("put_attr(X, a, 1), Y = X, attvar(Y), attvar(X).")
    assert_true("put_attr(X, a, 1), X = Y, attvar(Y), attvar(X).")
    e = get_engine("g(X) :- !, put_attr(X, m, 1), fail.")
    assert_true("\+ g(X), \+ attvar(X).", e)
    prolog_raises("representation_error(_, _)", "put_attr(a, a, a)")

def test_attvar_and_put_attr():
    assert_true("put_attr(X, m, 1), attvar(X).")
    assert_false("attvar(X), put_attr(X, m, 1).")

def test_get_attr():
    assert_true("put_attr(X, m, 1), get_attr(X, m, 1).")
    assert_false("get_attr(X, m, 1).")
    prolog_raises("type_error(A, B)", "get_attr(X, 2, 2)")
    prolog_raises("instantiation_error", "get_attr(X, Y, 2)")
    assert_true("put_attr(X, m, 1), put_attr(X, m, 2), get_attr(X, m, 2).")

def test_backtracking():
    assert_false("(put_attr(X, m, 1), fail); attvar(X).")
    assert_false("put_attr(X, m, 2), (put_attr(X, m, 1), fail); get_attr(X, m, 2).")
    assert_true("(put_attr(X, b, 1), fail); \+ get_attr(X, b, 1).")
    assert_true("put_attr(X, a, 2), ((put_attr(X, b, 1), fail); get_attr(X, a, 2)), \+ get_attr(X, b, 1).")
    assert_true("put_attr(X, a, 2), ((put_attr(X, b, 1), put_attr(X, c, 3), fail); get_attr(X, a, 2)), \+ get_attr(X, b, 1), \+ get_attr(X, c, 3).")

def test_del_attributes():
    assert_true("del_attr(X, m).")
    assert_true("del_attr(a, m).")
    prolog_raises("instantiation_error", "del_attr(X, Y)")
    prolog_raises("type_error(A, B)", "del_attr(X, 1)")
    assert_false("put_attr(X, m, 1), del_attr(X, m), attvar(X).")
    assert_true("""put_attr(X, m, 1), put_attr(X, m2, 2), 
                    del_attr(X, m), attvar(X).""")
    assert_true("put_attr(X, m, 1), (del_attr(X, m), fail; true), get_attr(X, m, 1).")
    assert_true("put_attr(X, m, 1), (del_attr(X, m), fail; attvar(X)).")

def test_attr_unify_hook():
    e = get_engine("",
    m = """
    :- module(m, []).
    
    attr_unify_hook(Attr, Value) :-
        10 is Attr + Value.
    """)
    assert_false("put_attr(X, m, 1), X = 10.", e)
    assert_false("put_attr(X, m, 0), X = 11.", e)
    assert_true("put_attr(X, m, 1), X = 9.", e)
    assert_true("put_attr(X, m, 2), X = 8.", e)
    
    assert_true("X = 11, put_attr(Y, m, -1), Y = X.", e)
    assert_false("X = 11, put_attr(Y, m, 0), Y = X.", e)

    assert_false("put_attr(X, m, 11), (X = -1, fail; X = 0).", e)
    assert_true("put_attr(X, m, 11), (X = -1, fail; X = -1).", e)

def test_attr_unify_hook_complex_term():
    e = get_engine("",
    m = """
    :- module(m, []).
    attr_unify_hook(Attr, Value) :-
        assert(user:f(Value)).
    """)
    assert_true("put_attr(X, m, 1), put_attr(Y, m, 2), g(X, Y) = g(a, b).", e)
    assert_true("findall(X, f(X), [a, b]).", e)
    assert_true("abolish(f/1).", e)
    assert_true("""
    put_attr(X, m, 1), put_attr(Y, m, 2), put_attr(Z, m, 3), 
    f(Z, g(a, X, X, h(Z), Y)) = f(q, g(a, j, j, U, x)), U = h(q).
    """, e)
    assert_true("findall(X, f(X), [q, j, x]).", e)

def test_hook_not_defined():
    e = get_engine("",
    m = """
    :- module(m2, []).
    """)
    prolog_raises("existence_error(A, B)", "put_attr(X, bla, blub), X = 1")
    prolog_raises("existence_error(A, B)", "put_attr(X, m, blub), X = 1", e)

def test_multiple_hooks_one_not_defined():
    e = get_engine("", 
    m = """
    :- module(m, []).
    attr_unify_hook(_, _).
    """)
    prolog_raises("existence_error(_, _)", "put_attr(X, m, 1), put_attr(X, n, 2), X = a", e)
    prolog_raises("existence_error(_, _)", "put_attr(X, m, 1), put_attr(Y, n, 2), X = a, Y = X", e)
    prolog_raises("existence_error(_, _)", "put_attr(X, m, 1), put_attr(Y, n, 2), X = a, X = Y", e)

def test_attr_unify_hook_choice():
    e = get_engine("",
    m = """
    :- module(m, []).
    
    attr_unify_hook(Attr, f(Value)) :-
        Value = a; Value = b.
    """)
    assert_false("put_attr(X, m, 1), X = c.", e)
    assert_false("put_attr(X, m, 1), X = f(c).", e)
    assert_true("put_attr(X, m, 1), X = f(Y), Y = a.", e)
    assert_true("put_attr(X, m, 1), X = f(Y), Y = b.", e)

def test_run_hook_once():
    e = get_engine("",
    m = """
    :- module(m, []).
    attr_unify_hook(Attr, Value) :-
        assert(user:f(Value)).
    """)
    assert_true("put_attr(X, m, 1), X = a, X = a.", e)
    assert_true("findall(Y, f(Y), [a]).", e)
    assert_true("abolish(f/1).", e) # clear the database
    assert_true("""
    put_attr(X, m, 1), put_attr(Y, m, 2),
    X = a, (X = a, fail; Y = b),
    findall(A, f(A), [a, b]).
    """, e)
    assert_true("abolish(f/1).", e)
    assert_true("""
    put_attr(X, m, 1), put_attr(Y, m, 2),
    (f(X, b) = f(a, a); Y = b),
    findall(A, f(A), [b]).
    """, e)
    assert_true("abolish(f/1).", e)
    assert_true("""
    put_attr(X, m, 1), (X = a, fail; true),
    findall(Z, f(Z), [a]).
    """, e)

def test_symmetric():
    e = get_engine("",
    m = """
    :- module(m, []).
    attr_unify_hook(A, V) :-
        assert(user:f(A)).
    """)
    assert_true("put_attr(X, m, 1), put_attr(Y, m, 2), X = Y.", e)
    assert_true("f(1).", e)
    assert_true("abolish(f/1).", e)
    assert_true("put_attr(X, m, 1), put_attr(Y, m, 2), Y = X.", e)
    assert_true("f(2).", e)

def test_attvar_unification():
    e = get_engine("",
    m = """
    :- module(m, []).
    attr_unify_hook(Attr, Value) :-
        assert(user:f(Value)).
    """)
    assert_true("""
    put_attr(X, m, 1), put_attr(Y, m, 2),
    X = Y, X = a,
    findall(Z, f(Z), [W, a]).
    """, e)
    assert_true("abolish(f/1).", e)
    assert_true("""
    put_attr(X, m, 1), put_attr(Y, m, 2),
    X = Y, X = a, X = a, Y = a,
    findall(Z, f(Z), [W, a]).
    """, e)

def test_term_variables():
    assert_true("put_attr(X, m, 1), term_variables(X, [H]), attvar(H).")

def test_term_attvars():
    e = get_engine("",
    m = """
    :- module(m, []).
    attr_unify_hook(_, _).
    """)
    assert_true("term_attvars(a, []).")
    assert_true("term_attvars([], []).")
    assert_false("term_attvars([], 1).")
    assert_true("put_attr(X, m, 1), term_attvars(X, [X]).")
    assert_true("term_attvars(X,Y), Y == [].")
    assert_true("put_attr(X, m, 1), term_attvars(f(g(h(X)), X), [X]).")
    assert_true("put_attr(X, m, 1), put_attr(Y, m, 2), term_attvars(f(X, Y), [X, Y]).")
    assert_false("put_attr(X, m, 1), put_attr(Y, m, 2), X = Y, term_attvars(f(X, Y), [X, Y]).", e)
    assert_true("put_attr(X, m, 1), put_attr(Y, m, 2), X = Y, term_attvars(f(X, Y), [X]).", e)
    assert_true("put_attr(X, m, 1), put_attr(Y, m, 2), X = Y, term_attvars(f(X, Y), [Y]).", e)
    assert_true("put_attr(X, m, 1), term_attvars(f(A, X, B, X), [X]).")
    assert_true("put_attr(X, m, 1), Y = X, term_attvars(f(X, Y), [Y]).")
    assert_true("put_attr(X, m, 1), Y = X, term_attvars(f(X, Y), [X]).")
    assert_true("term_attvars(X, []), put_attr(X, m, 1).")
    assert_true("put_attr(X, m , 1), term_attvars(X, [X]), del_attr(X, m), term_attvars(X, []).")
    assert_true("put_attr(X, m, Y), term_variables(X, L), L == [X].")

def test_term_attvars_fail_fast():
    py.test.skip("")
    e = get_engine("""
    f(1, [X]) :-
        put_attr(X, m, 1).
    f(N, [X|R]) :-
        N >= 1,
        put_attr(X, m, 1),
        N1 is N - 1,
        f(N1, R).
    """)
    assert_false("f(10000, L), term_attvars(L, []).", e)

def test_copy_term_2():
    assert_true("put_attr(X, m, 1), copy_term(X, Y), attvar(Y).")
    assert_true("put_attr(X, m, 1), copy_term(X, Y), get_attr(Y, m, 1).")
    assert_false("put_attr(X, m, A), copy_term(X, Y), get_attr(Y, m, B), A == B.")

def test_copy_term_3():
    assert_true("copy_term(a, a, []).")
    assert_true("copy_term(X, Y, []), X \== Y.")
    assert_false("put_attr(X, foor, bar), copy_term(X, Y, _), X == Y.")
    assert_false("put_attr(X, foo, bar), copy_term(X, Y, Z), attvar(Y).")
    assert_true("put_attr(X, foo, bar), copy_term(X, Y, Z), \+ attvar(Y).")
    assert_true("put_attr(X, foo, bar), copy_term(X, Y, Z), Z == [put_attr(Y, foo, bar)], X \== Y.")
    assert_true("put_attr(X, foo, bar), put_attr(X, blar, blupp), copy_term(X, Y, Z), Z == [put_attr(Y, foo, bar), put_attr(Y, blar, blupp)], X \== Y.")
    
    e = get_engine("",
        m = """
        :- module(m, []).
        attr_unify_hook(_, _).
        """)
    assert_true("put_attr(X, m, 1), X = a, copy_term(X, a, Z), Z == [].", e)
    assert_true("put_attr(X, a, 1), put_attr(Y, b, 2), copy_term(f(X,Y), f(A, B), [put_attr(A, a, 1), put_attr(B, b, 2)]), Z \== f(X, Y).")
    assert_true("put_attr(X, a, Y), copy_term(X, A, [put_attr(A, a, Y)]).")
    assert_true("(put_attr(X, m, 1), fail; true), copy_term(X, A, []).")
    assert_true("copy_term(X, A, []), put_attr(X, m, 1), copy_term(X, A, [put_attr(A, m, 1)]).")

def xtest_get_attrs():
    assert_false("get_attrs(X, Y).")
    assert_false("get_attrs(a, Y).")
    assert_false("get_attrs(1, Y).")
    assert_true("put_attr(X, m, 1), get_attrs(X, att(m, 1, [])).")
    assert_false("put_attr(X, m, 1), get_attrs(f(X), att(m, 1, [])).")
    assert_true("put_attr(X, m, 1), put_attr(X, a, 2), get_attrs(X, att(m, 1, att(a, 2, []))).")
    assert_false("(put_attr(X, m, 1), fail; true), get_attrs(X, L).")
    assert_true("put_attr(X, m, 1), put_attr(Y, m, X), get_attrs(Y, att(m, X, [])), get_attrs(X, att(m, 1, [])).")

def test_del_attrs():
    assert_true("del_attrs(1).")
    assert_true("del_attrs(a).")
    assert_true("\+ attvar(X), del_attrs(X).")
    assert_false("put_attr(X, m, 1), del_attrs(X), get_attr(X, m, 1).")
    assert_true("put_attr(X, m, 1), del_attrs(X), \+ attvar(X).")
    assert_true("put_attr(X, m, 1), del_attrs(X), del_attrs(X).")
    assert_true("put_attr(X, m, 1), (del_attrs(X), fail; true), get_attr(X, m, 1).")
    assert_true("put_attr(X, m, 1), put_attr(X, m, 2), del_attrs(X), \+ attvar(X).")

def test_put_attrs():
    e = Engine(load_system=True)
    assert_false("put_attrs(X, []), attvar(X).", e)
    prolog_raises("representation_error(A, B)", "put_attrs(a, [])", e)
    prolog_raises("representation_error(A, B)", "put_attrs(a, att(m, 1, []))", e)
    assert_true("put_attrs(X, att(m, 1, [])), get_attr(X, m, 1).", e)
    assert_true("put_attrs(X, att(m, 1, att(n, W, []))), get_attr(X, m, 1), get_attr(X, n, W).", e)
    assert_false("put_attrs(X, att(m, 1, [])), fail; attvar(X).", e)
    assert_true("put_attr(X, m, 1), (put_attrs(X, att(m, 2, [])), fail; true), get_attr(X, m, 1).", e)
    assert_true("put_attr(X, m, 1), put_attrs(X, att(m, 2, [])), get_attr(X, m, 2).", e)

def test_more_than_one_attr_unify_hook():
    e = get_engine("",
    m = """
    :- module(m, []).

    attr_unify_hook(Attribute, f(X)) :-
        X = 1.
    attr_unify_hook(Attribute, f(X)) :-
        X = 2.
    """)
    assert_true("put_attr(X, m, a), X = f(1).", e)
    assert_true("put_attr(X, m, a), X = f(2).", e)
    assert_true("put_attr(X, m, a), X = f(Y), Y = 1.", e)
    assert_true("put_attr(X, m, a), X = f(Y), Y = 2.", e)
    assert_true("put_attr(X, m, a), X = f(Y), ((Y = 1, fail); Y = 2).", e)

"""
* tests regarding map support
"""

def test_basic_maps():
    m = AttMap()
    assert m.indexes == {}
    assert m.other_maps == {}
    assert m.get_index("not available") == -1

    map1 = m.with_extra_attribute("x")
    assert m.indexes == {}
    assert m.other_maps == {"x": map1}
    assert map1.indexes == {"x": 0}

    map2 = m.with_extra_attribute("x")
    assert m.indexes == {}
    assert map2.indexes == {"x": 0}
    assert map2 is map1 
    assert m.other_maps == {"x": map1}

    map3 = m.with_extra_attribute("y")
    assert m.indexes == {}
    assert m.other_maps == {"x": map1, "y": map3}
    assert m.other_maps["x"].indexes == {"x": 0}
    assert m.other_maps["y"].indexes == {"y": 0}

    map4 = map3.with_extra_attribute("z")
    assert map3.indexes == {"y": 0}
    assert map3.other_maps == {"z": map4}
    assert map4.indexes == {"z": 1, "y": 0}
    assert map4.other_maps == {}

def test_attvars_with_maps():
    a = AttVar()
    assert a.attmap is AttVar.attmap
    assert a.attmap.indexes == {}
    assert a.value_list == []

    val1 = Callable.build("1")
    a.add_attribute("x", val1)
    assert a.attmap is not AttVar.attmap
    assert a.attmap.indexes == {"x": 0}
    assert a.value_list == [val1]

    m1 = a.attmap
    a.del_attribute("x")
    assert m1 is a.attmap
    assert a.value_list == [None]

    a.add_attribute("x", val1)
    assert a.attmap is m1
    assert a.value_list == [val1]

    val2 = Callable.build("2")
    a.add_attribute("y", val2)
    m2 = a.attmap
    assert m2.indexes == {"x": 0, "y": 1}
    assert a.value_list == [val1, val2]

    a.del_attribute("x")
    assert a.attmap is m2
    assert a.value_list == [None, val2]

    a.del_attribute("y")
    assert a.attmap is m2
    assert a.value_list == [None, None]

    val3 = Callable.build("3")
    a.add_attribute("z", val3)
    m3 = a.attmap
    assert m3.indexes == {"x": 0, "y": 1, "z": 2}
    assert a.value_list == [None, None, val3]

    a.add_attribute("x", val1)
    assert a.attmap is m3
    assert a.value_list == [val1, None, val3]

def test_attvars_get():
    a = AttVar()
    t1 = a.get_attribute("x")
    assert t1[0] is None
    assert t1[1] == -1

    val1 = Callable.build("1")
    a.add_attribute("x", val1)
    t2 = a.get_attribute("x")
    assert t2[0] is val1
    assert t2[1] == 0

def test_several_attvars_same_map():
    a = AttVar()
    b = AttVar()
    assert a.attmap is b.attmap

    val1 = Callable.build("1")
    val2 = Callable.build("2")
    a.add_attribute("x", val1)
    assert a.attmap is not b.attmap
    b.add_attribute("x", val2)
    assert a.attmap is b.attmap

    a.add_attribute("y", val1)
    a.add_attribute("z", val2)
    assert a.attmap is not b.attmap

"""
* end tests regarding map support
"""

def test_integration_efficient_bools():
    e = get_engine("",
    swi_bool_pred = """
    :- module(swi_bool_pred, [negate/2]).

    negate(X, Y) :-
        ( nonvar(X)  -> negate3(X, Y)
        ; nonvar(Y)  -> negate3(Y, X)
        ; get_attr(X, swi_bool_pred, OtherX) -> Y = OtherX, X \== Y, put_attr(Y, swi_bool_pred, X)
        ; get_attr(Y, swi_bool_pred, OtherY) -> X = OtherY, X \== Y, put_attr(X, swi_bool_pred, Y)
        ; X \== Y, put_attr(Y, swi_bool_pred, X), put_attr(X, swi_bool_pred, Y)
        ).

    negate3(pred_true, pred_false).
    negate3(pred_false, pred_true).

    attr_unify_hook(Other, Value) :-
        (var(Value) -> (get_attr(Value, swi_bool_pred, Other2)
                            -> Other = Other2, Value \== Other
                            ; put_attr(Value, swi_bool_pred, Other)
                        )
                    ; negate3(Value, Other)).
    """)
    assert_true("swi_bool_pred:negate(X,Y), swi_bool_pred:negate(Y,Z), X==Z, Z=pred_true, X==pred_true, Y==pred_false.", e)
    assert_true("swi_bool_pred:negate(X,Y), swi_bool_pred:negate(Y,Z), X==Z, Z=pred_true, X==pred_true, Y==pred_false.", e)
    assert_true("swi_bool_pred:negate(X,Y), swi_bool_pred:negate(X2,Y2), X=X2, Y==Y2, Y=pred_false, X2==pred_true.", e)
    assert_true("swi_bool_pred:negate(X,Y), swi_bool_pred:negate(X,Z), Y==Z, Z=pred_true, X==pred_false.", e)
    assert_true("swi_bool_pred:negate(X,Y), swi_bool_pred:negate(Y,Z), \+ swi_bool_pred:negate(Z,X).", e)
    assert_true("swi_bool_pred:negate(X,Y), swi_bool_pred:negate(Y,Z), swi_bool_pred:negate(Z,X2), \+ X2=X.", e)
    assert_true("swi_bool_pred:negate(X,Y), swi_bool_pred:negate(Y,Z), X2=X, \+ swi_bool_pred:negate(Z,X2).", e)
    assert_false("swi_bool_pred:negate(X,X).", e)
