# here only to make test runs work even if not running on top of PyPy
import sys, new

def builtinify(f):
    return f

pypy = new.module('__pypy__')
pypy.builtinify = builtinify
sys.modules.setdefault('__pypy__', pypy)
