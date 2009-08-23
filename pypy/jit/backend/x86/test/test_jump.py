from pypy.jit.backend.x86.ri386 import *
from pypy.jit.backend.x86.jump import remap_stack_layout

class MockAssembler:
    def __init__(self):
        self.ops = []

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
