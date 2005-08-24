from pypy.interpreter.pyparser.pythonparse import PYTHON_PARSER
from pypy.interpreter.pyparser.astbuilder import AstBuilder


from pypy.interpreter.pyparser.pythonutil import ast_from_input
import py.test

from pypy.interpreter.astcompiler import ast, misc, pycodegen

from test_astbuilder import expressions, comparisons, funccalls, backtrackings,\
    listmakers, genexps, dictmakers, multiexpr, attraccess, slices, imports,\
    asserts, execs, prints, globs, raises, imports_newstyle


TESTS = [
    expressions,
    comparisons,
    funccalls,
    backtrackings,
    listmakers,
    dictmakers,
    multiexpr,
    attraccess,
    slices,
    imports,
    execs,
    prints,
    globs,
    raises,
    ]

import sys
if sys.version_info[0]==2 and sys.version_info[1]>=4:
    # genexps and new style import don't work on python2.3
    TESTS.append(genexps)
    TESTS.append(imports_newstyle)
    # assertions give different bytecode with 2.4 (optimize if __debug__)
    TESTS.append(asserts)
TARGET_DICT = {
    'single' : 'single_input',
    'exec'   : 'file_input',
    'eval'   : 'eval_input',
    }

def ast_parse_expr(expr, target='single'):
    target = TARGET_DICT[target]
    builder = AstBuilder()
    PYTHON_PARSER.parse_source(expr, target, builder)
    return builder.rule_stack[-1]


### Note: builtin compile and compiler.compile behave differently
def compile_expr( expr, target="single" ):
    return compile( expr, "<?>", target )

def ast_compile( expr, target="single" ):
    from compiler import compile
    return compile( expr, "<?>", target )
    

def compare_code( code1, code2 ):
    #print "Filename", code1.co_filename, code2.co_filename
    assert code1.co_filename == code2.co_filename
    #print repr(code1.co_code)
    #print repr(code2.co_code)
    if code1.co_code != code2.co_code:
        import dis
        print "Code from pypy:"
        dis.dis(code1)
        print "Code from python", sys.version
        dis.dis(code2)
        assert code1.co_code == code2.co_code
    assert code1.co_varnames == code2.co_varnames

def check_compile( expr ):
    import new
    ast_tree = ast_parse_expr( expr )
    misc.set_filename("<?>", ast_tree)
    print "Compiling:", expr
    #print ast_tree
    codegenerator = pycodegen.InteractiveCodeGenerator(ast_tree)
    code1 = new.code(*codegenerator.getCode())
    code2 = ast_compile( expr )
    compare_code(code1,code2)

def test_compile_argtuple_1():
    code = """def f( x, (y,z) ):
    print x,y,z
"""
    check_compile( code )

def test_compile_argtuple_2():
    code = """def f( x, (y,(z,t)) ):
    print x,y,z,t
"""
    check_compile( code )


def test_compile_argtuple_3():
    code = """def f( x, (y,(z,(t,u))) ):
    print x,y,z,t,u
"""
    check_compile( code )



def test_basic_astgen():
    for family in TESTS:
        for expr in family:
            yield check_compile, expr
