import os

from pypy.interpreter.pyparser.pythonparse import PYTHON_PARSER
from pypy.interpreter.pyparser.astbuilder import AstBuilder
from pypy.interpreter.pyparser.pythonutil import ast_from_input
from pypy.interpreter.stablecompiler.transformer import Transformer
import py.test

from pypy.interpreter.astcompiler import ast

expressions = [
    "x = a + 1",
    "x = 1 - a",
    "x = a * b",
    "x = a ** 2",
    "x = a / b",
    "x = a & b",
    "x = a | b",
    "x = a ^ b",
    "x = a // b",
    "x = a * b + 1",
    "x = a + 1 * b",
    "x = a * b / c",
    "x = a * (1 + c)",
    "x, y, z = 1, 2, 3",
    "x = 'a' 'b' 'c'",
    "l = func()",
    "l = func(10)",
    "l = func(10, 12, a, b=c, *args)",
    "l = func(10, 12, a, b=c, **kwargs)",
    "l = func(10, 12, a, b=c, *args, **kwargs)",
    "l = func(10, 12, a, b=c)",
    # "l = [i for i in range(10)]",
    # "l = [i for i in range(10) if i%2 == 0]",
    # "l = [1, 2, 3]",
]
expression_tests = range(len(expressions))
# expression_tests = [-1]

backtrackings = [
    "f = lambda x: x+1",
    "f = lambda x,y: x+y",
    "f = lambda x,y=1,z=t: x+y",
    "f = lambda x,y=1,z=t,*args,**kwargs: x+y",
    "f = lambda x,y=1,z=t,*args: x+y",
    "f = lambda x,y=1,z=t,**kwargs: x+y",
    "f = lambda: 1",
    "f = lambda *args: 1",
    "f = lambda **kwargs: 1",
    ]
backtracking_tests = range(len(backtrackings))

comparisons = [
    "a < b",
    "a > b",
    "a not in b",
    "a is not b",
    "a in b",
    "a is b",
    "3 < x < 5",
    "(3 < x) < 5",
    "a < b < c < d",
    "(a < b) < (c < d)",
    "a < (b < c) < d",
    ]
comparison_tests = range(len(comparisons))
# comparison_tests = [7]

multiexpr = [
    'a = b; c = d;',
    'a = b = c = d',
    'a = b\nc = d',
    ]

def ast_parse_expr(expr):
    builder = AstBuilder()
    PYTHON_PARSER.parse_source(expr, 'single_input', builder)
    return builder

def tuple_parse_expr(expr):
    t = Transformer()
    return ast_from_input(expr, 'single', t)

def check_expression(expr):
    r1 = ast_parse_expr(expr)
    ast = tuple_parse_expr(expr)
    print "ORIG :", ast
    print "BUILT:", r1.rule_stack[-1]
    assert ast == r1.rule_stack[-1], 'failed on %r' % (expr)


def test_multiexpr():
    for expr in multiexpr:
        yield check_expression, expr

def test_backtracking_expressions():
    """tests for expressions that need backtracking"""
    for i in backtracking_tests:
        yield check_expression, backtrackings[i]

def test_expressions():
    for i in expression_tests:
        yield check_expression, expressions[i]

def test_comparisons():
    for i in comparison_tests:
        yield check_expression, comparisons[i]

SNIPPETS = [
#     'snippet_1.py',
#    'snippet_2.py',
#    'snippet_3.py',
#    'snippet_4.py',
#    'snippet_comment.py',
#    'snippet_encoding_declaration2.py',
#    'snippet_encoding_declaration3.py',
#    'snippet_encoding_declaration.py',
#    'snippet_function_calls.py',
#    'snippet_generator.py',
#    'snippet_import_statements.py',
#    'snippet_list_comps.py',
#    'snippet_multiline.py',
#    'snippet_numbers.py',
#    'snippet_only_one_comment.py',
#    'snippet_redirected_prints.py',
#    'snippet_samples.py',
#    'snippet_simple_assignment.py',
#    'snippet_simple_class.py',
#    'snippet_simple_for_loop.py',
#    'snippet_simple_in_expr.py',
#    'snippet_slice.py',
#    'snippet_whitespaces.py',
    ]

def test_snippets():
    py.test.skip('Not ready to test on real snippet files')
    for snippet_name in SNIPPETS:
        filepath = os.path.join(os.path.dirname(__file__), 'samples', snippet_name)
        source = file(filepath).read()
        yield check_expression, source

