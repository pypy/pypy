from rpython.jit.backend.zarch import conditions as cond
from rpython.jit.backend.zarch import registers as reg
from rpython.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from rpython.rlib.objectmodel import we_are_translated
from rpython.rtyper.lltypesystem import lltype, rffi, llmemory
from rpython.tool.udir import udir
from rpython.jit.backend.detect_cpu import autodetect
from rpython.rtyper.lltypesystem.rbuilder import always_inline

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

class Operand(object):
    pass

@always_inline
def encode_base_displace(mc, base_displace):
    displace = base_displace.displace # & 0x3ff
    base = base_displace.base & 0xf
    byte = (displace >> 8 & 0xf) | base << 4
    mc.writechar(chr(byte))
    mc.writechar(chr(displace & 0xff))

def build_rr(mnemonic, (opcode,)):
    def encode_rr(self, reg1, reg2):
        self.writechar(opcode)
        operands = ((reg1 & 0x0f) << 4) | (reg2 & 0xf)
        self.writechar(chr(operands))
    return encode_rr

def build_rre(mnemonic, (opcode,)):
    opcode1,opcode2 = opcode
    def encode_rr(self, reg1, reg2):
        self.writechar(opcode1)
        self.writechar(opcode2)
        self.writechar('\x00')
        operands = ((reg1 & 0x0f) << 4) | (reg2 & 0xf)
        self.writechar(chr(operands))
    return encode_rr

def build_rx(mnemonic, (opcode,)):
    def encode_rx(self, reg_or_mask, idxbasedisp):
        self.writechar(opcode)
        index = idxbasedisp.index
        byte = (reg_or_mask & 0x0f) << 4 | index & 0xf
        self.writechar(chr(byte))
        displace = idxbasedisp.displace & 0x3ff
        base = idxbasedisp.base & 0xf
        byte = displace >> 8 & 0xf | base << 4
        self.writechar(chr(byte))
        self.writechar(chr(displace & 0xff))
    return encode_rx

def build_rxy(mnemonic, (opcode1,opcode2)):
    def encode_rxy(self, reg_or_mask, idxbasedisp):
        self.writechar(opcode1)
        index = idxbasedisp.index
        byte = (reg_or_mask & 0x0f) << 4 | index & 0xf
        self.writechar(chr(byte))
        displace = idxbasedisp.displace & 0x3ff
        base = idxbasedisp.base & 0xf
        byte = displace >> 8 & 0xf | base << 4
        self.writechar(chr(byte))
        self.writechar(chr(displace & 0xff))
        self.writechar(chr(displace >> 12 & 0xff))
        self.writechar(opcode2)
    return encode_rxy

def build_ri(mnemonic, (opcode,halfopcode)):
    def encode_ri(self, reg_or_mask, imm16):
        self.writechar(opcode)
        byte = (reg_or_mask & 0xf) << 4 | (ord(halfopcode) & 0xf)
        self.writechar(chr(byte))
        self.writechar(chr(imm16 >> 8 & 0xff))
        self.writechar(chr(imm16 & 0xff))
    return encode_ri

def build_si(mnemonic, (opcode,)):
    def encode_si(self, base_displace, uimm8):
        self.writechar(opcode)
        self.writechar(chr(uimm8))
        encode_base_displace(self, base_displace)
    return encode_si

_mnemonic_codes = {
    'AR':      (build_rr,    ['\x1A']),
    'AGR':     (build_rre,   ['\xB9\x08']),
    'AGFR':    (build_rre,   ['\xB9\x18']),
    'A':       (build_rx,    ['\x5A']),
    'AY':      (build_rxy,   ['\xE3','\x5A']),
    'AG':      (build_rxy,   ['\xE3','\x08']),
    'AGF':     (build_rxy,   ['\xE3','\x18']),
    'AHI':     (build_ri,    ['\xA7','\x0A']),
    'NI':      (build_si,    ['\x94']),
}

def build_instr_codes(clazz):

    for mnemonic, (builder, args) in _mnemonic_codes.items():
        func = builder(mnemonic, args)
        name = mnemonic + "_" + builder.__name__.split("_")[1]
        setattr(clazz, name, func)

class AbstractZARCHBuilder(object):
    def write32(self, word):
        self.writechar(chr(word & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 24) & 0xFF))

    def AR_rr(self, reg1, reg2):
        self.writechar(chr(0x1A))
        self.writechar(encode_rr(reg1, reg2))

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
        self._dump(addr, "jit-backend-dump", 'arm')

    def currpos(self):
        return self.get_relative_pos()

#define_instructions(AbstractARMBuilder)

_classes = (AbstractZARCHBuilder,)

# Used to build the MachineCodeBlockWrapper
all_instructions = sorted([name for cls in _classes for name in cls.__dict__ \
                          if name.split('_')[0].isupper()])
