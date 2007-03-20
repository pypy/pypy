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
    return osp.join(osp.dirname(__file__), name)

def write_module(name):
    clean_module(name)
    f = open(_make_filename(name), 'w')
    f.write(code)
    f.close()

def clean_module(name):
    name = _make_filename(name)
    if os.path.isfile(name):
        os.unlink(name)
    if os.path.isfile(name+'c'):
        os.unlink(name+'c')

