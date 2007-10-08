
from pypy.tool.pairtype import pairtype, pair, extendabletype

def test_binop(): 
    ### Binary operation example
    class __extend__(pairtype(int, int)):
        def add((x, y)):
            return 'integer: %s+%s' % (x, y)
        def sub((x, y)):
            return 'integer: %s-%s' % (x, y)

    class __extend__(pairtype(bool, bool)):
        def add((x, y)):
            return 'bool: %s+%s' % (x, y)

    assert pair(3,4).add() == 'integer: 3+4'
    assert pair(3,4).sub() == 'integer: 3-4'
    assert pair(3,True).add() == 'integer: 3+True'
    assert pair(3,True).sub() == 'integer: 3-True'
    assert pair(False,4).add() == 'integer: False+4'
    assert pair(False,4).sub() == 'integer: False-4'
    assert pair(False,True).add() == 'bool: False+True'
    assert pair(False,True).sub() == 'integer: False-True'

def test_somebuiltin(): 
    ### Operation on built-in types
    class MiniPickler:
        def __init__(self):
            self.data = []
        def emit(self, datum):
            self.data.append(datum)

    class __extend__(pairtype(MiniPickler, int)):
        def write((pickler, x)):
            pickler.emit('I%d' % x)

    class __extend__(pairtype(MiniPickler, str)):
        def write((pickler, x)):
            pickler.emit('S%s' % x)

    class __extend__(pairtype(MiniPickler, list)):
        def write((pickler, x)):
            for item in x:
                pair(pickler, item).write()
            pickler.emit('L%d' % len(x))

    p = MiniPickler()
    pair(p, [1, 2, ['hello', 3]]).write()
    assert p.data == ['I1', 'I2', 'Shello', 'I3', 'L2', 'L3']

def test_some_multimethod(): 
    ### Another multimethod example
    class Block:
        def __init__(self, exit):
            self.exit = exit
    class Jump:
        pass
    class Switch:
        pass
    
    class C_Generator:
        def __init__(self):
            self.lines = []

    class __extend__(pairtype(C_Generator, Block)):
        def emit((gen, block), inputvars):
            gen.lines.append("C code for block")
            outputvars = inputvars + ['v4', 'v5']
            pair(gen, block.exit).emit(outputvars)

    class __extend__(pairtype(C_Generator, Jump)):
        def emit((gen, jump), inputvars):
            gen.lines.append("goto xyz")

    class __extend__(pairtype(C_Generator, Switch)):
        def emit((gen, jump), inputvars):
            gen.lines.append("switch (%s) { ... }" % inputvars[-1])

    g = C_Generator()
    pair(g, Block(Switch())).emit(['v1', 'v2'])
    assert g.lines == ["C code for block", "switch (v5) { ... }"] 

    class Lisp_Generator:
        def __init__(self):
            self.progn = []

    class __extend__(pairtype(Lisp_Generator, Block)):
        def emit((gen, block), inputvars):
            gen.progn.append("(do 'something)")

    g = Lisp_Generator()
    pair(g, Block(Switch())).emit(['v1', 'v2'])
    assert g.progn == ["(do 'something)"]

def test_multiple_extend():
    class A:
        __metaclass__ = extendabletype
    class B:
        __metaclass__ = extendabletype

    class __extend__(A,B):

        def f(self):
            pass

    assert hasattr(A, 'f')
    assert hasattr(B, 'f')
    

        
