import py
import os
from prolog.interpreter.test.tool import get_engine, assert_true, assert_false, prolog_raises
from prolog.interpreter.test.tool import create_file, delete_file, create_dir, delete_dir
from prolog.interpreter.test.tool import collect_all
from prolog.interpreter import term
from prolog.interpreter.signature import Signature
from prolog.interpreter.continuation import Engine
from prolog.interpreter.error import UncaughtError

def test_set_currently_parsed_module():
    e = get_engine("""
    f(a).
    """)
    m = e.modulewrapper
    assert m.current_module == m.user_module
    m.add_module("m1", [])
    assert "m1" in m.modules
    mod1 = m.modules["m1"]
    assert mod1.exports == []
    assert mod1.functions == {}
    atom = term.Callable.build("f")
    e.add_rule(atom)
    assert atom.signature() in mod1.functions

def test_module_exports():
    e = get_engine("""
    :- module(m, [g/2]).
    g(a, b).
    f(c, d, e).
    """)
    exports = e.modulewrapper.modules["m"].exports
    assert len(exports) == 1 and exports[0].eq(Signature("g", 2))

def test_use_module_with_file():
    e = get_engine("""
    :- use_module(m).
    """, True,
    m = """
    :- module(m, [f/0]).
    f.
    """)
    assert len(e.modulewrapper.modules) == 2
    assert_true("f.", e)

def test_use_module_locate_file():
    src1 = "src.pl"
    src2 = "src2"
    create_file(src1, ":- module(src, []).")
    create_file(src2, ":- module(src2, []).")
    try:
        assert_true("use_module('%s')." % src1)
        assert_true("use_module('%s')." % "src")
        # XXX some problems with unification, should be existence_error(_, _) 
        # instead of X
        prolog_raises("X", "use_module('%s')" % "src2.pl")
        assert_true("use_module('%s')." % "src2")
    finally:
        delete_file(src1)
        delete_file(src2)

def test_module_uses():
    e = get_engine("""
    :- use_module(b).
    """,
    a = """
    :- module(a, [h/1]).
    h(z).
    """,
    b = """
    :- module(b, [f/1]).
    :- use_module(a).
    f(X) :- h(X).
    g(a).
    """)
    assert len(e.modulewrapper.modules) == 3

def test_lookup():
    e = get_engine("""
    :- use_module(m).
    f(a) :- g(a, b).
    """,
    m = """
    :- module(m, [g/2]).
    g(a, b).
    h(w).
    """)
    f_sig = Signature.getsignature("f", 1)
    g_sig = Signature.getsignature("g", 2)
    h_sig = Signature.getsignature("h", 1)
    user = e.modulewrapper.modules["user"]
    m = e.modulewrapper.modules["m"]

    assert user.lookup(g_sig) == m.functions[g_sig]
    assert user.lookup(h_sig).rulechain is None
    assert m.lookup(g_sig) == m.functions[g_sig]
    assert m.lookup(f_sig).rulechain is None
    assert m.lookup(h_sig) == m.functions[h_sig]

def test_modules_use_module():
    e = get_engine("""
    :- use_module(m).
    f(X) :- g(X).
    f(b).
    h(a).
    """,
    m = """
    :- module(m, [g/1]).
    g(a).
    h(b).
    """)

    assert_true("f(a).", e)
    assert_true("f(b).", e)
    assert_true("h(a).", e)
    assert_false("h(b).", e)

def test_use_module_not_instantiated():
    prolog_raises("instantiation_error", "use_module(X)")
    prolog_raises("instantiation_error", "use_module(X, [])")

def test_modules_integration():
    e = get_engine("""
    :- use_module(m).
    f(X) :- g(X).
    h(b).
    both(X, Y) :- f(X), h(Y).
    """,
    m = """
    :- module(m, [g/1]).
    g(X) :- h(X).
    h(a).
    """)

    assert_true("findall(X, h(X), L), L = [b].", e)
    assert_true("both(X, Y), X == a, Y == b.", e)

def test_fail_and_retry_in_different_modules():
    e = get_engine("""
    :- use_module(m1).
    :- use_module(m2).
    """, 
    m1 = """
    :- module(m1, [f/1]).
    f(a).
    """, 
    m2 = """
    :- module(m2, [g/1]).
    g(a).
    """)
    assert_true(";((f(a), fail), g(a)).", e)

