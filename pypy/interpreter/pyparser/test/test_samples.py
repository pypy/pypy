"""test module for CPython / PyPy nested tuples comparison"""
import os, os.path as osp
import sys
from symbol import sym_name
from pprint import pprint

import py

def setup_module(mod):
    if sys.version > '2.5':
        py.test.skip("Fails on top of cpy 2.5 for messy reasons, investigate")

from pypy.interpreter.pyparser.pythonutil import python_parsefile, \
    pypy_parsefile, pypy_parse, python_parse, get_grammar_file, PYTHON_VERSION
from pypy.interpreter.pyparser import grammar
from pypy.interpreter.pyparser.pythonlexer import TokenError
grammar.DEBUG = False

_, PYPY_VERSION = get_grammar_file("2.5")
# these samples are skipped if the native version of Python does not match
# the version of the grammar we use
GRAMMAR_MISMATCH = PYTHON_VERSION != PYPY_VERSION
SKIP_IF_NOT_NATIVE = [
    #"snippet_samples.py",
    #"snippet_import_statements.py",
    "snippet_decorators.py",
]
SKIP_ALWAYS = [
    "snippet_with_1.py",
    "snippet_with_2.py",
    "snippet_decorators_2.py",
]
REAL_EXPECTED_OUTPUT = {
    # for snippets that show bugs of Python's compiler package
    "snippet_transformer_bug.py":
        "Module('This module does nothing', Stmt([Printnl([Const(1)], None)]))",
    }


def name(elt):
    return "%s[%s]"% (sym_name.get(elt,elt),elt)

def print_sym_tuple(nested, level=0, limit=15, names=False, trace=()):
    buf = []
    if level <= limit:
        buf.append("%s(" % (" "*level))
    else:
        buf.append("(")
    for index, elt in enumerate(nested):
        # Test if debugging and if on last element of error path
        if trace and not trace[1:] and index == trace[0]:
            buf.append('\n----> ')
        if type(elt) is int:
            if names:
                buf.append(name(elt))
            else:
                buf.append(str(elt))
            buf.append(', ')
        elif type(elt) is str:
            buf.append(repr(elt))
        else:
            if level < limit:
                buf.append('\n')
            buf.extend(print_sym_tuple(elt, level+1, limit,
                                       names, trace[1:]))
    buf.append(')')
    return buf

def assert_tuples_equal(tup1, tup2, curpos = ()):
    for index, (elt1, elt2) in enumerate(zip(tup1, tup2)):
        if elt1 != elt2:
            if isinstance(elt1, tuple) and isinstance(elt2, tuple):
                assert_tuples_equal(elt1, elt2, curpos + (index,))
            raise AssertionError('Found difference at %s : %s != %s\n' %
                                 (curpos, name(elt1), name(elt2) ), curpos)

def test_samples():
    samples_dir = py.magic.autopath().dirpath("samples") 
    for use_lookahead in (True, False):
        grammar.USE_LOOKAHEAD = use_lookahead
        sample_paths = samples_dir.listdir("*.py")
        # Make it as likely as possible (without tons of effort) that each
        # sample will have the same test name in each run.
        sample_paths.sort()
        for path in sample_paths:
            fname = path.basename 
            if fname in SKIP_ALWAYS:
                yield lambda fname=fname: py.test.skip(
                    "%r is set to always skip." % (fname,))
                continue
            if GRAMMAR_MISMATCH and fname in SKIP_IF_NOT_NATIVE:
                yield lambda fname=fname: py.test.skip(
                    "Grammar mismatch and %s is not native" % (fname,))
                continue
            yield check_parse, str(path)

def DISABLED_check_tuples_equality(pypy_tuples, python_tuples, testname):
    """XXX FIXME: refactor with assert_tuples_equal()"""
    try:
        assert_tuples_equal(pypy_tuples, python_tuples)
    except AssertionError, e:
        error_path = e.args[-1]
        print "ERROR PATH =", error_path
        print "-"*10, "PyPy parse results", "-"*10
        print ''.join(print_sym_tuple(pypy_tuples, names=True, trace=error_path))
        print "-"*10, "CPython parse results", "-"*10
        print ''.join(print_sym_tuple(python_tuples, names=True, trace=error_path))
        assert False, testname


from pypy.interpreter.stablecompiler.transformer import Transformer as PyPyTransformer
from compiler.transformer import Transformer as PythonTransformer
from pypy.interpreter.astcompiler.consts import OP_ASSIGN, OP_DELETE, OP_APPLY

def _check_tuples_equality(pypy_tuples, python_tuples, testname):
    # compare the two tuples by transforming them into AST, to hide irrelevant
    # differences -- typically newlines at the end of the tree.
    print 'Comparing the ASTs of', testname
    transformer1 = PyPyTransformer("")
    ast_pypy   = transformer1.compile_node(pypy_tuples)
    repr_pypy  = repr(ast_pypy)

    key = os.path.basename(testname)
    if key not in REAL_EXPECTED_OUTPUT:
        transformer2 = PythonTransformer()
        ast_python = transformer2.compile_node(python_tuples)
        repr_python = repr(ast_python)
    else:
        repr_python = REAL_EXPECTED_OUTPUT[key]

    if GRAMMAR_MISMATCH:
        # XXX hack:
        # hide the more common difference between 2.3 and 2.4, which is
        #   Function(None, ...)  where 'None' stands for no decorator in 2.4
        repr_pypy   = repr_pypy.replace("Function(None, ", "Function(")
        repr_python = repr_python.replace("Function(None, ", "Function(")
        # XXX hack(bis):
    #   we changed stablecompiler to use [] instead of () in several
    #   places (for consistency), so let's make sure the test won't fail
    #   because of that (the workaround is as drastic as the way we
    #   compare python and pypy tuples :-), but we'll change that with
    #   astbuilder.py
    repr_pypy = repr_pypy.replace("[]", "()")
    repr_python = repr_python.replace("[]", "()")
    # We also changed constants 'OP_ASSIGN' 'OP_DELETE' 'OP_APPLY' to use numeric values
    repr_python = repr_python.replace("'OP_ASSIGN'", repr(OP_ASSIGN) )
    repr_python = repr_python.replace("'OP_DELETE'", repr(OP_DELETE) )
    repr_python = repr_python.replace("'OP_APPLY'", repr(OP_APPLY) )

    assert repr_pypy == repr_python


def check_parse(filepath):
    pypy_tuples = pypy_parsefile(filepath, lineno=True)
    python_tuples = python_parsefile(filepath, lineno=True)
    _check_tuples_equality(pypy_tuples, python_tuples, filepath)


def check_parse_input(snippet, mode):
    pypy_tuples = pypy_parse(snippet, mode, lineno=True)
    python_tuples = python_parse(snippet, mode, lineno=True)
    _check_tuples_equality(pypy_tuples, python_tuples, snippet)

def test_eval_inputs():
    snippets = [
        '6*7',
        'a+b*c/d',
        'True and False',
        ]
    for snippet in snippets:
        yield check_parse_input, snippet, 'eval'

def test_exec_inputs():
    snippets = [
        # '\t # hello\n ',
        'print 6*7', 'if 1:\n  x\n',
        ]
    for snippet in snippets:
        yield check_parse_input, snippet, 'exec'

def test_single_inputs():
    snippets = ['a=1', 'True', 'def f(a):\n    return a+1\n\n']
    for snippet in snippets:
        yield check_parse_input, snippet, 'single'


def test_bad_inputs():
    inputs = ['x = (', 'x = (\n', 'x = (\n\n']
    for inp in inputs:
        py.test.raises(TokenError, pypy_parse, inp)
