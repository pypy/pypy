from rpython.jit.backend.zarch import registers as r
from rpython.jit.backend.zarch import locations as l
from rpython.jit.metainterp.history import (INT, REF, FLOAT,
        TargetToken)
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.history import Const
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.jit.backend.zarch.arch import (WORD,
        RECOVERY_GCMAP_POOL_OFFSET, RECOVERY_TARGET_POOL_OFFSET)
from rpython.rlib.longlong2float import float2longlong

class PoolOverflow(Exception):
    pass

class LiteralPool(object):
    def __init__(self):
        self.size = 0
        # the offset to index the pool
        self.pool_start = 0
        self.label_offset = 0
        self.label_count = 0
        # for constant offsets
        self.offset_map = {}
        # for descriptors
        self.offset_descr = {}
        self.constant_64_zeros = -1
        self.constant_64_ones = -1
        self.constant_64_sign_bit = -1
        self.constant_max_64_positive = -1

    def ensure_can_hold_constants(self, asm, op):
        opnum = op.getopnum()
        if op.is_guard():
            # 1x gcmap pointer
            # 1x target address
            self.offset_descr[op.getdescr()] = self.size
            self.allocate_slot(2*8)
        elif op.getopnum() == rop.JUMP:
            descr = op.getdescr()
            if descr not in asm.target_tokens_currently_compiling:
                # this is a 'long' jump instead of a relative jump
                self.offset_descr[descr] = self.size
                self.allocate_slot(8)
        elif op.getopnum() == rop.LABEL:
            descr = op.getdescr()
            if descr not in asm.target_tokens_currently_compiling:
                # this is a 'long' jump instead of a relative jump
                self.offset_descr[descr] = self.size
                self.allocate_slot(8)
        elif op.getopnum() == rop.INT_INVERT:
            self.constant_64_ones = 1 # we need constant ones!!!
        elif op.getopnum() == rop.INT_MUL_OVF:
            self.constant_64_sign_bit = 1
            self.constant_max_64_positive = 1
        elif opnum == rop.INT_RSHIFT or opnum == rop.INT_LSHIFT or \
             opnum == rop.UINT_RSHIFT:
            a0 = op.getarg(0)
            if a0.is_constant():
                self.reserve_literal(8, a0)
            return
        elif opnum == rop.GC_STORE or opnum == rop.GC_STORE_INDEXED:
            arg = op.getarg(0)
            if arg.is_constant():
                self.reserve_literal(8, arg)
            arg = op.getarg(1)
            if arg.is_constant():
                self.reserve_literal(8, arg)
            arg = op.getarg(2)
            if arg.is_constant():
                self.reserve_literal(8, arg)
            return
        elif opnum in (rop.GC_LOAD_F,
                       rop.GC_LOAD_I,
                       rop.GC_LOAD_R,) \
             or opnum in (rop.GC_LOAD_INDEXED_F,
                          rop.GC_LOAD_INDEXED_R,
                          rop.GC_LOAD_INDEXED_I,):
            arg = op.getarg(0)
            if arg.is_constant():
                self.reserve_literal(8, arg)
            arg = op.getarg(1)
            if arg.is_constant():
                self.reserve_literal(8, arg)
            return
        elif op.is_call_release_gil():
            for arg in op.getarglist()[1:]:
                if arg.is_constant():
                    self.reserve_literal(8, arg)
            return
        elif opnum == rop.COND_CALL_GC_WB_ARRAY:
            self.constant_64_ones = 1 # we need constant ones!!!
        for arg in op.getarglist():
            if arg.is_constant():
                self.reserve_literal(8, arg)

    def get_descr_offset(self, descr):
        return self.offset_descr[descr]

    def get_offset(self, box):
        assert box.is_constant()
        uvalue = self.unique_value(box)
        if not we_are_translated():
            assert self.offset_map[uvalue] >= 0
        return self.offset_map[uvalue]

    def unique_value(self, val):
        if val.type == FLOAT:
            if val.getfloat() == 0.0:
                return 0
            return float2longlong(val.getfloat())
        elif val.type == INT:
            return rffi.cast(lltype.Signed, val.getint())
        else:
            assert val.type == REF
            return rffi.cast(lltype.Signed, val.getref_base())

    def reserve_literal(self, size, box):
        uvalue = self.unique_value(box)
        if uvalue not in self.offset_map:
            self.offset_map[uvalue] = self.size
            self.allocate_slot(size)

    def reset(self):
        self.pool_start = 0
        self.label_offset = 0
        self.size = 0
        self.offset_map = {}
        self.constant_64_zeros = -1
        self.constant_64_ones = -1
        self.constant_64_sign_bit = -1
        self.constant_max_64_positive = -1

    def check_size(self, size=-1):
        if size == -1:
            size = self.size
        if size >= 2**19:
            msg = '[S390X/literalpool] size exceeded %d >= %d\n' % (size, 2**19)
            if we_are_translated():
                llop.debug_print(lltype.Void, msg)
            raise PoolOverflow(msg)

    def allocate_slot(self, size):
        val = self.size + size
        self.check_size(val)
        self.size = val

    def ensure_value(self, val):
        if val not in self.offset_map:
            self.offset_map[val] = self.size
            self.allocate_slot(8)
        return self.offset_map[val]

    def pre_assemble(self, asm, operations, bridge=False):
        # O(len(operations)). I do not think there is a way
        # around this.
        #
        # Problem:
        # constants such as floating point operations, plain pointers,
        # or integers might serve as parameter to an operation. thus
        # it must be loaded into a register. There is a space benefit
        # for 64-bit integers, or python floats, when a constant is used
        # twice.
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
        if self.constant_64_ones != -1:
            self.constant_64_ones = self.ensure_value(-1)
        if self.constant_64_zeros != -1:
            self.constant_64_zeros = self.ensure_value(0x0)
        if self.constant_64_sign_bit != -1:
            self.constant_64_sign_bit = self.ensure_value(-2**63) # == 0x8000000000000000
        if self.constant_max_64_positive != -1:
            self.constant_max_64_positive = self.ensure_value(0x7fffFFFFffffFFFF)
        asm.mc.write('\x00' * self.size)
        wrote = 0
        for val, offset in self.offset_map.items():
            self.overwrite_64(asm.mc, offset, val)
            wrote += 8

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
        for guard_token in pending_guard_tokens:
            descr = guard_token.faildescr
            offset = self.offset_descr[descr]
            assert isinstance(offset, int)
            assert offset >= 0
            assert guard_token._pool_offset != -1
            ptr = rffi.cast(lltype.Signed, guard_token.gcmap)
            self.overwrite_64(mc, offset + RECOVERY_GCMAP_POOL_OFFSET, ptr)
