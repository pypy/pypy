from pypy.lang.prolog.interpreter.parsing import parse_file, TermBuilder, OrderTransformer
from pypy.lang.prolog.interpreter.parsing import parse_query_term


def test_simple():
    t = parse_file("""
h(X, Y, Z) :- -Y = Z.
""")
    builder = TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 1

def test_numeral():
    from pypy.lang.prolog.interpreter.term import Term, Atom, Var
    from pypy.lang.prolog.interpreter.engine import Engine
    t = parse_file("""
numeral(null). % end of line comment
numeral(succ(X)) :- numeral(X). % another one

add_numeral(X, null, X).
add_numeral(X, succ(Y), Z) :- add_numeral(succ(X), Y, Z).

greater_than(succ(null), null).
greater_than(succ(X), null) :- greater_than(X, null).
greater_than(succ(X), succ(Y)) :- greater_than(X, Y).
""")
    builder = TermBuilder()
    facts = builder.build(t)
    e = Engine()
    for fact in facts:
        print fact
        e.add_rule(fact)
    assert e.signature2function["add_numeral/3"].rulechain.rule.head.args[1].name == "null"
    four = Term("succ", [Term("succ", [Term("succ",
                [Term("succ", [Atom("null")])])])])
    e.run(parse_query_term("numeral(succ(succ(null)))."))
    term = parse_query_term(
        """add_numeral(succ(succ(null)), succ(succ(null)), X).""")
    e.run(term)
    var = Var(0).getvalue(e.heap)
    print var, e.heap
    # does not raise
    var.unify(four, e.heap)
    term = parse_query_term(
        """greater_than(succ(succ(succ(null))), succ(succ(null))).""")
    e.run(term)

def test_quoted_atoms():
    t = parse_file("""
        g('ASa0%!!231@~!@#%', a, []). /* /* /* * * * / a mean comment */
    """)
    builder = TermBuilder()
    facts = builder.build(t)

def test_parenthesis():
    t = parse_file("""
        g(X, Y) :- (g(x, y); g(a, b)), /* this too is a comment
*/ g(x, z).
    """)
    builder = TermBuilder()
    facts = builder.build(t)

def test_cut():
    t = parse_file("""
        g(X, /* this is some comment */
        Y) :- g(X), !, h(Y).
    """)
    builder = TermBuilder()
    facts = builder.build(t)
  
def test_noparam():
    t = parse_file("""
        test.
    """)
    builder = TermBuilder()
    facts = builder.build(t)

def test_list():
    t = parse_file("""
        W = [].
        X = [a, b, c, d, e, f, g, h].
        Y = [a|T].
        Z = [a,b,c|T].
    """)
    builder = TermBuilder()
    facts = builder.build(t)

def test_number():
    t = parse_file("""
        X = -1.
        Y = -1.345.
    """)
    builder = TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 2
    assert facts[0].args[1].num == -1
    assert facts[1].args[1].floatval == -1.345
    t = parse_file("""
        X = -1.
        arg(X, h(a, b, c), b), X = 2.
        arg(X, h(a, b, g(X, b)), g(3, B)), X = 3, B = b.
    """)

def test_chaining():
    t = parse_file("f(X) = X + X + 1 + 2.")
    builder = TermBuilder()
    facts = builder.build(t)
    t = parse_file("f(X) = X + X * 1 + 23 / 13.")
    facts = builder.build(t)
    t = parse_file("-X + 1.")