def test_builtin_module_or():
    e = get_engine("""
    :- use_module(m).
    t :- h, x.
    x.
    """,
    m = """
    :- module(m, [h/0]).
    h :- f; g.
    f.
    g.
    """)
    assert_true("t.", e)
    assert_true("not(x); h.", e)
    assert_true("h; x.", e)
    assert_true("(\+ h; \+ x); h.", e)

def test_builtin_module_and():
    e = get_engine("""
    :- use_module(m).
    t :- h, x.
    x.
    """,
    m = """
    :- module(m, [h/0]).
    h :- f, g.
    f.
    g.
    """)
    assert_true("t.", e)
    assert_true("x, h.", e)
    assert_false("h, \+ x.", e)
    assert_false("\+ x, h.", e)
    assert_false("\+ x, \+ h.", e)
    assert_true("\+ (x, \+ h).", e)

def test_catch_error():
    e = get_engine("""
    :- use_module(m).
    h :- catch(f, X, g).
    g.
    """,
    m = """
    :- module(m, [f/0]).
    f :- throw(foo).
    """)
    assert_true("h.", e)

def test_abolish():
    e = get_engine("""
    :- use_module(m).
    f(a).
    """,
    m = """
    :- module(m, [g/1]).
    g(a).
    """)

    assert_true("f(a).", e)
    assert len(e.modulewrapper.modules["user"].functions) == 2
    assert_true("abolish(f/1).", e)
    prolog_raises("existence_error(A, B)", "f(a)", e)
    assert_true("g(a).", e)
    assert_true("abolish(g/1).", e)
    prolog_raises("existence_error(A, B)", "g(a)", e)
    assert len(e.modulewrapper.modules["user"].functions) == 2
    assert len(e.modulewrapper.modules["m"].functions) == 1

def test_if():
    e = get_engine("""
    :- use_module(m).
    f(X) :- (X = b
        -> g(X)
        ; h(X)).
    g(c).
    """,
    m = """
    :- module(m, [h/1]).
    h(a).
    """)

    assert_true("f(a).", e)
    assert_false("f(b).", e)

def test_once():
    e = get_engine("""
    :- use_module(m).
    x :- f, h.
    h.
    """,
    m = """
    :- module(m, [f/0]).
    f :- once(g).
    g.
    """)
    assert_true("x.", e)

def test_module_switch_1():
    e = get_engine("""
    :- use_module(m).
    :- module(m).
    """,
    m = """
    :- module(m, [g/0]).
    g.
    f.
    """)
    assert e.modulewrapper.current_module.name == "m"
    assert_true("g.", e)
    assert_true("f.", e)

def test_module_switch_2():
    e = get_engine("""
    :- use_module(m).
    f.
    :- module(m).
    """,
    m = """
    :- module(m, []).
    g.
    """)

    assert e.modulewrapper.current_module.name == "m"
    prolog_raises("existence_error(X, Y)", "f", e)
    assert_true("g.", e)
    assert_true("module(user).", e)
    assert e.modulewrapper.current_module.name == "user"
    prolog_raises("existence_error(X, Y)", "g", e)
    assert_true("f.", e)

def test_switch_to_nonexistent_module():
    e = get_engine("""
    :- module(m).
    """)
    prolog_raises("existence_error(X, Y)", "x", e)
    assert_true("assert(x).", e)
    assert_true("x.", e)
    assert_true("module(user).", e)
    prolog_raises("existence_error(X, Y)", "x", e)

def test_module_assert_retract():
    e = Engine()
    assert_true("module(m).", e)
    assert_true("assert(x).", e)
    assert_true("asserta(y).", e)
    assert_true("x, y.", e)
    assert_true("module(user).", e)
    assert_false("retract(x).", e)
    assert_false("retract(y).", e)
    assert_true("assert(x).", e)
    assert_true("x.", e)
    assert_true("module(m).", e)
    assert_true("retract(x).", e)
    prolog_raises("existence_error(X, Y)", "x", e)
    assert_true("module(user).", e)
    assert_true("x.", e)

