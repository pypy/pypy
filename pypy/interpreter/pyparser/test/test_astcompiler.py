import os
from pypy.interpreter.pyparser.pythonparse import PYTHON_PARSER
from pypy.interpreter.pyparser.astbuilder import AstBuilder
from pypy.interpreter.pycode import PyCode
import py.test

def setup_module(mod):
    import sys
    if sys.version[:3] != "2.4":
        py.test.skip("expected to work only on 2.4")

from pypy.interpreter.astcompiler import ast, misc, pycodegen

from test_astbuilder import expressions, comparisons, funccalls, backtrackings,\
    listmakers, genexps, dictmakers, multiexpr, attraccess, slices, imports,\
    asserts, execs, prints, globs, raises_, imports_newstyle, augassigns, \
    if_stmts, one_stmt_classdefs, one_stmt_funcdefs, tryexcepts, docstrings, \
    returns, SNIPPETS, SINGLE_INPUTS, LIBSTUFF

from test_astbuilder import FakeSpace


TESTS = [
    expressions,
    augassigns,
    comparisons,
    funccalls,
     backtrackings,
     listmakers,
     dictmakers,
     multiexpr,
     # genexps, investigate?
     attraccess,
     slices,
     imports,
     execs,
     prints,
     globs,
     raises_,
#  EXEC_INPUTS
     one_stmt_classdefs,
     one_stmt_funcdefs,
     if_stmts,
     tryexcepts,
     docstrings,
     returns,
    ]

import sys
if sys.version_info[0]==2 and sys.version_info[1]>=4:
    # genexps and new style import don't work on python2.3
    # TESTS.append(genexps) XXX: 2.4 optimizes bytecode so our comparison doesn't work
    TESTS.append(imports_newstyle)
    # assertions give different bytecode with 2.4 (optimize if __debug__)
    TESTS.append(asserts)
TARGET_DICT = {
    'single' : 'single_input',
    'exec'   : 'file_input',
    'eval'   : 'eval_input',
    }

def ast_parse_expr(expr, target='single', space=FakeSpace()):
    target = TARGET_DICT[target]
    builder = AstBuilder(space=space)
    PYTHON_PARSER.parse_source(expr, target, builder)
    return builder.rule_stack[-1]


def compile_with_astcompiler(expr, target='exec', space=FakeSpace()):
    ast = ast_parse_expr(expr, target='exec', space=space)
    misc.set_filename('<?>', ast)
    if target == 'exec':
        Generator = pycodegen.ModuleCodeGenerator
    elif target == 'single':
        Generator = pycodegen.InteractiveCodeGenerator
    elif target == 'eval':
        Generator = pycodegen.ExpressionCodeGenerator
    codegen = Generator(space, ast)
    rcode = codegen.getCode()
    return to_code(rcode)

def compile_with_stablecompiler(expr, target='exec'):
    from pypy.interpreter.testcompiler import compile
    # from compiler import compile
    return compile(expr, '<?>', target)


def compare_code(ac_code, sc_code):
    #print "Filename", ac_code.co_filename, sc_code.co_filename
    assert ac_code.co_filename == sc_code.co_filename
    #print repr(ac_code.co_code)
    #print repr(sc_code.co_code)
    if ac_code.co_code != sc_code.co_code:
        import dis
        print "Code from pypy:"
        dis.dis(ac_code)
        print "Code from python", sys.version
        dis.dis(sc_code)
        assert ac_code.co_code == sc_code.co_code
    assert ac_code.co_varnames == sc_code.co_varnames
    assert ac_code.co_flags == sc_code.co_flags
    
    assert len(ac_code.co_consts) == len(sc_code.co_consts)
    for c1, c2 in zip( ac_code.co_consts, sc_code.co_consts ):
        if type(c1)==PyCode:
            c1 = to_code(c1)
            return compare_code( c1, c2 )
        else:
            assert c1 == c2

def to_code( rcode ):
    import new
    code = new.code( rcode.co_argcount,
                     rcode.co_nlocals,
                     rcode.co_stacksize,
                     rcode.co_flags,
                     rcode.co_code,
                     tuple(rcode.co_consts_w),
                     tuple(rcode.co_names),
                     tuple(rcode.co_varnames),
                     rcode.co_filename,
                     rcode.co_name,
                     rcode.co_firstlineno,
                     rcode.co_lnotab,
                     tuple(rcode.co_freevars),
                     tuple(rcode.co_cellvars) )
    return code

def check_compile(expr, target='exec', quiet=False):
    if not quiet:
        print "Compiling:", expr
    sc_code = compile_with_stablecompiler(expr, target=target)
    ac_code = compile_with_astcompiler(expr, target=target)
    compare_code(ac_code, sc_code)

## def check_compile( expr ):
##     space = FakeSpace()
##     ast_tree = ast_parse_expr( expr, target='exec', space=space )
##     misc.set_filename("<?>", ast_tree)
##     print "Compiling:", expr
##     print ast_tree
##     codegenerator = pycodegen.ModuleCodeGenerator(space,ast_tree)
##     rcode = codegenerator.getCode()
##     code1 = to_code( rcode )
##     code2 = ast_compile( expr )
##     compare_code(code1,code2)

def test_compile_argtuple_1():
    #py.test.skip('will be tested when more basic stuff will work')
    code = """def f( x, (y,z) ):
    print x,y,z
"""
    check_compile( code )

def test_compile_argtuple_2():
    #py.test.skip('will be tested when more basic stuff will work')
    code = """def f( x, (y,(z,t)) ):
    print x,y,z,t
"""
    check_compile( code )


def test_compile_argtuple_3():
    #py.test.skip('will be tested when more basic stuff will work')
    code = """def f( x, (y,(z,(t,u))) ):
    print x,y,z,t,u
"""
    check_compile( code )



def test_basic_astgen():
    for family in TESTS:
        for expr in family:
            yield check_compile, expr

def test_snippets():
    for snippet_name in SNIPPETS:
        filepath = os.path.join(os.path.dirname(__file__), 'samples', snippet_name)
        source = file(filepath).read()
        yield check_compile, source, 'exec'

def test_libstuff():
    for snippet_name in LIBSTUFF:
        filepath = os.path.join(os.path.dirname(__file__), '../../../lib', snippet_name)
        source = file(filepath).read()
        yield check_compile, source, 'exec'        


def test_single_inputs():
    for family in SINGLE_INPUTS:
        for expr in family:
            yield check_compile, expr, 'single'
