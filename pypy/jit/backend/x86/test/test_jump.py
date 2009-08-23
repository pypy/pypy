from pypy.jit.backend.x86.ri386 import *
from pypy.jit.backend.x86.jump import remap_stack_layout

class MockAssembler:
    def __init__(self):
        self.ops = []

    def regalloc_load(self, from_loc, to_loc):
        self.ops.append(('load', from_loc, to_loc))

    def regalloc_store(self, from_loc, to_loc):
        self.ops.append(('store', from_loc, to_loc))


def test_trivial():
    assembler = MockAssembler()
    remap_stack_layout(assembler, [], [])
    assert assembler.ops == []
    remap_stack_layout(assembler, [eax, ebx, ecx, edx, esi, edi],
                                  [eax, ebx, ecx, edx, esi, edi])
    assert assembler.ops == []
    s8 = mem(ebp, -8)
    s12 = mem(ebp, -12)
    s20 = mem(ebp, -20)
    remap_stack_layout(assembler, [eax, ebx, ecx, s20, s8, edx, s12, esi, edi],
                                  [eax, ebx, ecx, s20, s8, edx, s12, esi, edi])
    assert assembler.ops == []

def test_simple_registers():
    assembler = MockAssembler()
    remap_stack_layout(assembler, [eax, ebx, ecx], [edx, esi, edi])
    assert assembler.ops == [('load', eax, edx),
                             ('load', ebx, esi),
                             ('load', ecx, edi)]

def test_simple_stacklocs():
    assembler = MockAssembler()
    s8 = mem(ebp, -8)
    s12 = mem(ebp, -12)
    s20 = mem(ebp, -20)
    s24 = mem(ebp, -24)
    remap_stack_layout(assembler, [s8, eax, s12], [s20, s24, edi], [edx, esi])
    assert assembler.ops == [('load', s8, edx),
                             ('store', edx, s20),
                             ('store', eax, s24),
                             ('load', s12, edi)]
