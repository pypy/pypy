
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
    "f = lambda x: x+1",
    "x, y, z = 1, 2, 3",
]    
expression_tests = [ 0, 1, 2, 3, 4, 5, 6,7, 8, 9, 10, 11, ] # = range(len(expressions))
failed_expression_tests = [ 12, 13, 14 ]

comparisons = [
    "a < b",
    "a > b",
    "a not in b",
    "a in b",
    "3 < x < 5",
    "(3 < x) < 5",
    ]
comparison_tests = []
failed_comparison_tests = range( len(comparisons) )
def ast_parse_expr( expr ):
    builder = AstBuilder()
    PYTHON_PARSER.parse_source( expr, "single_input", builder )
    return builder

def tuple_parse_expr( expr ):
    t = Transformer()
    return ast_from_input( expr, "single", t )

def check_expression( expr ):
    r1 = ast_parse_expr( expr )
    ast = tuple_parse_expr( expr )
    print "ORIG :", ast
    print "BUILT:", r1.rule_stack[-1]
    assert ast == r1.rule_stack[-1]

def test_expressions():
##    py.test.skip("work in progress")
    for i in expression_tests:
        yield check_expression, expressions[i]

def test_comparisons():
##    py.test.skip("work in progress")
    for i in comparison_tests:
        yield check_expression, comparisons[i]
