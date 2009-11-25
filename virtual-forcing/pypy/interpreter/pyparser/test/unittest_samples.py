"""test module for CPython / PyPy nested tuples comparison"""

import os, os.path as osp
import sys
from pypy.interpreter.pyparser.pythonutil import python_parse, pypy_parse
from pprint import pprint
from pypy.interpreter.pyparser import grammar
grammar.DEBUG = False
from symbol import sym_name


def name(elt):
    return "%s[%s]"% (sym_name.get(elt,elt),elt)

def read_samples_dir():
    return [osp.join('samples', fname) for fname in os.listdir('samples') if fname.endswith('.py')]

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
            raise AssertionError('Found difference at %s : %s != %s' %
                                 (curpos, name(elt1), name(elt2) ), curpos)

from time import time, clock
def test_samples( samples ):
    time_reports = {}
    for sample in samples:
        print "testing", sample
        tstart1, cstart1 = time(), clock()
        pypy_tuples = pypy_parse(sample)
        tstart2, cstart2 = time(), clock()
        python_tuples = python_parse(sample)
        time_reports[sample] = (time() - tstart2, tstart2-tstart1, clock() - cstart2, cstart2-cstart1 )
        #print "-"*10, "PyPy parse results", "-"*10
        #print ''.join(print_sym_tuple(pypy_tuples, names=True))
        #print "-"*10, "CPython parse results", "-"*10
        #print ''.join(print_sym_tuple(python_tuples, names=True))
        print
        try:
            assert_tuples_equal(pypy_tuples, python_tuples)
        except AssertionError,e:
            error_path = e.args[-1]
            print "ERROR PATH =", error_path
            print "="*80
            print file(sample).read()
            print "="*80
            print "-"*10, "PyPy parse results", "-"*10
            print ''.join(print_sym_tuple(pypy_tuples, names=True, trace=error_path))
            print "-"*10, "CPython parse results", "-"*10
            print ''.join(print_sym_tuple(python_tuples, names=True, trace=error_path))
            print "Failed on (%s)" % sample
            # raise
    pprint(time_reports)

if __name__=="__main__":
    import getopt
    opts, args = getopt.getopt( sys.argv[1:], "d:", [] )
    for opt, val in opts:
        if opt == "-d":
            pass
#            set_debug(int(val))
    if args:
        samples = args
    else:
        samples = read_samples_dir()

    test_samples( samples )
