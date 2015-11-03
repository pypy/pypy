from rpython.jit.backend.zarch import conditions as c
from rpython.jit.backend.zarch import registers as r
from rpython.jit.backend.zarch import locations as l
from rpython.jit.backend.zarch.instruction_builder import build_instr_codes
from rpython.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from rpython.jit.backend.llsupport.assembler import GuardToken
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.unroll import unrolling_iterable
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.tool.udir import udir
from rpython.jit.backend.detect_cpu import autodetect

clear_cache = rffi.llexternal(
    "__clear_cache",
    [llmemory.Address, llmemory.Address],
    lltype.Void,
    _nowrapper=True,
    sandboxsafe=True)

def binary_helper_call(name):
    function = getattr(support, 'arm_%s' % name)

    def f(self, c=c.AL):
        """Generates a call to a helper function, takes its
        arguments in r0 and r1, result is placed in r0"""
        addr = rffi.cast(lltype.Signed, function)
        self.BL(addr, c)
    return f

class ZARCHGuardToken(GuardToken):
    def __init__(self, cpu, gcmap, descr, failargs, faillocs,
                 guard_opnum, frame_depth, fcond=c.cond_none):
        GuardToken.__init__(self, cpu, gcmap, descr, failargs, faillocs,
                            guard_opnum, frame_depth)
        self.fcond = fcond
        self._pool_offset = -1

class AbstractZARCHBuilder(object):

    def write_i64(self, word):
        self.writechar(chr((word >> 56) & 0xFF))
        self.writechar(chr((word >> 48) & 0xFF))
        self.writechar(chr((word >> 40) & 0xFF))
        self.writechar(chr((word >> 32) & 0xFF))
        self.writechar(chr((word >> 24) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr(word & 0xFF))

    def write_i32(self, word):
        self.writechar(chr((word >> 24) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr(word & 0xFF))

    def write_i16(self, word):
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr(word & 0xFF))

    def write(self, bytestr):
        for char in bytestr:
            self.writechar(char)

build_instr_codes(AbstractZARCHBuilder)

class InstrBuilder(BlockBuilderMixin, AbstractZARCHBuilder):

    def __init__(self):
        AbstractZARCHBuilder.__init__(self)
        self.init_block_builder()
        #
        # ResOperation --> offset in the assembly.
        # ops_offset[None] represents the beginning of the code after the last op
        # (i.e., the tail of the loop)
        self.ops_offset = {}

    def mark_op(self, op):
        pos = self.get_relative_pos()
        self.ops_offset[op] = pos


    def _dump_trace(self, addr, name, formatter=-1):
        if not we_are_translated():
            if formatter != -1:
                name = name % formatter
            dir = udir.ensure('asm', dir=True)
            f = dir.join(name).open('wb')
            data = rffi.cast(rffi.CCHARP, addr)
            for i in range(self.currpos()):
                f.write(data[i])
            f.close()

    def clear_cache(self, addr):
        if we_are_translated():
            startaddr = rffi.cast(llmemory.Address, addr)
            endaddr = rffi.cast(llmemory.Address,
                            addr + self.get_relative_pos())
            clear_cache(startaddr, endaddr)

    def copy_to_raw_memory(self, addr):
        self._copy_to_raw_memory(addr)
        self.clear_cache(addr)
        self._dump(addr, "jit-backend-dump", "s390x")

    def load(self, treg, sreg, offset):
        self.LG(treg, l.addr(offset, sreg))

    def currpos(self):
        return self.get_relative_pos()

    def b_cond_offset(self, offset, condition):
        assert condition != c.cond_none
        # TODO ? BI, BO = c.encoding[condition]
        self.BRC(condition, l.imm(offset))

    def b_offset(self, reladdr):
        offset = reladdr - self.get_relative_pos()
        self.BRC(c.ANY, l.imm(offset))

    def b_abs(self, pooled, restore_pool=False):
        self.LG(r.r10, pooled)
        self.LG(r.POOL, l.pool(0))
        self.BCR(c.ANY, r.r10)

    def reserve_guard_branch(self):
        print "reserve!", self.get_relative_pos()
        self.BRC(l.imm(0x0), l.imm(0))

    def cmp_op(self, a, b, pool=False, imm=False, signed=True, fp=False):
        if fp == True:
            xxx
            self.fcmpu(a, b)
        else:
            if signed:
                if pool:
                    # 64 bit immediate signed
                    self.CLG(a, b)
                elif imm:
                    self.CGHI(a, b)
                else:
                    # 64 bit signed
                    self.CLGR(a, b)
            else:
                if pool:
                    # 64 bit immediate unsigned
                    self.CG(a, b)
                elif imm:
                    raise NotImplementedError
                else:
                    # 64 bit unsigned
                    self.CGR(a, b)


_classes = (AbstractZARCHBuilder,)

# Used to build the MachineCodeBlockWrapper
all_instructions = sorted([name for cls in _classes for name in cls.__dict__ \
                          if name.split('_')[0].isupper() and '_' in name])
