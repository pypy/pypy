import os

from pypy.interpreter.pyparser import pythonparse
from pypy.interpreter.pyparser.astbuilder import AstBuilder
from pypy.interpreter.pyparser.pythonutil import ast_from_input, build_parser_for_version
from pypy.interpreter.stablecompiler.transformer import Transformer
import pypy.interpreter.stablecompiler.ast as test_ast
import pypy.interpreter.astcompiler.ast as ast_ast

flatten = ast_ast.flatten

import py.test

from pypy.interpreter.astcompiler import ast

from fakes import FakeSpace
from expressions import TESTS, SINGLE_INPUTS, EXEC_INPUTS

def arglist_equal(left,right):
    """needs special case because we handle the argumentlist differently"""
    for l,r in zip(left,right):
        if type(l)==str and isinstance(r,ast_ast.AssName):
            if l!=r.name:
                print "Name mismatch", l, r.name
                return False
        elif type(l)==tuple and isinstance(r,ast_ast.AssTuple):
            if not arglist_equal(l,r.nodes):
                print "Tuple mismatch"
                return False
        else:
            print "Type mismatch", repr(l), repr(r)
            print "l is str", repr(l), type(l)==str
            print "r is AssName", repr(r), isinstance(r,ast_ast.AssName)
            print "left is", repr(left)
            print "right is", repr(right)
            return False
    return True


def nodes_equal(left, right, check_lineno=False):
    if isinstance(left, ast_ast.Node) and isinstance(right, ast_ast.Node):
        # direct comparison
        if left.__class__ is not right.__class__:
            print "Node type mismatch:", left, right
            return False
        if check_lineno and left.lineno != right.lineno:
            print "lineno mismatch in (%s) left: %s, right: %s" % (left, left.lineno, right.lineno)
            return False
        left_nodes = list(left.getChildren())
        right_nodes = list(right.getChildren())
        if len(left_nodes) != len(right_nodes):
            print "Number of children mismatch:", left, right
            return False
        for left_node, right_node in zip(left_nodes, right_nodes):
            if not nodes_equal(left_node, right_node, check_lineno):
                return False
        return True

    if not isinstance(left,test_ast.Node) or not isinstance(right,ast_ast.Node):
        return left==right
    if left.__class__.__name__ != right.__class__.__name__:
        print "Node type mismatch:", left, right
        return False
    if isinstance(left,test_ast.Function) and isinstance(right,ast_ast.Function):
        left_nodes = list(left.getChildren())
        right_nodes = [] # generated ast differ here because argnames is a list of nodes in
        right_nodes.append(right.decorators)
        right_nodes.append(right.name)
        right_nodes.append(right.argnames)
        right_nodes.extend(flatten(right.defaults))
        right_nodes.append(right.flags)
        right_nodes.append(right.w_doc)
        right_nodes.append(right.code)
        left_args = left_nodes[2]
        del left_nodes[2]
        right_args = right_nodes[2]
        del right_nodes[2]
        if not arglist_equal(left_args, right_args):
            return False
    elif isinstance(left,test_ast.Lambda) and isinstance(right,ast_ast.Lambda):
        left_nodes = list(left.getChildren())
        right_nodes = [] # generated ast differ here because argnames is a list of nodes in
        right_nodes.append(right.argnames)
        right_nodes.extend(flatten(right.defaults))
        right_nodes.append(right.flags)
        right_nodes.append(right.code)
        print "left", repr(left_nodes)
        print "right", repr(right_nodes)
        left_args = left_nodes[0]
        del left_nodes[0]
        right_args = right_nodes[0]
        del right_nodes[0]
        if not arglist_equal(left_args, right_args):
            return False
    elif isinstance(left,test_ast.Const):
        if isinstance(right,ast_ast.Const):
            r = left.value == right.value
        elif isinstance(right,ast_ast.NoneConst):
            r = left.value == None
        elif isinstance(right, ast_ast.NumberConst):
            r = left.value == right.number_value
        elif isinstance(right, ast_ast.StringConst):
            r = left.value == right.string_value
        else:
            print "Not const type %s" % repr(right)
            return False
        if not r:
            print "Constant mismatch:", left, right
        if check_lineno:
            # left is a stablecompiler.ast node which means and stable compiler
            # doesn't set a lineno on each Node
            if left.lineno is not None and left.lineno != right.lineno:
                print "(0) (%s) left: %s, right: %s" % (left, left.lineno, right.lineno)
                return False
        return True
    elif isinstance(right, ast_ast.Return) and isinstance(left, test_ast.Return):
        left_nodes = left.getChildren()
        if right.value is None:
            right_nodes = (ast_ast.Const(None),)
        else:
            right_nodes = right.getChildren()
    elif isinstance(left,test_ast.Subscript):
        # test_ast.Subscript is not expressive enough to tell the difference
        # between a[x] and a[x,]  :-(
        left_nodes = list(left.getChildren())
        if len(left.subs) > 1:
            left_nodes[-len(left.subs):] = [test_ast.Tuple(left_nodes[-len(left.subs):],
                                                           left.lineno)]
        right_nodes = right.getChildren()
    else:
        left_nodes = left.getChildren()
        right_nodes = right.getChildren()
    if len(left_nodes)!=len(right_nodes):
        print "Number of children mismatch:", left, right
        return False
    for i,j in zip(left_nodes,right_nodes):
        if not nodes_equal(i,j, check_lineno):
            return False
    if check_lineno:
        # left is a stablecompiler.ast node which means and stable compiler
        # doesn't set a lineno on each Node.
        # (stablecompiler.ast.Expression doesn't have a lineno attribute)
        if hasattr(left, 'lineno') and left.lineno is not None and left.lineno != right.lineno:
            print "(1) (%s) left: %s, right: %s" % (left, left.lineno, right.lineno)
            return False
    return True

