import os
from pypy.interpreter.pyparser import pythonparse
from pypy.interpreter.pyparser.astbuilder import AstBuilder
from pypy.interpreter.pyparser.tuplebuilder import TupleBuilder
from pypy.interpreter.pycode import PyCode
import py.test

def setup_module(mod):
    import pypy.conftest
    mod.std_space = pypy.conftest.gettestobjspace('std')

from pypy.interpreter.astcompiler import ast, misc, pycodegen

from test_astbuilder import expressions, comparisons, funccalls, backtrackings,\
    listmakers, genexps, dictmakers, multiexpr, attraccess, slices, imports,\
    asserts, execs, prints, globs, raises_, imports_newstyle, augassigns, \
    if_stmts, one_stmt_classdefs, one_stmt_funcdefs, tryexcepts, docstrings, \
    returns, SNIPPETS, SINGLE_INPUTS, LIBSTUFF, constants

from test_astbuilder import FakeSpace


TESTS = [
    constants,
    expressions,
    augassigns,
    comparisons,
    funccalls,
     backtrackings,
     listmakers,
     dictmakers,
     multiexpr,
     genexps,
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
    pythonparse.PYTHON_PARSER.parse_source(expr, target, builder)
    return builder.rule_stack[-1]


def compile_with_astcompiler(expr, target='exec', space=FakeSpace()):
    ast = ast_parse_expr(expr, target='exec', space=space) # xxx exec: single not really tested, mumble
    misc.set_filename('<?>', ast)
    if target == 'exec':
        Generator = pycodegen.ModuleCodeGenerator
    elif target == 'single':
        Generator = pycodegen.InteractiveCodeGenerator
    elif target == 'eval':
        Generator = pycodegen.ExpressionCodeGenerator
    codegen = Generator(space, ast)
    rcode = codegen.getCode()
    return rcode


# Create parser from Grammar_stable, not current grammar.
stable_grammar, _ = pythonparse.get_grammar_file("stable")
stable_parser = pythonparse.python_grammar(stable_grammar)

def compile_with_testcompiler(expr, target='exec', space=FakeSpace()):
    target2 = TARGET_DICT['exec'] # xxx exec: single not really tested
    builder = TupleBuilder()
    stable_parser.parse_source(expr, target2, builder)
    tuples =  builder.stack[-1].as_tuple(True)
    from pypy.interpreter.stablecompiler import transformer, pycodegen, misc
    ast = transformer.Transformer('<?>').compile_node(tuples)
    misc.set_filename('<?>', ast)
    if target == 'exec':
        Generator = pycodegen.ModuleCodeGenerator
    elif target == 'single':
        Generator = pycodegen.InteractiveCodeGenerator
    elif target == 'eval':
        Generator = pycodegen.ExpressionCodeGenerator
    codegen = Generator(ast)
    rcode = codegen.getCode()
    return rcode


def compare_code(ac_code, sc_code, space=FakeSpace()):
    #print "Filename", ac_code.co_filename, sc_code.co_filename
    ac_code = to_code(ac_code, space)
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
        if isinstance(c1, PyCode):
            return compare_code( c1, c2, space )
        else:
            assert c1 == c2

def to_code( rcode, space ):
    import new
    consts = []
    for w in rcode.co_consts_w:
        if type(w)==PyCode:
            consts.append(w)
        else:
            consts.append(space.unwrap(w))
    code = new.code( rcode.co_argcount,
                     rcode.co_nlocals,
                     rcode.co_stacksize,
                     rcode.co_flags,
                     rcode.co_code,
                     tuple(consts),
                     tuple(rcode.co_names),
                     tuple(rcode.co_varnames),
                     rcode.co_filename,
                     rcode.co_name,
                     rcode.co_firstlineno,
                     rcode.co_lnotab,
                     tuple(rcode.co_freevars),
                     tuple(rcode.co_cellvars) )
    return code

def check_compile(expr, target='exec', quiet=False, space=None):
    if not quiet:
        print "Compiling:", expr

    if space is None:
        space = std_space

    ac_code = compile_with_astcompiler(expr, target=target, space=space)
    if expr == "k[v,]" or expr.startswith('"'):  # module-level docstring
        py.test.skip('comparison skipped, bug in "reference stable compiler"')
    sc_code = compile_with_testcompiler(expr, target=target)
    compare_code(ac_code, sc_code, space=space)

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

STDLIB_PATH = os.path.dirname(os.__file__)
def test_on_stdlib():
    py.test.skip('too ambitious for now (and time consuming)')
    for basename in os.listdir(STDLIB_PATH):
        if not basename.endswith('.py'):
            continue
        filepath = os.path.join(STDLIB_PATH, basename)
        # size = os.stat(filepath)[6]
        # filter on size
        # if size <= 10000:
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
