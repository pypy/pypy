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
]

funccalls = [
    "l = func()",
    "l = func(10)",
    "l = func(10, 12, a, b=c, *args)",
    "l = func(10, 12, a, b=c, **kwargs)",
    "l = func(10, 12, a, b=c, *args, **kwargs)",
    "l = func(10, 12, a, b=c)",
    ]

listmakers = [
    "l = []",
    "l = [1, 2, 3]",
    "l = [i for i in range(10)]",
    "l = [i for i in range(10) if i%2 == 0]",
    "l = [i for i in range(10) if i%2 == 0 or i%2 == 1]",
    "l = [i for i in range(10) if i%2 == 0 and i%2 == 1]",
    "l = [i for j in range(10) for i in range(j)]",
    "l = [i for j in range(10) for i in range(j) if j%2 == 0]",
    "l = [i for j in range(10) for i in range(j) if j%2 == 0 and i%2 == 0]",
    "l = [(a, b) for (a,b,c) in l2]",
    "l = [{a:b} for (a,b,c) in l2]",
    "l = [i for j in k if j%2 == 0 if j*2 < 20 for i in j if i%2==0]",
    ]

genexps = [
    "l = (i for i in j)",
    "l = (i for i in j if i%2 == 0)",
    "l = (i for j in k for i in j)",
    "l = (i for j in k for i in j if j%2==0)",
    "l = (i for j in k if j%2 == 0 if j*2 < 20 for i in j if i%2==0)",
    ]


dictmakers = [
    "l = {a : b, 'c' : 0}",
    "l = {}",
    ]

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

multiexpr = [
    'a = b; c = d;',
    'a = b = c = d',
    ]

attraccess = [
    # 'a.b = 2', # Module(None, Stmt([Assign([AssAttr(Name('a'), 'b', 'OP_ASSIGN')], Const(2))]))
    'x = a.b',
    ]

imports = [
    'import os',
    'import sys, os',
    'import os.path',
    'import os.path, sys',
    'import sys, os.path as osp',
    'import os.path as osp',
    'import os.path as osp, sys as _sys',
    'import a.b.c.d',
    'import a.b.c.d as abcd',
    'from os import path',
    'from os import path, system',
    'from os import path, system,',
    'from os import path as P, system as S,',
    'from os import (path as P, system as S,)',
    'from os import *',
    ]

if_stmts = [
    "if a == 1: a+= 2",
    """if a == 1:
    a += 2
elif a == 2:
    a += 3
else:
    a += 4
"""
    ]

one_stmt_funcdefs = [
    "def f(): return 1",
    "def f(x): return x+1",
    "def f(x,y): return x+y",
    "def f(x,y=1,z=t): return x+y",
    "def f(x,y=1,z=t,*args,**kwargs): return x+y",
    "def f(x,y=1,z=t,*args): return x+y",
    "def f(x,y=1,z=t,**kwargs): return x+y",
    "def f(*args): return 1",
    "def f(**kwargs): return 1",
    ]

TESTS = [
    expressions,
    comparisons,
    funccalls,
    backtrackings,
    listmakers,
    genexps,
    dictmakers,
    multiexpr,
    attraccess,
    imports,
    ]

EXEC_INPUTS = [
    one_stmt_funcdefs,
    if_stmts,
    ]

TARGET_DICT = {
    'single' : 'single_input',
    'exec'   : 'file_input',
    'eval'   : 'eval_input',
    }

def ast_parse_expr(expr, target='single'):
    target = TARGET_DICT[target]
    builder = AstBuilder()
    PYTHON_PARSER.parse_source(expr, target, builder)
    return builder

def tuple_parse_expr(expr, target='single'):
    t = Transformer()
    return ast_from_input(expr, target, t)

def check_expression(expr, target='single'):
    r1 = ast_parse_expr(expr, target)
    ast = tuple_parse_expr(expr, target)
    print "-" * 30
    print "ORIG :", ast
    print 
    print "BUILT:", r1.rule_stack[-1]
    print "-" * 30
    assert ast == r1.rule_stack[-1], 'failed on %r' % (expr)


def test_basic_astgen():
    for family in TESTS:
        for expr in family:
            yield check_expression, expr

def test_exec_inputs():
    for family in EXEC_INPUTS:
        for expr in family:
            yield check_expression, expr, 'exec'


SNIPPETS = [    
    'snippet_1.py',
    'snippet_several_statements.py',
    'snippet_simple_function.py',
    'snippet_simple_for_loop.py',
    'snippet_while.py',
    'snippet_import_statements.py',
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
#    'snippet_simple_in_expr.py',
#    'snippet_slice.py',
#    'snippet_whitespaces.py',
    ]

def test_snippets():
    for snippet_name in SNIPPETS:
        filepath = os.path.join(os.path.dirname(__file__), 'samples', snippet_name)
        source = file(filepath).read()
        yield check_expression, source, 'exec'

