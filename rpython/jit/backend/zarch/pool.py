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
        # for constant offsets
        self.offset_map = {}
        # for descriptors
        self.offset_descr = {}

    def reset(self):
        self.pool_start = 0
        self.size = 0
        self.offset_map = {}
        self.offset_descr = {}

    def ensure_can_hold_constants(self, asm, op):
        # allocates 8 bytes in memory for pointers, long integers or floats
        if op.is_jit_debug():
            return

        for arg in op.getarglist():
            if arg.is_constant():
                self.reserve_literal(8, arg, asm)

    def contains_constant(self, unique_val):
        return unique_val in self.offset_map

    def get_descr_offset(self, descr):
        return self.offset_descr[descr]

    def contains_box(self, box):
        uvalue = self.unique_value(box)
        return self.contains_constant(uvalue)

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

    def reserve_literal(self, size, box, asm):
        uvalue = self.unique_value(box)
        if box.type == INT and -2**31 <= uvalue <= 2**31-1:
            # we do not allocate non 64 bit values, these
            # can be loaded as imm by LGHI/LGFI
            return
        #
        self._ensure_value(uvalue, asm)

    def check_size(self, size=-1):
        if size == -1:
            size = self.size
        if size >= 2**19:
            msg = '[S390X/literalpool] size exceeded %d >= %d\n' % (size, 2**19)
            if we_are_translated():
                llop.debug_print(lltype.Void, msg)
            raise PoolOverflow(msg)

    def _ensure_value(self, uvalue, asm):
        if uvalue not in self.offset_map:
            self.offset_map[uvalue] = self.size
            self.allocate_slot(8)
            asm.mc.write_i64(uvalue)
        return self.offset_map[uvalue]

    def allocate_slot(self, size):
        val = self.size + size
        self.check_size(val)
        self.size = val
        assert val >= 0

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
        self._ensure_value(asm.cpu.pos_exc_value(), asm)
        # the top of shadow stack
        gcrootmap = asm.cpu.gc_ll_descr.gcrootmap
        if gcrootmap and gcrootmap.is_shadow_stack:
            self._ensure_value(gcrootmap.get_root_stack_top_addr(), asm)
        # endaddr of insert stack check
        endaddr, lengthaddr, _ = self.cpu.insert_stack_check()
        self._ensure_value(endaddr, asm)
        # fast gil
        fastgil = rgil.gil_fetch_fastgil()
        self._ensure_value(fastgil, asm)
        # TODO add more values that are loaded with load_imm

    # XXX def post_assemble(self, asm):
    # XXX     mc = asm.mc
    # XXX     pending_guard_tokens = asm.pending_guard_tokens
    # XXX     if self.size == 0:
    # XXX         return
    # XXX     for guard_token in pending_guard_tokens:
    # XXX         descr = guard_token.faildescr
    # XXX         offset = self.offset_descr[descr]
    # XXX         assert isinstance(offset, int)
    # XXX         assert offset >= 0
    # XXX         assert guard_token._pool_offset != -1
    # XXX         ptr = rffi.cast(lltype.Signed, guard_token.gcmap)
    # XXX         self._overwrite_64(mc, offset + RECOVERY_GCMAP_POOL_OFFSET, ptr)

    def _overwrite_64(self, mc, index, value):
        index += self.pool_start

        mc.overwrite(index,   chr(value >> 56 & 0xff))
        mc.overwrite(index+1, chr(value >> 48 & 0xff))
        mc.overwrite(index+2, chr(value >> 40 & 0xff))
        mc.overwrite(index+3, chr(value >> 32 & 0xff))
        mc.overwrite(index+4, chr(value >> 24 & 0xff))
        mc.overwrite(index+5, chr(value >> 16 & 0xff))
        mc.overwrite(index+6, chr(value >> 8 & 0xff))
        mc.overwrite(index+7, chr(value & 0xff))
