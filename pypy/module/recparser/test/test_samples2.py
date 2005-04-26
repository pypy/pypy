"""test module for CPython / PyPy nested tuples comparison"""
import os, os.path as osp
from pypy.module.recparser.pythonutil import python_parse, pypy_parse
from pprint import pprint
from pypy.module.recparser import grammar
grammar.DEBUG = False
from symbol import sym_name

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
            if type(elt1) is tuple and type(elt2) is tuple:
                assert_tuples_equal(elt1, elt2, curpos + (index,))
            raise AssertionError('Found difference at %s : %s != %s\n' %
                                 (curpos, name(elt1), name(elt2) ), curpos)

def test_samples():
    samples_dir = osp.join(osp.dirname(__file__), 'samples')
    for fname in os.listdir(samples_dir):
        if not fname.endswith('.py'):
            continue
        abspath = osp.join(samples_dir, fname)
        yield check_parse, abspath

def check_parse(filepath):
    pypy_tuples = pypy_parse(filepath)
    python_tuples = python_parse(filepath)
    try:
        assert_tuples_equal(pypy_tuples, python_tuples)
    except AssertionError, e:
        error_path = e.args[-1]
        print "ERROR PATH =", error_path
        print "="*80
        print file(filepath).read()
        print "="*80
        print "-"*10, "PyPy parse results", "-"*10
        print ''.join(print_sym_tuple(pypy_tuples, names=True, trace=error_path))
        print "-"*10, "CPython parse results", "-"*10
        print ''.join(print_sym_tuple(python_tuples, names=True, trace=error_path))
        assert False, filepath
    
