"""test module for CPython / PyPy nested tuples comparison"""
import os, os.path as osp
from symbol import sym_name
from pprint import pprint

import py.test

from pypy.interpreter.pyparser.pythonutil import python_parsefile, \
    pypy_parsefile, python_parse, pypy_parse
from pypy.interpreter.pyparser import grammar
from pypy.interpreter.pyparser.pythonlexer import TokenError
from pypy.interpreter.pyparser.pythonparse import PYTHON_VERSION, PYPY_VERSION
grammar.DEBUG = False


# these samples are skipped if the native version of Python does not match
# the version of the grammar we use
GRAMMAR_MISMATCH = PYTHON_VERSION != PYPY_VERSION
SKIP_IF_NOT_NATIVE = [
    "snippet_samples.py",
    "snippet_import_statements.py",
]


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
    samples_dir = osp.join(osp.dirname(__file__), 'samples')
    # samples_dir = osp.dirname(os.__file__)
    for use_lookahead in (True, False):
        grammar.USE_LOOKAHEAD = use_lookahead
        for fname in os.listdir(samples_dir):
            if not fname.endswith('.py'):
                continue
            if GRAMMAR_MISMATCH and fname in SKIP_IF_NOT_NATIVE:
                print "Skipping", fname
                continue
            abspath = osp.join(samples_dir, fname)
            yield check_parse, abspath

def _check_tuples_equality(pypy_tuples, python_tuples, testname):
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

def check_parse(filepath):
    pypy_tuples = pypy_parsefile(filepath)
    python_tuples = python_parsefile(filepath)
    _check_tuples_equality(pypy_tuples, python_tuples, filepath)


def check_parse_input(snippet, mode, lineno=False):
    pypy_tuples = pypy_parse(snippet, mode, lineno)
    python_tuples = python_parse(snippet, mode, lineno)
    _check_tuples_equality(pypy_tuples, python_tuples, snippet)

def test_eval_inputs():
    snippets = [
        '6*7',
        'a+b*c/d',
        'True and False',
        ]
    for snippet in snippets:
        yield check_parse_input, snippet, 'eval', True
        yield check_parse_input, snippet, 'eval', False

def test_exec_inputs():
    snippets = [
        # '\t # hello\n ',
        'print 6*7', 'if 1:\n  x\n',
        ]
    for snippet in snippets:
        yield check_parse_input, snippet, 'exec', True
        yield check_parse_input, snippet, 'exec', False        

def test_single_inputs():
    snippets = ['a=1', 'True', 'def f(a):\n    return a+1\n\n']
    for snippet in snippets:
        yield check_parse_input, snippet, 'single', True
        yield check_parse_input, snippet, 'single', False        

    
def test_bad_inputs():
    inputs = ['x = (', 'x = (\n', 'x = (\n\n']
    for inp in inputs:
        py.test.raises(TokenError, pypy_parse, inp)
