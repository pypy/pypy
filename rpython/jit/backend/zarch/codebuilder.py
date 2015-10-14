from rpython.jit.backend.zarch import conditions as cond
from rpython.jit.backend.zarch import registers as reg
from rpython.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from rpython.rlib.objectmodel import we_are_translated
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

    def f(self, c=cond.AL):
        """Generates a call to a helper function, takes its
        arguments in r0 and r1, result is placed in r0"""
        addr = rffi.cast(lltype.Signed, function)
        self.BL(addr, c)
    return f


codes = {
    'ADD_rr': 0x1A,
}

def encode_rr(reg1, reg2):
    return chr(((reg2 & 0x0f) << 4) | (reg1 & 0xf))

class AbstractZARCHBuilder(object):
    def write32(self, word):
        self.writechar(chr(word & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 24) & 0xFF))

    def AR_rr(self, reg1, reg2):
        self.writechar(chr(0x1A))
        self.writechar(encode_rr(reg1, reg2))

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
        self._dump(addr, "jit-backend-dump", 'arm')

    def currpos(self):
        return self.get_relative_pos()

#define_instructions(AbstractARMBuilder)

_classes = (AbstractZARCHBuilder,)

# Used to build the MachineCodeBlockWrapper
all_instructions = sorted([name for cls in _classes for name in cls.__dict__ \
                          if name.split('_')[0].isupper()])
