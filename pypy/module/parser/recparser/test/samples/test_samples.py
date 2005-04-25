


import os, os.path as osp
import sys
from ebnf import parse_grammar
from python import python_parse, pypy_parse, set_debug
from pprint import pprint
import grammar
grammar.DEBUG = False
from symbol import sym_name


def name(elt):
    return "%s[%d]"% (sym_name.get(elt,elt),elt)

def read_samples_dir():
    return [osp.join('samples', fname) for fname in os.listdir('samples')
            if fname.endswith('.py')]


def print_sym_tuple( tup ):
    print "\n(",
    for elt in tup:
        if type(elt)==int:
            print name(elt),
        elif type(elt)==str:
            print repr(elt),
        else:
            print_sym_tuple(elt)
    print ")",

def assert_tuples_equal(tup1, tup2, curpos = (), disp=""):
    if disp:
        print "\n"+disp+"(",
    for index, (elt1, elt2) in enumerate(zip(tup1, tup2)):
        if disp and elt1==elt2 and type(elt1)==int:
            print name(elt1),
        if elt1 != elt2:
            if type(elt1) is tuple and type(elt2) is tuple:
                if disp:
                    disp=disp+" "
                assert_tuples_equal(elt1, elt2, curpos + (index,), disp)
            print
            print "TUP1"
            print_sym_tuple(tup1)
            print
            print "TUP2"
            print_sym_tuple(tup2)
            
            raise AssertionError('Found difference at %s : %s != %s' %
                                 (curpos, name(elt1), name(elt2) ), curpos)
    if disp:
        print ")",

def test_samples( samples ):
    for sample in samples:
        pypy_tuples = pypy_parse(sample)
        python_tuples = python_parse(sample)
        print "="*20
        print file(sample).read()
        print "-"*10
        pprint(pypy_tuples)
        print "-"*10
        pprint(python_tuples)
        try:
            assert_tuples_equal( python_tuples, pypy_tuples, disp=" " )
            assert python_tuples == pypy_tuples
        except AssertionError,e:
            print
            print "python_tuples"
            show( python_tuples, e.args[-1] )
            print
            print "pypy_tuples"
            show( pypy_tuples, e.args[-1] )
            raise


def show( tup, idxs ):
    for level, i in enumerate(idxs):
        print " "*level , tup
        tup=tup[i]
    print tup

if __name__=="__main__":
    import getopt
    opts, args = getopt.getopt( sys.argv[1:], "d:", [] )
    for opt, val in opts:
        if opt=="-d":
            set_debug(int(val))
    if args:
        samples = args
    else:
        samples = read_samples_dir()

    test_samples( samples )
