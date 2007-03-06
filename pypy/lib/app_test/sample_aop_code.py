code = """
def foo(b,c):
    print 'foo'
    a = 2
    d = bar()
    return b+a+c+d


def bar():
    print 'bar'
    return 42

def baz(b,c):
    try:
        return foo(b,c)
    finally:
        bar()
"""
import os
import os.path as osp

def _make_filename(name):
    if not name.endswith('.py'):
        name += ".py"
    return osp.join(osp.dirname(__file__), name)

def write_module(name):
    f = open(_make_filename(name), 'w')
    f.write(code)
    f.close()

def clean_module(name):
    os.unlink(_make_filename(name))
