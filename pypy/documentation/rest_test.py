from __future__ import generators

import py
import pypy

pydir = py.magic.autopath(vars(py)).dirpath()
rest = pydir.join('bin', 'py.rest').getpymodule()

docdir = py.path.svnwc(pypy.__file__).dirpath('documentation')

def restcheck(path):
    try:
        import docutils
    except ImportError:
        py.test.skip("docutils not importable")
    rest.process(path)
    check_htmllinks(path) 
    #assert not out

def test_rest_files():
    for x in docdir.listdir('*.txt'):
        yield restcheck, x

def check_htmllinks(path): 
    ddir = docdir.localpath 

    for lineno, line in py.builtin.enumerate(path.readlines()): 
        line = line.strip()
        if line.startswith('.. _'): 
            l = line.split(':', 1)
            if len(l) != 2: 
                continue
            tryfn = l[1].strip() 
            if tryfn.startswith('http:'): 
                # XXX try retrieve? 
                pass 
            elif tryfn.endswith('.html'): 
                # assume it should be a file 
                fn = ddir.join(tryfn) 
                fn = fn.new(ext='.txt')
                if not fn.check(file=1): 
                    py.test.fail("reference error %r in %s:%d" %(
                                  tryfn, path.basename, lineno+1))
            else: 
                # yes, what else? 
                pass 

            