EXPECTED = {
    "k[v,]" : "Module(None, Stmt([Discard(Subscript(Name('k'), 2, Tuple([Name('v')])))]))",
    "m[a,b]" : "Module(None, Stmt([Discard(Subscript(Name('m'), 2, Tuple([Name('a'), Name('b')])))]))",

    "1 if True else 2" : "Module(None, Stmt([Discard(CondExpr(Name('True'), Const(1), Const(2)))]))",
    "1 if False else 2" : "Module(None, Stmt([Discard(CondExpr(Name('False'), Const(1), Const(2)))]))",

    "a[1:2:3, 100]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Sliceobj([Const(1), Const(2), Const(3)]), Const(100)])))]))",
    "a[:2:3, 100]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Sliceobj([Const(None), Const(2), Const(3)]), Const(100)])))]))",
    "a[1::3, 100,]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Sliceobj([Const(1), Const(None), Const(3)]), Const(100)])))]))",
    "a[1:2:, 100]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Sliceobj([Const(1), Const(2), Const(None)]), Const(100)])))]))",
    "a[1:2, 100]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Sliceobj([Const(1), Const(2)]), Const(100)])))]))",
    "a[1:, 100,]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Sliceobj([Const(1), Const(None)]), Const(100)])))]))",
    "a[:2, 100]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Sliceobj([Const(None), Const(2)]), Const(100)])))]))",
    "a[:, 100]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Sliceobj([Const(None), Const(None)]), Const(100)])))]))",
    "a[100, 1:2:3,]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Const(100), Sliceobj([Const(1), Const(2), Const(3)])])))]))",
    "a[100, :2:3]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Const(100), Sliceobj([Const(None), Const(2), Const(3)])])))]))",
    "a[100, 1::3]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Const(100), Sliceobj([Const(1), Const(None), Const(3)])])))]))",
    "a[100, 1:2:,]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Const(100), Sliceobj([Const(1), Const(2), Const(None)])])))]))",
    "a[100, 1:2]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Const(100), Sliceobj([Const(1), Const(2)])])))]))",
    "a[100, 1:]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Const(100), Sliceobj([Const(1), Const(None)])])))]))",
    "a[100, :2,]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Const(100), Sliceobj([Const(None), Const(2)])])))]))",
    "a[100, :]": "Module(None, Stmt([Discard(Subscript(Name('a'), 2, Tuple([Const(100), Sliceobj([Const(None), Const(None)])])))]))",

    # stablecompiler produces a Pass statement which does not seem very consistent
    # (a module should only have a Stmt child)
    "\t # hello\n": "Module(None, Stmt([]))",
    }

# Create parser from Grammar_stable, not current grammar.
stable_parser = pythonparse.make_pyparser('stable')

def tuple_parse_expr(expr, target='single'):
    t = Transformer("dummyfile")
    return ast_from_input(expr, target, t, stable_parser)