def test_module_prefixing():
    e = get_engine("""
    a.
    """,
    m = """
    :- module(m, []).
    f(a).
    f(b).
    """)
    assert_true("m:f(a), m:f(b).", e)
    assert_true("m:f(a), a.", e)
    prolog_raises("existence_error(X, Y)", "m:a", e)
    assert_true("module(m).", e)
    prolog_raises("existence_error(X, Y)", "a", e)
    assert_true("user:a.", e)

def test_prefix_non_existent_module():
    prolog_raises("existence_error(X, Y)", "a:b")

def test_prefix_module_in_other_directory():
    d = "__dir__"
    create_dir(d)
    m = "mod"
    create_file("%s/%s" % (d, m), """
    :- module(%s, [f/1]).

    f(a).
    """ % m)

    e = Engine()
    try:
        assert_true("use_module('%s/%s')." % (d, m), e)
        assert_true("current_module(%s)." % m, e)
        assert_true("%s:f(X), X == a." % m, e)
    finally:
        delete_dir(d)

def test_recursive_use_module():
    # if this test fails, one will recognize it by
    # waiting very long ...
    mod = "m"
    create_file(mod, """
    :- module(m, []).
    :- use_module(m).
    """)

    try:
        e = get_engine("""
        :- use_module(m).
        """)
    finally:
        delete_file(mod)

def test_alternating_recursive_import():
    mod = "m2"
    create_file(mod, """
    :- module(m2, [g/1]).
    :- use_module(m1).
    g(b).
    """)
    
    e = get_engine("""
    :- use_module(m1).
    """,
    m1 = """
    :- module(m1, [f/1]).
    f(a).
    :- use_module(m2).
    """)
    try:
        assert_true("f(X), X = a.", e)
        prolog_raises("existence_error(X, Y)", "g(X)", e)
    finally:
        delete_file(mod)

def test_recursive_ring_import():
    mod2 = "m2"
    mod3 = "m3"

    create_file(mod2, """
    :- module(m2, [g/1]).
    :- use_module(m3).
    g(a).
    """)

    create_file(mod3, """
    :- module(m3, [h/1]).
    :- use_module(m1).
    h(a).
    """)

    e = get_engine("""
    :- use_module(m1).
    z(a).
    """,
    m1 = """
    :- module(m1, [f/1]).
    f(a).
    :- use_module(m2).
    """)
    m = e.modulewrapper
    try:
        assert len(m.modules) == 4
        assert len(m.modules["user"].functions) == 2
        assert len(m.modules["m1"].functions) == 2
        assert len(m.modules["m2"].functions) == 2
        assert len(m.modules["m3"].functions) == 2
        assert_true("z(a).", e)
        assert_true("f(a).", e)
        assert_true("m1:f(a).", e)
        assert_true("m1:g(a).", e)
        assert_true("m2:g(a).", e)
        assert_true("m2:h(a).", e)
        assert_true("m3:h(a).", e)
        assert_true("m3:f(a).", e)
    finally:
        delete_file(mod2)
        delete_file(mod3)

def test_use_same_module_twice():
    # if this test fails, one will recognize it by
    # waiting very long ...
    e = get_engine(
    """
    :- use_module(m1).
    :- use_module(m2).
    h(X) :- g(X), f(X).
    """, True,
    m1 = """
    :- module(m1, [f/1]).
    f(a).
    """,
    m2 = """
    :- module(m2, [g/1]).
    :- use_module(m1).
    g(X) :- f(X).
    """)
    assert_true("h(X), X == a.", e)

def test_impl_use_module():
    from prolog.builtin.modules import impl_use_module
    from prolog.interpreter.heap import Heap
    filecontent = """
    :- module(blub, []).
    """
    e = Engine()
    h = Heap()
    m = e.modulewrapper
    create_file("blub.pl", filecontent)
    try:
        impl_use_module(e, m.user_module, h,
                term.Callable.build("blub.pl"))
        assert "blub" in e.modulewrapper.modules.keys()
    finally:
        delete_file("blub.pl")

    create_file("blub", filecontent)
    m.modules = {}
    m.seen_modules = {}
    try:
        impl_use_module(e, m.user_module, h, term.Callable.build("blub"))
        assert "blub" in m.modules.keys()
    finally:
        delete_file("blub")

