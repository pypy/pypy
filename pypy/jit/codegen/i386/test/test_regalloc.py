
from pypy.jit.codegen.i386.regalloc  import RegAllocator
from pypy.jit.codegen.i386 import operation as op
from pypy.jit.codegen.i386.ri386 import mem, ebp, I386CodeBuilder
from pypy.jit.codegen.model import GenVar

WORD = op.WORD

class DummyMc:
    def __init__(self):
        self.ops = []
    
    def __getattr__(self, attr):
        def append_to_ops(*args):
            if attr == 'write':
                return
            self.ops.append((attr, args))
        return append_to_ops
        

class TestRegalloc:
    def test_basics(self):
        """ This tests a simple two-arg routine
        """
        varx, vary = GenVar(), GenVar()
        x = mem(ebp)
        y = mem(ebp, WORD)
        finalloc = mem(ebp, 2*WORD)
        operations = [op.OpIntAdd(varx, vary)]
        regalloc = RegAllocator(operations)
        regalloc.set_final(operations, [finalloc])
        regalloc.compute_lifetimes()
        regalloc.init_reg_alloc([varx, vary], [x, y])
        dummy_mc = DummyMc()
        regalloc.generate_operations(dummy_mc)
        regalloc.generate_final_moves(operations, [finalloc])
        names = (op for op, args in dummy_mc.ops)
        assert list(names) == ['MOV', 'ADD', 'PUSH', 'POP']
        # XXX more asserts here
