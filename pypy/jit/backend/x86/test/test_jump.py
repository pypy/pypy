from pypy.jit.backend.x86.ri386 import *
from pypy.jit.backend.x86.regalloc import X86FrameManager
from pypy.jit.backend.x86.jump import remap_frame_layout

frame_pos = X86FrameManager.frame_pos

class MockAssembler:
    def __init__(self):
        self.ops = []

    def regalloc_mov(self, from_loc, to_loc):
        self.ops.append(('mov', from_loc, to_loc))

    def regalloc_push(self, loc):
        self.ops.append(('push', loc))

    def regalloc_pop(self, loc):
        self.ops.append(('pop', loc))

    def got(self, expected):
        print '------------------------ comparing ---------------------------'
        for op1, op2 in zip(self.ops, expected):
            print '%-38s| %-38s' % (op1, op2)
            if op1 == op2:
                continue
            assert len(op1) == len(op2)
            for x, y in zip(op1, op2):
                if isinstance(x, MODRM) and isinstance(y, MODRM):
                    assert x.byte == y.byte
                    assert x.extradata == y.extradata
                else:
                    assert x == y
        assert len(self.ops) == len(expected)
        return True


def test_trivial():
    assembler = MockAssembler()
    remap_frame_layout(assembler, [], [], '?')
    assert assembler.ops == []
    remap_frame_layout(assembler, [eax, ebx, ecx, edx, esi, edi],
                                  [eax, ebx, ecx, edx, esi, edi], '?')
    assert assembler.ops == []
    s8 = frame_pos(1, 1)
    s12 = frame_pos(31, 1)
    s20 = frame_pos(6, 1)
    remap_frame_layout(assembler, [eax, ebx, ecx, s20, s8, edx, s12, esi, edi],
                                  [eax, ebx, ecx, s20, s8, edx, s12, esi, edi],
                                  '?')
    assert assembler.ops == []

def test_simple_registers():
    assembler = MockAssembler()
    remap_frame_layout(assembler, [eax, ebx, ecx], [edx, esi, edi], '?')
    assert assembler.ops == [('mov', eax, edx),
                             ('mov', ebx, esi),
                             ('mov', ecx, edi)]

def test_simple_framelocs():
    assembler = MockAssembler()
    s8 = frame_pos(0, 1)
    s12 = frame_pos(13, 1)
    s20 = frame_pos(20, 1)
    s24 = frame_pos(221, 1)
    remap_frame_layout(assembler, [s8, eax, s12], [s20, s24, edi], edx)
    assert assembler.ops == [('mov', s8, edx),
                             ('mov', edx, s20),
                             ('mov', eax, s24),
                             ('mov', s12, edi)]

def test_reordering():
    assembler = MockAssembler()
    s8 = frame_pos(8, 1)
    s12 = frame_pos(12, 1)
    s20 = frame_pos(19, 1)
    s24 = frame_pos(1, 1)
    remap_frame_layout(assembler, [eax, s8, s20, ebx],
                                  [s8, ebx, eax, edi], '?')
    assert assembler.got([('mov', ebx, edi),
                          ('mov', s8, ebx),
                          ('mov', eax, s8),
                          ('mov', s20, eax)])

def test_cycle():
    assembler = MockAssembler()
    s8 = frame_pos(8, 1)
    s12 = frame_pos(12, 1)
    s20 = frame_pos(19, 1)
    s24 = frame_pos(1, 1)
    remap_frame_layout(assembler, [eax, s8, s20, ebx],
                                  [s8, ebx, eax, s20], '?')
    assert assembler.got([('push', s8),
                          ('mov', eax, s8),
                          ('mov', s20, eax),
                          ('mov', ebx, s20),
                          ('pop', ebx)])

def test_cycle_2():
    assembler = MockAssembler()
    s8 = frame_pos(8, 1)
    s12 = frame_pos(12, 1)
    s20 = frame_pos(19, 1)
    s24 = frame_pos(1, 1)
    s2 = frame_pos(2, 1)
    s3 = frame_pos(3, 1)
    remap_frame_layout(assembler,
                       [eax, s8, edi, s20, eax, s20, s24, esi, s2, s3],
                       [s8, s20, edi, eax, edx, s24, ebx, s12, s3, s2],
                       ecx)
    assert assembler.got([('mov', eax, edx),
                          ('mov', s24, ebx),
                          ('mov', esi, s12),
                          ('mov', s20, ecx),
                          ('mov', ecx, s24),
                          ('push', s8),
                          ('mov', eax, s8),
                          ('mov', s20, eax),
                          ('pop', s20),
                          ('push', s3),
                          ('mov', s2, ecx),
                          ('mov', ecx, s3),
                          ('pop', s2)])

def test_constants():
    assembler = MockAssembler()
    c3 = imm(3)
    remap_frame_layout(assembler, [c3], [eax], '?')
    assert assembler.ops == [('mov', c3, eax)]
    assembler = MockAssembler()
    s12 = frame_pos(12, 1)
    remap_frame_layout(assembler, [c3], [s12], '?')
    assert assembler.ops == [('mov', c3, s12)]

def test_constants_and_cycle():
    assembler = MockAssembler()
    c3 = imm(3)
    s12 = frame_pos(13, 1)
    remap_frame_layout(assembler, [ebx, c3,  s12],
                                  [s12, eax, ebx], edi)
    assert assembler.ops == [('mov', c3, eax),
                             ('push', s12),
                             ('mov', ebx, s12),
                             ('pop', ebx)]
