import py

from pypy.jit.backend.x86.test.test_jump import MockAssembler
from pypy.jit.backend.arm.registers import *
from pypy.jit.backend.arm.locations import *
from pypy.jit.backend.arm.regalloc import ARMFrameManager
from pypy.jit.backend.arm.jump import remap_frame_layout
from pypy.jit.metainterp.history import INT

frame_pos = ARMFrameManager.frame_pos

class TestJump(object):
    def setup_method(self, m):
        self.assembler = MockAssembler()

    def test_trivial(self):
        remap_frame_layout(self.assembler, [], [], '?')
        assert self.assembler.ops == []
        remap_frame_layout(self.assembler, [r0, r1, r3, r5, r6, r7, r9],
                                      [r0, r1, r3, r5, r6, r7, r9], '?')
        assert self.assembler.ops == []
        s8 = frame_pos(1, INT)
        s12 = frame_pos(31, INT)
        s20 = frame_pos(6, INT)
        remap_frame_layout(self.assembler, [r0, r1, s20, s8, r3, r5, r6, s12, r7, r9],
                                      [r0, r1, s20, s8, r3, r5, r6, s12, r7, r9],
                                      '?')
        assert self.assembler.ops == []

    def test_simple_registers(self):
        remap_frame_layout(self.assembler, [r0, r1, r2], [r3, r4, r5], '?')
        assert self.assembler.ops == [('mov', r0, r3),
                                 ('mov', r1, r4),
                                 ('mov', r2, r5)]

    def test_simple_framelocs(self):
        s8 = frame_pos(0, INT)
        s12 = frame_pos(13, INT)
        s20 = frame_pos(20, INT)
        s24 = frame_pos(221, INT)
        remap_frame_layout(self.assembler, [s8, r7, s12], [s20, s24, r9], ip)
        assert self.assembler.ops == [('mov', s8, ip),
                                 ('mov', ip, s20),
                                 ('mov', r7, s24),
                                 ('mov', s12, r9)]

    def test_reordering(self):
        s8 = frame_pos(8, INT)
        s12 = frame_pos(12, INT)
        s20 = frame_pos(19, INT)
        s24 = frame_pos(1, INT)
        remap_frame_layout(self.assembler, [r7, s8, s20, r4],
                                      [s8, r4, r7, r2], '?')
        assert self.assembler.got([('mov', r4, r2),
                              ('mov', s8, r4),
                              ('mov', r7, s8),
                              ('mov', s20, r7)])

    def test_cycle(self):
        s8 = frame_pos(8, INT)
        s12 = frame_pos(12, INT)
        s20 = frame_pos(19, INT)
        s24 = frame_pos(1, INT)
        remap_frame_layout(self.assembler, [r4, s8, s20, r7],
                                      [s8, r7, r4, s20], '?')
        assert self.assembler.got([('push', s8),
                              ('mov', r4, s8),
                              ('mov', s20, r4),
                              ('mov', r7, s20),
                              ('pop', r7)])

    def test_cycle_2(self):
        s8 = frame_pos(8, INT)
        s12 = frame_pos(12, INT)
        s20 = frame_pos(19, INT)
        s24 = frame_pos(1, INT)
        s2 = frame_pos(2, INT)
        s3 = frame_pos(3, INT)
        remap_frame_layout(self.assembler,
                           [r0, s8, r1, s20, r0, s20, s24, r3, s2, s3],
                           [s8, s20, r1, r0, r4, s24, r5, s12, s3, s2],
                           ip)
        assert self.assembler.got([('mov', r0, r4),
                              ('mov', s24, r5),
                              ('mov', r3, s12),
                              ('mov', s20, ip),
                              ('mov', ip, s24),
                              ('push', s8),
                              ('mov', r0, s8),
                              ('mov', s20, r0),
                              ('pop', s20),
                              ('push', s3),
                              ('mov', s2, ip),
                              ('mov', ip, s3),
                              ('pop', s2)])

    def test_constants(self):
        c3 = ImmLocation(3)
        remap_frame_layout(self.assembler, [c3], [r0], '?')
        assert self.assembler.ops == [('mov', c3, r0)]

    def test_constants2(self):
        c3 = ImmLocation(3)
        s12 = frame_pos(12, INT)
        remap_frame_layout(self.assembler, [c3], [s12], '?')
        assert self.assembler.ops == [('mov', c3, s12)]

    def test_constants_and_cycle(self):
        c3 = ImmLocation(3)
        s12 = frame_pos(13, INT)
        remap_frame_layout(self.assembler, [r5, c3,  s12],
                                      [s12, r0, r5], r1)
        assert self.assembler.ops == [('mov', c3, r0),
                                 ('push', s12),
                                 ('mov', r5, s12),
                                 ('pop', r5)]