def source2ast(source, mode, space=FakeSpace()):
    version = '2.4'
    python_parser = pythonparse.make_pyparser(version)
    builder = AstBuilder(python_parser, version, space=space)
    python_parser.parse_source(source, mode, builder)
    return builder.rule_stack[-1]

def check_expression(expr, mode='single'):
    pypy_ast = source2ast(expr, mode)
    try:
        python_ast = EXPECTED[expr]
    except KeyError:
        # trust the stablecompiler's Transformer when no explicit result has
        # been provided (although trusting it is a foolish thing to do)
        python_ast = tuple_parse_expr(expr, mode)
        check_lineno = True
    else:
        if isinstance(python_ast, str):
            python_ast = eval(python_ast, ast_ast.__dict__)
        check_lineno = False
    print "-" * 30
    print "ORIG :", python_ast
    print
    print "BUILT:", pypy_ast
    print "-" * 30
    assert nodes_equal(python_ast, pypy_ast, check_lineno), 'failed on %r' % (expr)


def test_basic_astgen():
    for family in TESTS:
        for expr in family:
            yield check_expression, expr

def test_exec_inputs():
    for family in EXEC_INPUTS:
        for expr in family:
            yield check_expression, expr, 'exec'


NEW_GRAMMAR_SNIPPETS = [
    'snippet_with_1.py',
    'snippet_with_2.py',
    ]

SNIPPETS = [
    'snippet_1.py',
    'snippet_several_statements.py',
    'snippet_simple_function.py',
    'snippet_simple_for_loop.py',
    'snippet_while.py',
    'snippet_import_statements.py',
    'snippet_generator.py',
    'snippet_exceptions.py',
    'snippet_classes.py',
    'snippet_simple_class.py',
    'snippet_docstring.py',
    'snippet_2.py',
    'snippet_3.py',
    'snippet_4.py',
    'snippet_comment.py',
    'snippet_encoding_declaration2.py',
    'snippet_encoding_declaration3.py',
    'snippet_encoding_declaration.py',
    'snippet_function_calls.py',
    'snippet_import_statements.py',
    'snippet_list_comps.py',
    'snippet_multiline.py',
    'snippet_numbers.py',
    'snippet_only_one_comment.py',
    'snippet_redirected_prints.py',
    'snippet_simple_assignment.py',
    'snippet_simple_in_expr.py',
    'snippet_slice.py',
    'snippet_whitespaces.py',
    'snippet_samples.py',
    'snippet_decorators.py',
    'snippet_listlinenos.py',
    'snippet_whilelineno.py',
    ]

LIBSTUFF = [
      '_marshal.py',
    ]

def test_snippets():
    for snippet_name in SNIPPETS: # + NEW_GRAMMAR_SNIPPETS: # Disabled 2.5 syntax
        filepath = os.path.join(os.path.dirname(__file__), 'samples', snippet_name)
        source = file(filepath).read()
        # To avoid using the stable compiler we pull an explicit AST out of the snippet
        if source.startswith('# EXPECT:'):
            firstline,_ = source.split('\n', 1)
            firstline = firstline[len('# EXPECT:'):].strip()
            EXPECTED[source] = firstline
        yield check_expression, source, 'exec'

def test_libstuff():
    #py.test.skip("failing, need to investigate")
    for snippet_name in LIBSTUFF:
        filepath = os.path.join(os.path.dirname(__file__), '../../../lib', snippet_name)
        source = file(filepath).read()
        yield check_expression, source, 'exec'

# FIXME: find the sys' attribute that define this
STDLIB_PATH = os.path.dirname(os.__file__)
def test_on_stdlib():
    py.test.skip('too ambitious for now (and time consuming)')
    for basename in os.listdir(STDLIB_PATH):
        if not basename.endswith('.py'):
            continue
        filepath = os.path.join(STDLIB_PATH, basename)
        size = os.stat(filepath)[6]
        # filter on size
        source = file(filepath).read()
        yield check_expression, source, 'exec'


def test_eval_string():
    test = ['""', "''", '""""""', "''''''", "''' '''", '""" """', '"foo"',
            "'foo'", '"""\n"""', '"\\ "', '"\\n"',
            '"\\""',
            '"\\x00"',
            ]
    for data in test:
        yield check_expression, data, 'eval'

def test_single_inputs():
    for family in SINGLE_INPUTS:
        for expr in family:
            yield check_expression, expr, 'single'
