import sys
import os
#print "dyncode_test: __name__ ==", __name__
from py.__impl__.magic import dyncode, exprinfo
import py

def setup_module(mod):
    py.magic.invoke(dyncode=1)
def teardown_module(mod):
    py.magic.revoke(dyncode=1)

def test_dyncode_trace():
    source = """
        def f():
            raise ValueError
    """
    co = dyncode.compile2(source)
    exec co 
    excinfo = py.test.raises(ValueError, f)
    filename, lineno = dyncode.tbinfo(excinfo[2])
    line = dyncode.getline(filename, lineno)
    assert line.strip() == 'raise ValueError'

def test_dyncode_trace_multiple():
    test_dyncode_trace()
    test_dyncode_trace()

def test_unique_filenames():
    fn1 = dyncode._makedynfilename('fn','source')
    fn2 = dyncode._makedynfilename('fn','source')
    assert fn1 != fn2

def test_syntaxerror_rerepresentation():
    ex = py.test.raises(SyntaxError, dyncode.compile2, 'x x')[1]
    assert ex.lineno == 1
    assert ex.offset == 3
    assert ex.text.strip(), 'x x'

def test_getfuncsource_dynamic():
    source = """
        def f():
            raise ValueError

        def g(): pass
    """
    co = dyncode.compile2(source)
    exec co 
    source = dyncode.getsource(f)
    assert dyncode.getsource(f) == 'def f():\n    raise ValueError\n'
    assert dyncode.getsource(g) == 'def g(): pass\n'

def test_getpyfile():
    fn = dyncode.getpyfile(dyncode)
    assert os.path.exists(fn)

def test_getstartingblock_singleline():
    class A:
        def __init__(self, *args):
            frame = sys._getframe(1)
            self.source = dyncode.getparseablestartingblock(frame)
           
    x = A('x', 'y') 

    l = [i for i in x.source.split('\n') if i.strip()]
    assert len(l) == 1

def test_getstartingblock_multiline():
    class A:
        def __init__(self, *args):
            frame = sys._getframe(1)
            self.source = dyncode.getparseablestartingblock(frame) 
           
    x = A('x', 
          'y' \
          , 
          'z') 

    l = [i for i in x.source.split('\n') if i.strip()]
    assert len(l) == 4

def test_getline_finally():
    def c(): pass
    excinfo = py.test.raises(TypeError, """
           teardown = None
           try:
                c(1) 
           finally:
                if teardown: 
                    teardown() 
    """)
    tb = dyncode.gettb(excinfo[2], -1)
    source = dyncode.getparseablestartingblock(tb) 
    assert source.strip() == 'c(1)' 