def test_add_library_dir():
    e = Engine()
    m = e.modulewrapper
    assert m.libs == []
    prolog_raises("existence_error(X, Y)", "add_library_dir('does_not_exist')", e)

    lib1 = "__lib1__"
    lib2 = "__lib2__"
    create_dir(lib1)
    create_dir(lib2)

    try:
        assert_true("add_library_dir('%s')." % lib1, e)
        assert_true("add_library_dir('%s')." % lib2, e)
        assert len(m.libs) == 2
    finally:
        delete_dir(lib1)
        delete_dir(lib2)

def test_library_directory():
    e = Engine()
    m = e.modulewrapper
    assert m.libs == []
    libs = collect_all(e, "library_directory(X).")
    assert len(libs) == 0

    tempdir1 = "__tempdir1__"
    tempdir2 = "__tempdir2__"
    create_dir(tempdir1)
    create_dir(tempdir2)

    try:
        assert_true("add_library_dir('%s')." % tempdir1, e)
        assert_true("add_library_dir('%s')." % tempdir2, e)
        libs = collect_all(e, "library_directory(X).")
        assert len(libs) == 2
        assert len(m.libs) == 2
    finally:
        delete_dir(tempdir1)
        delete_dir(tempdir2)

def test_use_library_errors():
    prolog_raises("instantiation_error", "use_module(library(X))")
    prolog_raises("existence_error(_, _)", "use_module(library(does_not_exist_))")
    prolog_raises("existence_error(source_sink, _)", "use_module(sdfdsfsf(sadasd))")

def test_library_dir_single_query():
    e = Engine()
    tempdir = "__temp__"
    create_dir(tempdir)
    try:
        assert_true("add_library_dir('%s')." % tempdir, e)
        assert_true("library_directory('%s')." % tempdir, e)
    finally:
        delete_dir(tempdir)

def test_library_usage():
    tempdir = "__tempdir__"
    mod = "m"
    mod2 = "m2"

    create_dir(tempdir)
    create_file(tempdir + "/" + mod, """
    :- module(m, [f/1]).
    f(a).
    g.
    """)

    create_file(tempdir + "/" + (mod2 + ".pl"), """
    :- module(m2, [f/1]).
    f(a).
    g.
    """)

    try:
        e = get_engine(":- add_library_dir('%s')." % tempdir)
        assert len(e.modulewrapper.libs) == 1
        assert_true("use_module(library('%s'))." % mod, e)
        assert_true("f(a).", e)
        prolog_raises("existence_error(X, Y)", "g", e)

        e = get_engine(":- add_library_dir('%s')." % tempdir)
        assert len(e.modulewrapper.libs) == 1
        assert_true("use_module(library('%s'))." % mod2, e)
        assert_true("f(a).", e)
        prolog_raises("existence_error(X, Y)", "g", e)
    finally:
        delete_dir(tempdir)

def test_library_load_priority():
    tempdir = "__tempdir__"
    mod = "m"

    create_dir(tempdir)
    create_file(tempdir + "/" + mod, """
    :- module(m, [f/1]).
    f(a).
    g.
    """)

    create_file(mod, """
    :- module(m, [f/1, g]).
    f(b).
    g.
    """)

    try:
        e = get_engine(":- add_library_dir('%s')." % tempdir)
        assert len(e.modulewrapper.libs) == 1
        assert_true("use_module(library('%s'))." % mod, e)
        assert_true("f(a).", e)
        prolog_raises("existence_error(X, Y)", "g", e)
    finally:
        delete_dir(tempdir)
        delete_file(mod)

def test_add_library_twice():
    e = Engine()
    lib1 = "__lib1__"
    lib2 = "__lib2__"
    create_dir(lib1)
    create_dir(lib2)
    try:
        assert_true("add_library_dir('%s')." % lib1, e)
        assert len(e.modulewrapper.libs) == 1
        assert_true("add_library_dir('%s')." % lib1, e)
        assert len(e.modulewrapper.libs) == 1
        assert_true("add_library_dir('%s')." % lib2, e)
        assert len(e.modulewrapper.libs) == 2
    finally:
        delete_dir(lib1)
        delete_dir(lib2)

