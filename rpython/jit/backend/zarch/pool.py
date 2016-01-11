from rpython.jit.backend.zarch import registers as r
from rpython.jit.backend.zarch import locations as l
from rpython.jit.metainterp.history import (INT, REF, FLOAT,
        TargetToken)
from rpython.rlib.objectmodel import we_are_translated
from rpython.jit.metainterp.resoperation import rop
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.jit.backend.zarch.arch import (WORD,
        RECOVERY_GCMAP_POOL_OFFSET, RECOVERY_TARGET_POOL_OFFSET)
from rpython.rlib.longlong2float import float2longlong

class LiteralPool(object):
    def __init__(self):
        self.size = 0
        # the offset to index the pool
        self.pool_start = 0
        self.label_offset = 0
        self.label_count = 0
        self.offset_map = {}
        self.constant_64_zeros = -1
        self.constant_64_ones = -1
        self.constant_64_sign_bit = -1
        self.constant_max_64_positive = -1

    def ensure_can_hold_constants(self, asm, op):
        opnum = op.getopnum()
        if op.is_guard():
            # 1x gcmap pointer
            # 1x target address
            self.offset_map[op.getdescr()] = self.size
            self.reserve_literal(2 * 8)
        elif op.getopnum() == rop.JUMP:
            descr = op.getdescr()
            if descr not in asm.target_tokens_currently_compiling:
                # this is a 'long' jump instead of a relative jump
                self.offset_map[descr] = self.size
                self.reserve_literal(8)
        elif op.getopnum() == rop.LABEL:
            descr = op.getdescr()
            if descr not in asm.target_tokens_currently_compiling:
                # this is a 'long' jump instead of a relative jump
                self.offset_map[descr] = self.size
        elif op.getopnum() == rop.INT_INVERT:
            self.constant_64_ones = 1 # we need constant ones!!!
        elif op.getopnum() == rop.INT_MUL_OVF:
            self.constant_64_sign_bit = 1
            self.constant_max_64_positive = 1
        elif opnum == rop.INT_RSHIFT or opnum == rop.INT_LSHIFT or \
             opnum == rop.UINT_RSHIFT:
            a0 = op.getarg(0)
            if a0.is_constant():
                self.offset_map[a0] = self.size
                self.reserve_literal(8)
            return
        elif opnum == rop.GC_STORE or opnum == rop.GC_STORE_INDEXED:
            arg = op.getarg(0)
            if arg.is_constant():
                self.offset_map[arg] = self.size
                self.reserve_literal(8)
            arg = op.getarg(2)
            if arg.is_constant():
                self.offset_map[arg] = self.size
                self.reserve_literal(8)
            return
        elif opnum in (rop.GC_LOAD_F,
                       rop.GC_LOAD_I,
                       rop.GC_LOAD_R,) \
             or opnum in (rop.GC_LOAD_INDEXED_F,
                          rop.GC_LOAD_INDEXED_R,
                          rop.GC_LOAD_INDEXED_I,):
            arg = op.getarg(0)
            if arg.is_constant():
                self.offset_map[arg] = self.size
                self.reserve_literal(8)
            return
        elif op.is_call_release_gil():
            for arg in op.getarglist()[1:]:
                if arg.is_constant():
                    self.offset_map[arg] = self.size
                    self.reserve_literal(8)
            return
        for arg in op.getarglist():
            if arg.is_constant():
                self.offset_map[arg] = self.size
                self.reserve_literal(8)

    def get_descr_offset(self, descr):
        return self.offset_map[descr]

    def get_offset(self, box):
        return self.offset_map[box]

    def reserve_literal(self, size):
        self.size += size

    def reset(self):
        self.pool_start = 0
        self.label_offset = 0
        self.size = 0
        self.offset_map = {}
        self.constant_64_zeros = -1
        self.constant_64_ones = -1
        self.constant_64_sign_bit = -1
        self.constant_max_64_positive -1

    def pre_assemble(self, asm, operations, bridge=False):
        # O(len(operations)). I do not think there is a way
        # around this.
        #
        # Problem:
        # constants such as floating point operations, plain pointers,
        # or integers might serve as parameter to an operation. thus
        # it must be loaded into a register. You cannot do this with
        # assembler immediates, because the biggest immediate value
        # is 32 bit for branch instructions.
        #
        # Solution:
        # the current solution (gcc does the same), use a literal pool
        # located at register r13. This one can easily offset with 20
        # bit signed values (should be enough)
        self.pool_start = asm.mc.get_relative_pos()
        for op in operations:
            self.ensure_can_hold_constants(asm, op)
        if self.size == 0:
            # no pool needed!
            return
        assert self.size % 2 == 0, "not aligned properly"
        asm.mc.write('\x00' * self.size)
        written = 0
        if self.constant_64_ones != -1:
            asm.mc.write('\xFF' * 8)
            self.constant_64_ones = self.size
            written += 8
        if self.constant_64_zeros != -1:
            asm.mc.write('\x00' * 8)
            self.constant_64_zeros = self.size
            written += 8
        if self.constant_64_sign_bit != -1:
            asm.mc.write('\x80' + ('\x00' * 7))
            self.constant_64_sign_bit = self.size
            written += 8
        if self.constant_max_64_positive != -1:
            asm.mc.write('\x7F' + ('\xFF' * 7))
            self.constant_max_64_positive = self.size
            written += 8
        self.size += written
        if not we_are_translated():
            print "pool with %d quad words" % (self.size // 8)

    def overwrite_64(self, mc, index, value):
        index += self.pool_start
        mc.overwrite(index,   chr(value >> 56 & 0xff))
        mc.overwrite(index+1, chr(value >> 48 & 0xff))
        mc.overwrite(index+2, chr(value >> 40 & 0xff))
        mc.overwrite(index+3, chr(value >> 32 & 0xff))
        mc.overwrite(index+4, chr(value >> 24 & 0xff))
        mc.overwrite(index+5, chr(value >> 16 & 0xff))
        mc.overwrite(index+6, chr(value >> 8 & 0xff))
        mc.overwrite(index+7, chr(value & 0xff))

    def post_assemble(self, asm):
        mc = asm.mc
        pending_guard_tokens = asm.pending_guard_tokens
        if self.size == 0:
            return
        for val, offset in self.offset_map.items():
            if not we_are_translated():
                print('pool: %s at offset: %d' % (val, offset))
            if val.is_constant():
                if val.type == FLOAT:
                    self.overwrite_64(mc, offset, float2longlong(val.value))
                elif val.type == INT:
                    i64 = rffi.cast(lltype.Signed, val.value)
                    self.overwrite_64(mc, offset, i64)
                else:
                    assert val.type == REF
                    i64 = rffi.cast(lltype.Signed, val.value)
                    self.overwrite_64(mc, offset, i64)
            else:
                pass

        for guard_token in pending_guard_tokens:
            descr = guard_token.faildescr
            offset = self.offset_map[descr]
            assert isinstance(offset, int)
            guard_token._pool_offset = offset
            ptr = rffi.cast(lltype.Signed, guard_token.gcmap)
            self.overwrite_64(mc, offset + RECOVERY_GCMAP_POOL_OFFSET, ptr)
