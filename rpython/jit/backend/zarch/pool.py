from rpython.jit.backend.zarch import registers as r
from rpython.jit.backend.zarch import locations as l
from rpython.jit.metainterp.history import (INT, REF, FLOAT,
        TargetToken)
from rpython.jit.metainterp.resoperation import rop
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.jit.backend.zarch.arch import (WORD,
        RECOVERY_GCMAP_POOL_OFFSET, RECOVERY_TARGET_POOL_OFFSET)

class LiteralPool(object):
    def __init__(self):
        self.size = 0
        # the offset to index the pool
        self.pool_start = 0
        self.label_offset = 0
        self.label_count = 0
        self.offset_map = {}

    def ensure_can_hold_constants(self, asm, op):
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
                descr._ll_loop_code = self.pool_start
                self.offset_map[descr] = self.size
        for arg in op.getarglist():
            if arg.is_constant():
                self.offset_map[arg] = self.size
                self.reserve_literal(8)

    def get_descr_offset(self, descr):
        return self.offset_map[descr]

    def reserve_literal(self, size):
        self.size += size
        print "resized to", self.size, "(+",size,")"

    def reset(self):
        self.pool_start = 0
        self.label_offset = 0
        self.size = 0
        self.offset_map.clear()

    def pre_assemble(self, asm, operations, bridge=True):
        self.reset()
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
        if bridge:
            self.reserve_literal(8)
        for op in operations:
            self.ensure_can_hold_constants(asm, op)
        if self.size == 0:
            # no pool needed!
            return
        self.size += 8
        assert self.size % 2 == 0
        #if self.size % 2 == 1:
        #    self.size += 1
        assert self.size < 2**16-1
        if bridge:
            asm.mc.LGR(r.SCRATCH, r.r13)
        asm.mc.BRAS(r.POOL, l.imm(self.size+asm.mc.BRAS_byte_count))
        self.pool_start = asm.mc.get_relative_pos()
        asm.mc.write('\xFF' * self.size)
        if bridge:
            asm.mc.STG(r.SCRATCH, l.pool(0))
        print "pool with %d quad words" % (self.size // 8)

    def overwrite_64(self, mc, index, value):
        index += self.pool_start
        print("value", hex(value), "at", index - self.pool_start)
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
            print val, offset
            if val.is_constant():
                if val.type == FLOAT:
                    self.overwrite_64(mc, offset, float2longlong(val.value))
                elif val.type == INT:
                    self.overwrite_64(mc, offset, val.value)
                else:
                    raise NotImplementedError
            else:
                pass

        for guard_token in pending_guard_tokens:
            descr = guard_token.faildescr
            offset = self.offset_map[descr]
            guard_token._pool_offset = offset
            ptr = rffi.cast(lltype.Signed, guard_token.gcmap)
            self.overwrite_64(mc, offset + RECOVERY_GCMAP_POOL_OFFSET, ptr)