def test_import_list_simple():
    e = get_engine("""
    :- use_module(m, [f/1, g/0]).
    h(X) :- f(X), g.
    """,
    m = """
    :- module(m, [f/1, g/0]).
    f(a).
    g.
    q.
    """)
    assert_true("h(a).", e)
    prolog_raises("existence_error(X, Y)", "q", e)

def test_empty_import_list():
    e = get_engine("""
    :- use_module(m, []).
    """,
    m = """
    :- module(m, [f/1, g/0]).
    f(a).
    g.
    q.
    """)
    assert len(e.modulewrapper.modules["user"].functions) == 0
    prolog_raises("existence_error(X, Y)", "f(a)", e)
    prolog_raises("existence_error(X, Y)", "g", e)
    prolog_raises("existence_error(X, Y)", "q", e)

def test_nonexisting_predicates_in_import_list():
    e = get_engine("""
    :- use_module(m, [z/0, g/1]).
    """,
    m = """
    :- module(m, [f/1, g/0]).
    f(a).
    g.
    q.
    """)
    prolog_raises("existence_error(X, Y)", "z", e)
    prolog_raises("existence_error(X, Y)", "g(A)", e)

def test_existing_system_module():
    e = Engine(load_system=True)
    assert e.modulewrapper.modules.has_key("system")

# needs list module
def test_access_system_predicate():
    e = Engine(load_system=True)
    assert_true("append([1], [2], [1, 2]).", e)

# needs list and dcg module
def test_term_expansion():
    e = get_engine("""
    a --> [b].
    f(X) :-
        X = x;
        X = y.
    """,
    load_system=True)
    assert_true("a([b], []).", e)
    assert_false("a([], []).", e)
    assert_false("f(a).", e)
    assert_false("f(b).", e)
    assert_true("f(x).", e)
    assert_true("f(y).", e)
    assert_true("assert((g --> [h])).", e)
    prolog_raises("existence_error(A, B)", "g([h], [])", e)
    assert_true("g --> [h].", e)
    assert_false("g --> [].", e)
    assert_true("term_expand((z --> [q]), R).", e)
    prolog_raises("existence_error(A, B)", "z([q], [])", e)

def test_overwrite_term_expand():
    e = get_engine("""
    term_expand(A, A).
    a --> [b].
    """,
    load_system=True)
    assert_true("(X --> Y), X == a, Y == [b].", e)
    assert_true("system:term_expand((a --> [b]), R), assert(R).", e)
    assert_true("a([b], []).", e)
    assert_true("term_expand((a --> b), R), assert(R).", e)
    assert_true("(A --> b), A == a.", e)

def test_module_with_dcg():
    e = get_engine("""
    :- use_module(m).
    """,
    m = """
    :- module(m, [f/1]).
    f(X) :- a(X, []).
    a --> [b], c, [d].
    c --> [1].
    c --> [x, y, z].
    """,
    load_system=True)
    assert_true("f([b, 1, d]).", e)
    assert_true("f([b, x, y, z, d]).", e)
    assert_false("f([b, y, z, d]).", e)
    assert_false("f([]).", e)

def test_assert_dcg():
    e = Engine(load_system=True)
    assert_true("assert((a --> b)).", e)
    assert_true("a --> b.", e)

def test_term_expand_fail():
    # Since self-defined term_expand fails
    # the system term_expand should be called.
    e = get_engine("""
    term_expand(A, A) :- fail.
    a --> [b].
    """,
    load_system=True)
    assert_true("a([b], []).", e)

def test_assert_other_module():
    e = Engine()
    assert_true("assert(m:f(a)).", e)
    assert len(e.modulewrapper.modules) == 2
    assert_true("m:f(a).", e)
    prolog_raises("existence_error(_, _)", "f(a)", e)
    assert_true("module(m).", e)
    assert_true("f(a).", e)
    assert_true("module(user).", e)
    prolog_raises("existence_error(_, _)", "f(a)", e)

