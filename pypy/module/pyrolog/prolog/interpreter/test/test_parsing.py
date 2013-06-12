from prolog.interpreter.signature import Signature
from prolog.interpreter.parsing import parse_file, TermBuilder, OrderTransformer
from prolog.interpreter.parsing import parse_query_term
from prolog.interpreter.heap import Heap


def test_simple():
    t = parse_file("""
h(X, Y, Z) :- -Y = Z.
""")
    builder = TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 1

def test_numeral():
    from prolog.interpreter.term import Callable, Atom, BindingVar
    from prolog.interpreter.continuation import Engine
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
    m = e.modulewrapper
    for fact in facts:
        print fact
        e.add_rule(fact)
    assert m.modules["user"].lookup(Signature.getsignature("add_numeral", 3)).rulechain.head.argument_at(1).name() == "null"
    four = Callable.build("succ", [Callable.build("succ", [Callable.build("succ",
                [Callable.build("succ", [Callable.build("null")])])])])
    e.run(parse_query_term("numeral(succ(succ(null)))."), m.user_module)
    term = parse_query_term(
        """add_numeral(succ(succ(null)), succ(succ(null)), X).""")
    e.run(term, m.user_module)
    hp = Heap()
    var = BindingVar().dereference(hp)
    # does not raise
    var.unify(four, hp)
    term = parse_query_term(
        """greater_than(succ(succ(succ(null))), succ(succ(null))).""")
    e.run(term, m.user_module)

def test_quoted_atoms():
    t = parse_file("""
        g('ASa0%!!231@~!@#%', a, []). /* /* /* * * * / a mean comment */
    """)
    builder = TermBuilder()
    fact, = builder.build(t)
    assert fact.argument_at(0).name()== 'ASa0%!!231@~!@#%'
    assert fact.argument_at(1).name()== 'a'
    assert fact.argument_at(2).name()== '[]'
    t = parse_file("""
        'a'.
        a.
    """)
    builder = TermBuilder()
    fact1, fact2, = builder.build(t)
    assert fact1.name()== fact2.name()

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

def test_braces():
    t = parse_file("""
        W = {}.
        X = {}(a, b, c).
        Y = {a, b, c}.
    """)
    builder = TermBuilder()
    facts = builder.build(t)

    t = parse_file("""
        {a, b, c}.
    """)
    builder = TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 1
    assert facts[0].name() == "{}"
    assert facts[0].argument_count() == 1
    assert facts[0].argument_at(0).name() == ","
    assert facts[0].argument_at(0).argument_count() == 2

def test_number():
    t = parse_file("""
        X = -1.
        Y = -1.345.
    """)
    builder = TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 2
    assert facts[0].argument_at(1).num == -1
    assert facts[1].argument_at(1).floatval == -1.345
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

def test_block():
    t = parse_file(":- block f('-', '?'), f('-', '?', '?'), a.")
    builder = TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 1
    assert facts[0].name() == ":-"
    assert facts[0].argument_at(0).name() == "block"
    
def test_meta_predicate():
    t = parse_file(":- meta_predicate f(:), f(2, '+', '+'), f(:, '-'), a.")
    builder = TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 1
    assert facts[0].name() == ":-"
    assert facts[0].argument_at(0).name() == "meta_predicate"
    
def test_block_comment_basic():
    t = parse_file("""
        g(a).
        /*
        a.
        b.
        f(x).
        */
        h(e).
    """)
    builder = TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 2

def test_block_comment_stars_and_stripes():
    t = parse_file("""
        the_first_fact.
        /* this is some random stuff ....

            * / * / * / ******************** /*

        */
        some_fact.
        some_other_fact.

        /**************
        
            skjdhfjskdfhskjfd.

        *************/
    """)
    builder = TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 3

def test_many_block_comments():
    t = parse_file("""

        a.

        /*
            b.
            c.
            d.
        */

        a2.

        /**********************************************

            d.
            e.

        ********************************************** */

        a3.

        /*
            x. 
            y.
            z.
        * */

        /*
        f.
        **/

        a4.

    """)
    builder =  TermBuilder()
    facts = builder.build(t)
    assert len(facts) == 4
    assert facts[0].name() == "a"
    assert facts[1].name() == "a2"
    assert facts[2].name() == "a3"
    assert facts[3].name() == "a4"


