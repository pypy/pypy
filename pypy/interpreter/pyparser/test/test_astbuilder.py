import os

from pypy.interpreter.pyparser.pythonparse import PYTHON_PARSER
from pypy.interpreter.pyparser.astbuilder import AstBuilder
from pypy.interpreter.pyparser.pythonutil import ast_from_input
from pypy.interpreter.stablecompiler.transformer import Transformer
import pypy.interpreter.stablecompiler.ast as stable_ast
import pypy.interpreter.astcompiler.ast as ast_ast

import py.test

from pypy.interpreter.astcompiler import ast


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
            print "l is str", type(l)==str
            print "r is AssName", isinstance(r,ast_ast.AssName)
            return False
    return True


def nodes_equal(left, right):
    if not isinstance(left,stable_ast.Node) or not isinstance(right,ast_ast.Node):
        return left==right
    if left.__class__.__name__ != right.__class__.__name__:
        return False    
    if isinstance(left,stable_ast.Function) and isinstance(right,ast_ast.Function):
        left_nodes = list(left.getChildren())
        right_nodes = list(right.getChildren())
        left_args = left_nodes[2]
        del left_nodes[2]
        right_args = right_nodes[2]
        del right_nodes[2]
        if not arglist_equal(left_args, right_args):
            return False
    elif isinstance(left,stable_ast.Lambda) and isinstance(right,ast_ast.Lambda):
        left_nodes = list(left.getChildren())
        right_nodes = list(right.getChildren())
        left_args = left_nodes[0]
        del left_nodes[0]
        right_args = right_nodes[0]
        del right_nodes[0]
        if not arglist_equal(left_args, right_args):
            return False
    elif isinstance(left,stable_ast.Const):
        if isinstance(right,ast_ast.Const):
            return left.value == right.value
        elif isinstance(right,ast_ast.NoneConst):
            return left.value == None
        elif isinstance(right, ast_ast.NumberConst):
            return left.value == right.number_value
        elif isinstance(right, ast_ast.StringConst):
            return left.value == right.string_value
        else:
            print "Not const type %s" % repr(right)
            return False
    else:
        left_nodes = left.getChildren()
        right_nodes = right.getChildren()
    if len(left_nodes)!=len(right_nodes):
        return False
    for i,j in zip(left_nodes,right_nodes):
        if not nodes_equal(i,j):
            return False
    return True

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
    "del foo",
    "del foo[bar]",
    "del foo.bar",
    "l[0]",
    "m[a,b]",
    "a.b.c[d]",
    "file('some.txt').read()",
    "a[0].read()",
    "a[1:1].read()",
    "f('foo')('bar')('spam')",
    "f('foo')('bar')('spam').read()[0]",
    "a.b[0][0]",
    "a.b[0][:]",
    "a.b[0][::]",
    "a.b[0][0].pop()[0].push('bar')('baz').spam",
    "a.b[0].read()[1][2].foo().spam()[0].bar",
    "a**2",
    "a**2**2",
    "a.b[0]**2",
    "a.b[0].read()[1][2].foo().spam()[0].bar ** 2",
    "l[start:end] = l2",
    "l[::] = l2",
    "a = `s`",
    "a = `1 + 2 + f(3, 4)`",
    "[a, b] = c",
    "(a, b) = c",
    "[a, (b,c), d] = e",
    "a, (b, c), d = e",
    ]

funccalls = [
    "l = func()",
    "l = func(10)",
    "l = func(10, 12, a, b=c, *args)",
    "l = func(10, 12, a, b=c, **kwargs)",
    "l = func(10, 12, a, b=c, *args, **kwargs)",
    "l = func(10, 12, a, b=c)",
    "e = l.pop(3)",
    "e = k.l.pop(3)",
    "simplefilter('ignore', category=PendingDeprecationWarning, append=1)",
    """methodmap = dict(subdirs=phase4,
                        same_files=phase3, diff_files=phase3, funny_files=phase3,
                        common_dirs = phase2, common_files=phase2, common_funny=phase2,
                        common=phase1, left_only=phase1, right_only=phase1,
                        left_list=phase0, right_list=phase0)""",
    "odata = b2a_qp(data, quotetabs = quotetabs, header = header)",
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
    "l = (i for i in [ j*2 for j in range(10) ] )",
    "l = [i for i in ( j*2 for j in range(10) ) ]",
    "l = (i for i in [ j*2 for j in ( k*3 for k in range(10) ) ] )",
    "l = [i for j in ( j*2 for j in [ k*3 for k in range(10) ] ) ]",
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
    'a.b = 2',
    'x = a.b',
    ]