def test_asserta_other_module():
    e = Engine()
    assert_true("asserta(m:f(a)).", e)
    assert len(e.modulewrapper.modules) == 2
    assert_true("m:f(a).", e)
    prolog_raises("existence_error(_, _)", "f(a)", e)
    assert_true("module(m).", e)
    assert_true("f(a).", e)
    assert_true("module(user).", e)
    prolog_raises("existence_error(_, _)", "f(a)", e)

def test_retract_other_module():
    e = get_engine("",
    m = """
    :- module(m, []).
    f(a).
    f(b).
    """)
    assert_true("m:f(a), m:f(b).", e)
    assert_true("retract(m:f(a)).", e)
    assert_false("retract(m:f(a)).", e)
    assert_false("m:f(a).", e)
    assert_true("m:f(b).", e)
    assert_true("retract(m:f(b)).", e)
    prolog_raises("existence_error(_, _)", "f(b)", e)

def test_abolish_other_module():
    e = get_engine("",
    m = """
    :- module(m, []).
    f(a).
    f(b).
    g(c).
    """)
    assert_true("m:f(a), m:f(b), m:g(c).", e)
    assert_true("abolish(m:f/1).", e)
    prolog_raises("existence_error(_, _)", "m:f(X)", e)
    assert_true("m:g(c).", e)
    assert_true("abolish(m:g/1).", e)
    prolog_raises("existence_error(_, _)", "m:g(c)", e)
    assert_true("abolish(m:g/1).", e)

def test_assert_rule_into_other_module():
    e = get_engine("""
    :- use_module(m).
    """,
    m = """
    :- module(m, []).
    """)
    assert_true("m:assert(a).", e)
    assert_true("m:a.", e)
    prolog_raises("existence_error(_, _)", "a", e)

    assert_true("m:assert(user:b).", e)
    assert_true("b.", e)
    prolog_raises("existence_error(_, _)", "m:b", e)

def test_assert_rule_into_other_module_2():
    e = get_engine("""
    :- use_module(m).
    """,
    m = """
    :- module(m, [f/1]).

    f(Rule) :-
        assert(Rule).
    """)
    assert_true("f(g(a)).", e)
    prolog_raises("existence_error(_, _)", "g(a)", e)
    assert_true("m:g(a).", e)

def test_retract_rule_from_other_module():
    e = get_engine("""
    :- use_module(m).
    """,
    m = """
    :- module(m, []).
    a.
    """)
    assert_false("retract(a).", e)
    assert_true("m:retract(a).", e)
    assert_false("m:retract(a).", e)

def test_abolish_from_other_module():
    e = get_engine("""
    :- use_module(m).
    """,
    m = """
    :- module(m, []).
    a.
    """)
    assert_true("m:abolish(a/0).", e)
    prolog_raises("existence_error(_, _)", "m:a", e)
def test_call_other_module():
    e = get_engine("",
    m = """
    :- module(m, []).
    f(a).
    """)
    assert_true("call(m:f(X)), X = a.", e)
    prolog_raises("existence_error(_, _)", "f(X)", e)

def test_once_other_module():
    e = get_engine("",
    m = """
    :- module(m, []).
    f(a).
    """)
    assert_true("once(m:f(X)), X = a.", e)
    prolog_raises("existence_error(_, _)", "f(X)", e)

def test_file_parsing():
    e = get_engine("""
    :- use_module(m).
    :- use_module(m).
    """,
    create_files=True,
    m = """
    :- module(m, []).
    :- assert(user:f(a)).
    """)
    assert_true("findall(X, f(X), [a]).", e)

def test_this_module():
    e = get_engine(":- module(a).")
    assert_true("this_module(user).")
    assert_true("this_module(a).", e)
    assert_true("this_module(X), X == user.")

def test_this_module_2():
    e = get_engine("""
    :- use_module(m).
    g(X) :- f(X).
    """,
    m = """
    :- module(m, [f/1]).
    f(X) :-
        this_module(X).
    """,
    n = """
    :- module(n).
    :- use_module(m).
    g(X) :- f(X).
    """)
    assert_true("g(X), X == user.", e)

