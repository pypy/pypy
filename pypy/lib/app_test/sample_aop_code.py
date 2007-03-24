import py 

code = """
def foo(b, c):
    '''
    pre:
        b < c
    '''
    print 'foo'
    a = 2
    d = bar(a)
    print d
    return b+a+c+d


def bar(val):
    print 'bar', val
    return 42

def baz(b,c):
    try:
        return foo(b,c)
    finally:
        bar(3)

class Mumble:
    def __init__(self, param):
        self.p = param
    def frobble(self, b):
        return 3 * self.p  + b
    def __del__(self):
        print 'Mumble goes poof'

def truc():
    m = Mumble(2)
    r = m.frobble(1)
    print 'truc', r, 'expected 7'
    return r
"""
import os
import os.path as osp

def _make_filename(name):
    if not name.endswith('.py'):
        name += ".py"
    base = py.test.ensuretemp("aop_test")
    return base.join(name)

def _write_module(name):
    f = _make_filename(name).open('w')
    f.write(code)
    f.close()

def import_(name):
    _write_module(name)
    p = _make_filename(name)
    return p.pyimport()
