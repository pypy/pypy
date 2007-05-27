import py
from pypy.lang.js import interpreter
from pypy.lang.js.operations import *
from pypy.lang.js.jsobj import W_Number, empty_context

class MOCKNode(Node):
    def __init__(self, pos, ret):
        self.pos = pos
        self.ret = ret

    def eval(self, ctx):
        return self.ret

POSDEF = Position()
VALDEF = MOCKNode(POSDEF, 1)

def test_return():
    ctx = empty_context()
    r = Return(POSDEF, VALDEF)
    block = Block(POSDEF, [r])
    selements = SourceElements(POSDEF, [], {}, [r])
    br = block.execute(ctx)
    sr = selements.execute(ctx)
    assert br == 1 and sr == 1