def test_meta_function():
    e = get_engine("""
    :- meta_predicate f(:), g('?'), h(0).

    f(X) :- X = foobar.
    a(FooBar).
    """)
    user = e.modulewrapper.modules["user"]
    assert len(user.functions) == 4

    for key in user.functions.keys():
        assert key.name in ["f","g","h","a"]
        assert key.numargs == 1
        if key.name in ["f", "g", "h"]:
            assert user.functions[key].meta_args != []
        else:
            assert not user.functions[key].meta_args == []

def test_meta_predicate():
    e = get_engine("""
    :- use_module(mod).
    """,
    mod = """
    :- module(mod, [test/1, test2/2]).
    :- meta_predicate test(:), test2(:, -).

    test(X) :- X = _:_.
    test2(M:A, M:A).
    """)
    
    assert_true("test(blar).", e)
    assert_false("test2(f, f).", e)
    assert_true("test2(f, user:f).", e)
    assert_true("test2(f(A, B, C), user:f(A, B, C)).", e)

def test_meta_predicate_2():
    e = get_engine("",
    m = """
    :- module(m, [f/4]).
    :- meta_predicate f(:, :, '?', '?').

    f(M1:G1, M2:G2, M1, M2).
    """)
    # setup
    assert_true("module(x).", e)
    assert_true("use_module(m).", e)
    # real tests
    assert_true("f(a, b, x, x).", e)
    assert_false("f(1:a, 2:b, x, x).", e)
    assert_true("f(1:a, 2:b, 1, 2).", e)
    assert_true("m:f(a, b, m, m).", e)
    assert_false("m:f(1:a, 2:b, m, m).", e)
    assert_true("m:f(1:a, 2:b, 1, 2).", e)

def test_meta_predicate_prefixing():
    e = get_engine("""
    :- use_module(mod).
    """,
    mod = """
    :- module(mod, [f/2]).
    :- meta_predicate f(:, '?').

    f(X, M) :-
        X = M:_,
        M =.. [A|_],
        A \== ':'.
    """)
    assert_true("f(a, user).", e)
    assert_true("f(user:a, user).", e)
    assert_true("mod:f(a, mod).", e)
    assert_true("mod:f(user:a, user).", e)
    assert_true("mod:f(mod:user:a, mod).", e)

def test_meta_predicate_module_chaining():
    m1 = "m1.pl"
    m2 = "m2.pl"
    m3 = "m3.pl"
    try:
        create_file(m1, """
        :- module(m1, [f/2]).
        :- meta_predicate f(:, '?').
        f(M:_, M).
        """)

        create_file(m2, """
        :- module(m2, [g/2]).
        :- use_module(m1).
        g(X, Y) :- f(X, Y).
        """)

        create_file(m3, """
        :- module(m3, [h/2]).
        :- meta_predicate h(:, ?).
        :- use_module(m2).
        h(X, Y) :- g(X, Y).
        """)
        
        e = get_engine("""
        :- use_module(m2).
        :- use_module(m3).
        """)

        assert_true("g(a, X), X == m2.", e)
        assert_true("g(user:a, X), X == user.", e)
        assert_true("h(a, X), X == user.", e)
        assert_true("m3:h(a, X), X == m3.", e)
        assert_true("m3:h(user:a, X), X == user.", e)
    finally:
        delete_file(m1)
        delete_file(m2)
        delete_file(m3)

def test_meta_predicate_colon_predicate():
    e = get_engine("""
    :- use_module(m).
    """,
    m = """
    :- module(m, [:/3]).
    :- meta_predicate :(:, :, '?'), :(:, :).

    :(A, B, C) :-
        A = X:_,
        B = Y:_,
        C = (X, Y).
    """)
    assert_true(":(a, blub:b, (user, blub)).", e)
    assert_true(":(1, a:2, (user, a)).", e)
    assert_true(":(a:1.234, 2, (a, user)).", e)
    assert_true(":(a:9999999999999999999999999999999999999999999999999, b:2, (a, b)).", e)