slices = [
    "l[:]",
    "l[::]",
    "l[1:2]",
    "l[1:]",
    "l[:2]",
    "l[1::]",
    "l[:1:]",
    "l[::1]",
    "l[1:2:]",
    "l[:1:2]",
    "l[1::2]",
    "l[0:1:2]",
    "a.b.l[:]",
    "a.b.l[1:2]",
    "a.b.l[1:]",
    "a.b.l[:2]",
    "a.b.l[0:1:2]",
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
    ]

imports_newstyle = [
    'from os import path, system',
    'from os import path as P, system as S',
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
""",
    "if a and not b == c: pass",
    "if a and not not not b == c: pass",
    ]

asserts = [
    'assert False',
    'assert a == 1',
    'assert a == 1 and b == 2',
    'assert a == 1 and b == 2, "assertion failed"',
    ]

execs = [
    'exec a',
    'exec "a=b+3"',
    'exec a in f()',
    'exec a in f(), g()',
    ]

prints = [
    'print',
    'print a',
    'print a,',
    'print a, b',
    'print a, "b", c',
    'print >> err',
    'print >> err, "error"',
    'print >> err, "error",',
    'print >> err, "error", a',
    ]

globs = [
    'global a',
    'global a,b,c',
    ]

raises_ = [      # NB. 'raises' creates a name conflict with py.test magic
    'raise',
    'raise ValueError',
    'raise ValueError("error")',
    'raise ValueError, "error"',
    'raise ValueError, "error", foo',
    ]

tryexcepts = [
    """try:
    a
    b
except:
    pass
""",
    """try:
    a
    b
except NameError:
    pass
""",
    """try:
    a
    b
except NameError, err:
    pass
""",
    """try:
    a
    b
except (NameError, ValueError):
    pass
""",
    """try:
    a
    b
except (NameError, ValueError), err:
    pass
""",
    """try:
    a
except NameError, err:
    pass
except ValueError, err:
    pass
""",
    """try:
    a
except NameError, err:
    a = 1
    b = 2
except ValueError, err:
    a = 2
    return a
"""
    """try:
    a
except NameError, err:
    a = 1
except ValueError, err:
    a = 2
else:
    a += 3
""",
    """try:
    a
finally:
    b
""",
    """try:
    return a
finally:
    a = 3
    return 1
""",

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
    "def f(t=()): pass",
    "def f(a, b, (c, d), e): pass",
    "def f(a, b, (c, (d, e), f, (g, h))): pass",
    "def f(a, b, (c, (d, e), f, (g, h)), i): pass",
    ]

one_stmt_classdefs = [
    "class Pdb(bdb.Bdb, cmd.Cmd): pass",
    ]

docstrings = [
    '''def foo():
    """foo docstring"""
    return 1
''',
    '''def foo():
    """foo docstring"""
    a = 1
    """bar"""
    return a
''',
    '''def foo():
    """doc"""; print 1
    a=1
''',
    '''"""Docstring""";print 1''',
    ]

returns = [
    'def f(): return',
    'def f(): return 1',
    'def f(): return a.b',
    'def f(): return a',
    'def f(): return a,b,c,d',
    'return (a,b,c,d)',
    ]

augassigns = [
    'a=1;a+=2',
    'a=1;a-=2',
    'a=1;a*=2',
    'a=1;a/=2',
    'a=1;a//=2',
    'a=1;a%=2',
    'a=1;a**=2',
    'a=1;a>>=2',
    'a=1;a<<=2',
    'a=1;a&=2',
    'a=1;a^=2',
    'a=1;a|=2',
    
    'a=A();a.x+=2',
    'a=A();a.x-=2',
    'a=A();a.x*=2',
    'a=A();a.x/=2',
    'a=A();a.x//=2',
    'a=A();a.x%=2',
    'a=A();a.x**=2',
    'a=A();a.x>>=2',
    'a=A();a.x<<=2',
    'a=A();a.x&=2',
    'a=A();a.x^=2',
    'a=A();a.x|=2',

    'a=A();a[0]+=2',
    'a=A();a[0]-=2',
    'a=A();a[0]*=2',
    'a=A();a[0]/=2',
    'a=A();a[0]//=2',
    'a=A();a[0]%=2',
    'a=A();a[0]**=2',
    'a=A();a[0]>>=2',
    'a=A();a[0]<<=2',
    'a=A();a[0]&=2',
    'a=A();a[0]^=2',
    'a=A();a[0]|=2',

    'a=A();a[0:2]+=2',
    'a=A();a[0:2]-=2',
    'a=A();a[0:2]*=2',
    'a=A();a[0:2]/=2',
    'a=A();a[0:2]//=2',
    'a=A();a[0:2]%=2',
    'a=A();a[0:2]**=2',
    'a=A();a[0:2]>>=2',
    'a=A();a[0:2]<<=2',
    'a=A();a[0:2]&=2',
    'a=A();a[0:2]^=2',
    'a=A();a[0:2]|=2',
    ]

TESTS = [
    expressions,
    augassigns,
    comparisons,
    funccalls,
    backtrackings,
    listmakers,
    genexps,
    dictmakers,
    multiexpr,
    attraccess,
    slices,
    imports,
    imports_newstyle,
    asserts,
    execs,
    prints,
    globs,
    raises_,
    ]

EXEC_INPUTS = [
    one_stmt_classdefs,
    one_stmt_funcdefs,
    if_stmts,
    tryexcepts,
    docstrings,
    returns,
    ]

SINGLE_INPUTS = [
   one_stmt_funcdefs,
   ['\t # hello\n',
    'print 6*7',
    'if 1:  x\n',
    'x = 5',
    'x = 5 ',
    '''"""Docstring""";print 1''',
    '''"Docstring"''',
    ]
]

TARGET_DICT = {
    'single' : 'single_input',
    'exec'   : 'file_input',
    'eval'   : 'eval_input',
    }


class FakeSpace:
    w_None = None
    w_str = str
    w_int = int
    
    def wrap(self,obj):
        return obj

    def isinstance(self, obj, wtype ):
        return isinstance(obj,wtype)

    def is_true(self, obj):
        return obj

    def eq_w(self, obj1, obj2):
        return obj1 == obj2

    def is_w(self, obj1, obj2):
        return obj1 is obj2

    def type(self, obj):
        return type(obj)

    def newtuple(self, lst):
        return tuple(lst)
    
def ast_parse_expr(expr, target='single'):
    target = TARGET_DICT[target]
    builder = AstBuilder(space=FakeSpace())
    PYTHON_PARSER.parse_source(expr, target, builder)
    return builder

def tuple_parse_expr(expr, target='single'):
    t = Transformer("dummyfile")
    return ast_from_input(expr, target, t)

def check_expression(expr, target='single'):
    r1 = ast_parse_expr(expr, target)
    ast = tuple_parse_expr(expr, target)
    print "-" * 30
    print "ORIG :", ast
    print 
    print "BUILT:", r1.rule_stack[-1]
    print "-" * 30
    assert nodes_equal( ast, r1.rule_stack[-1]), 'failed on %r' % (expr)


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
    'snippet_generator.py',
    'snippet_exceptions.py',
    'snippet_classes.py',
    'snippet_simple_class.py',
    'snippet_docstring.py',
    'snippet_2.py',
    'snippet_3.py',
    'snippet_4.py',
    # XXX: skip snippet_comment because we don't have a replacement of
    #      eval for numbers and strings (eval_number('0x1L') fails)
    # 'snippet_comment.py',
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
    ]

def test_snippets():
    for snippet_name in SNIPPETS:
        filepath = os.path.join(os.path.dirname(__file__), 'samples', snippet_name)
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
        if size <= 10000:
            print "TESTING", filepath
            source = file(filepath).read()
            yield check_expression, source, 'exec'


def test_eval_string():
    from pypy.interpreter.pyparser.astbuilder import eval_string
    test = ['""', "''", '""""""', "''''''", "''' '''", '""" """', '"foo"',
            "'foo'", '"""\n"""', '"\\ "', '"\\n"',
            # '"\""',
            ]
    for data in test:
        assert eval_string(data) == eval(data)

def test_single_inputs():
    for family in SINGLE_INPUTS:
        for expr in family:
            yield check_expression, expr, 'single'
