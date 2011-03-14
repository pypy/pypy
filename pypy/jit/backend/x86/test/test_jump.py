from pypy.jit.backend.x86.regloc import *
from pypy.jit.backend.x86.regalloc import X86FrameManager
from pypy.jit.backend.x86.jump import ConcreteJumpRemapper
from pypy.jit.metainterp.history import INT

frame_pos = X86FrameManager.frame_pos

class MockAssembler(ConcreteJumpRemapper):
    def __init__(self, tmpreg='?'):
        self.ops = []
        self.tmpreg = tmpreg

    def get_tmp_reg(self, src):
        return self.tmpreg

    def simple_move(self, from_loc, to_loc):
        self.ops.append(('mov', from_loc, to_loc))

    def push(self, loc):
        self.ops.append(('push', loc))

    def pop(self, loc):
        self.ops.append(('pop', loc))

    def got(self, expected):
        print '------------------------ comparing ---------------------------'
        for op1, op2 in zip(self.ops, expected):
            print '%-38s| %-38s' % (op1, op2)
            if op1 == op2:
                continue
            assert len(op1) == len(op2)
            for x, y in zip(op1, op2):
                if isinstance(x, StackLoc) and isinstance(y, MODRM):
                    assert x.byte == y.byte
                    assert x.extradata == y.extradata
                else:
                    assert x == y
        assert len(self.ops) == len(expected)
        return True


def test_trivial():
    assembler = MockAssembler()
    assembler.remap_frame_layout([], [])
    assert assembler.ops == []
    assembler.remap_frame_layout([eax, ebx, ecx, edx, esi, edi],
                                 [eax, ebx, ecx, edx, esi, edi])
    assert assembler.ops == []
    s8 = frame_pos(1, INT)
    s12 = frame_pos(31, INT)
    s20 = frame_pos(6, INT)
    assembler.remap_frame_layout([eax, ebx, ecx, s20, s8, edx, s12, esi, edi],
                                 [eax, ebx, ecx, s20, s8, edx, s12, esi, edi])
    assert assembler.ops == []

def test_simple_registers():
    assembler = MockAssembler()
    assembler.remap_frame_layout([eax, ebx, ecx], [edx, esi, edi])
    assert assembler.ops == [('mov', eax, edx),
                             ('mov', ebx, esi),
                             ('mov', ecx, edi)]

def test_simple_framelocs():
    assembler = MockAssembler(edx)
    s8 = frame_pos(0, INT)
    s12 = frame_pos(13, INT)
    s20 = frame_pos(20, INT)
    s24 = frame_pos(221, INT)
    assembler.remap_frame_layout([s8, eax, s12], [s20, s24, edi])
    assert assembler.ops == [('mov', s8, edx),
                             ('mov', edx, s20),
                             ('mov', eax, s24),
                             ('mov', s12, edi)]

def test_reordering():
    assembler = MockAssembler()
    s8 = frame_pos(8, INT)
    s12 = frame_pos(12, INT)
    s20 = frame_pos(19, INT)
    s24 = frame_pos(1, INT)
    assembler.remap_frame_layout([eax, s8, s20, ebx],
                                 [s8, ebx, eax, edi])
    assert assembler.got([('mov', ebx, edi),
                          ('mov', s8, ebx),
                          ('mov', eax, s8),
                          ('mov', s20, eax)])

def test_cycle():
    assembler = MockAssembler()
    s8 = frame_pos(8, INT)
    s12 = frame_pos(12, INT)
    s20 = frame_pos(19, INT)
    s24 = frame_pos(1, INT)
    assembler.remap_frame_layout([eax, s8, s20, ebx],
                                 [s8, ebx, eax, s20])
    assert assembler.got([('push', s8),
                          ('mov', eax, s8),
                          ('mov', s20, eax),
                          ('mov', ebx, s20),
                          ('pop', ebx)])

def test_cycle_2():
    assembler = MockAssembler(ecx)
    s8 = frame_pos(8, INT)
    s12 = frame_pos(12, INT)
    s20 = frame_pos(19, INT)
    s24 = frame_pos(1, INT)
    s2 = frame_pos(2, INT)
    s3 = frame_pos(3, INT)
    assembler.remap_frame_layout(
                       [eax, s8, edi, s20, eax, s20, s24, esi, s2, s3],
                       [s8, s20, edi, eax, edx, s24, ebx, s12, s3, s2])
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
    assembler.remap_frame_layout([c3], [eax])
    assert assembler.ops == [('mov', c3, eax)]
    assembler = MockAssembler()
    s12 = frame_pos(12, INT)
    assembler.remap_frame_layout([c3], [s12])
    assert assembler.ops == [('mov', c3, s12)]

def test_constants_and_cycle():
    assembler = MockAssembler(edi)
    c3 = imm(3)
    s12 = frame_pos(13, INT)
    assembler.remap_frame_layout([ebx, c3,  s12],
                                 [s12, eax, ebx])
    assert assembler.ops == [('mov', c3, eax),
                             ('push', s12),
                             ('mov', ebx, s12),
                             ('pop', ebx)]