def test_meta_predicate_errors():
    py.test.skip("todo")
    prolog_raises("instantiation_error", "meta_predicate f(X)")
    prolog_raises("instantiation_error", "meta_predicate X")
    prolog_raises("domain_error(_, _)", "meta_predicate f(blub)")

    m = "mod"
    create_file(m, """
    :- module(%s, []).
    :- meta_predicate X.
    """ % m)
    e = Engine()
    try:
        try: # XXX strange behaviour, can't catch
            prolog_raises("instantiation_error", "use_module(%s)" % m)
        except UncaughtError:
            pass
        assert e.modulewrapper.current_module.name == "user"
    finally:
        delete_file(m)


def test_current_module():
    e = get_engine("""
    length([], 0).
    length([_|T], R) :-
        length(T, R1),
        R is R1 + 1.
    """,
    m1 = ":- module(m1, []).",
    m2 = ":- module(m2, []).",
    m3 = ":- module(m3, []).")
    assert_true("current_module(user).", e)
    assert_true("current_module(m1).", e)
    assert_true("current_module(m2).", e)
    assert_true("current_module(m3).", e)
    assert_true("findall(X, current_module(X), L), length(L, 4).", e)

    e = Engine()
    assert_true("findall(X, current_module(X), L), L == [user].", e)
    assert_false("current_module(1).")
    assert_false("current_module(some_strange_thing).")

def test_engine_current_module_after_invalid_import():
    m = "m.pl"
    create_file(m, """
    :- module(m, [f(a)]).
    f(a).
    """)
    e = Engine()
    try:
        try: # XXX strange, prolog_raises does not catch the error
            prolog_raises("type_error(_, _)", "use_module(m)", e)
        except UncaughtError:
            pass
        assert e.modulewrapper.current_module.name == "user"
    finally:
        delete_file(m)
        
def test_importlist_with_not_existing_rule():
    e = Engine()
    m = "mod"
    create_file(m, """
    :- module('%s', [f/1]).
    """ % m)
    try:
        prolog_raises("import_error(mod, 'f/1')", "use_module(%s)" % m, e)
        assert e.modulewrapper.current_module.name == "user"
    finally:
        delete_file(m)

def test_numeric_module():
    prolog_raises("domain_error(_, _)", "assert(:(1, 2))")
    prolog_raises("domain_error(_, _)", "assert(:(1.2, 2.2))")

def test_load_broken_module_twice():
    e = Engine()
    m = "mod"
    create_file(m, """
    :- module(%s, [f/1]).
    """ % m)
    try:
        prolog_raises("import_error(mod, 'f/1')", "use_module('%s')" % m, e)
        assert_true("use_module('%s')." % m, e)
        assert m in e.modulewrapper.modules
    finally:
        delete_file(m)

def test_retract_module_name_is_not_atom():
    assert_false("retract(f(x):f(y)).")

def test_importlist_intersection():
    e = get_engine("""
    :- use_module(m, []).
    """, 
    m = """
    :- module(m, [f/1]).
    f(a).
    g(a).
    """)
    prolog_raises("existence_error(procedure, '/'('f', 1))", "f(a)", e)
    prolog_raises("existence_error(procedure, '/'('g', 1))", "g(a)", e)

    e = get_engine("""
    :- use_module(m, [g/1]).
    """, 
    m = """
    :- module(m, [f/1]).
    f(a).
    g(a).
    """)
    prolog_raises("existence_error(procedure, '/'('f', 1))", "f(a)", e)
    prolog_raises("existence_error(procedure, '/'('g', 1))", "g(a)", e)

    e = get_engine("""
    :- use_module(m, [f/1, g/1]).
    """, 
    m = """
    :- module(m, [f/1]).
    f(a).
    g(a).
    """)
    assert_true("f(a).", e)
    prolog_raises("existence_error(procedure, '/'('g', 1))", "g(a)", e)

def test_modules_without_module_declaration():
    m1 = "mod1"
    m2 = "mod2"

    create_file(m1, """
    :- use_module(%s).
    f(a).
    """ % m2)

    create_file(m2, """
    :- use_module(%s).
    g(a).
    """ % m1)

    e = Engine()
    try:
        assert_true("use_module(%s)." % m1, e)
        assert_true("f(a).", e)
        assert_true("g(a).", e)
        assert len(e.modulewrapper.modules) == 1
        assert "user" in e.modulewrapper.modules
    finally:
        delete_file(m1)
        delete_file(m2)
