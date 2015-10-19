from rpython.jit.backend.zarch import conditions as cond
from rpython.jit.backend.zarch import registers as reg
from rpython.jit.backend.zarch import locations as loc
from rpython.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.unroll import unrolling_iterable
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

class builder(object):
    """ NOT_RPYTHON """
    @staticmethod
    def arguments(args_str):
        """ NOT_RPYTHON """
        """
        Available names:
        r      - register
        r/m    - register or mask
        iX     - immediate X bits (signed)
        uX     - immediate X bits (unsigend)
        bd     - base displacement (12 bit)
        bdl    - base displacement long (20 bit)
        bid    - index base displacement
        bidl   - index base displacement (20 bit)
        l4bd   - length base displacement (4 bit)
        l8bd   - length base displacement (8 bit)

        note that a suffix 'l' means long, and a prefix length
        """
        def impl(func):
            func._arguments_ = args_str.split(',')
            return func
        return impl

BIT_MASK_4 =  0xF
BIT_MASK_12 = 0xFFF
BIT_MASK_16 = 0xFFFF
BIT_MASK_20 = 0xFFFFF
BIT_MASK_32 = 0xFFFFFFFF

@always_inline
def encode_base_displace(mc, base_displace):
    """
        +---------------------------------+
        | ... | base | length[0:11] | ... |
        +---------------------------------+
    """
    displace = base_displace.displace
    base = base_displace.base & 0xf
    byte = (displace >> 8 & 0xf) | base << 4
    mc.writechar(chr(byte))
    mc.writechar(chr(displace & 0xff))

@always_inline
def encode_base_displace_long(mc, basedisp):
    """
        +-------------------------------------------------+
        | ... | base | length[0:11] | length[12:20] | ... |
        +-------------------------------------------------+
    """
    displace = basedisp.displace & 0xfffff
    base = basedisp.base & 0xf
    byte = displace >> 8 & 0xf | base << 4
    mc.writechar(chr(byte))
    mc.writechar(chr(displace & 0xff))
    byte = displace >> 12 & 0xff
    mc.writechar(chr(byte))

def build_rr(mnemonic, (opcode,)):
    @builder.arguments('r,r')
    def encode_rr(self, reg1, reg2):
        self.writechar(opcode)
        operands = ((reg1 & 0x0f) << 4) | (reg2 & 0xf)
        self.writechar(chr(operands))
    return encode_rr

def build_rre(mnemonic, (opcode,)):
    opcode1,opcode2 = opcode
    @builder.arguments('r,r')
    def encode_rr(self, reg1, reg2):
        self.writechar(opcode1)
        self.writechar(opcode2)
        self.writechar('\x00')
        operands = ((reg1 & 0x0f) << 4) | (reg2 & 0xf)
        self.writechar(chr(operands))
    return encode_rr

def build_rx(mnemonic, (opcode,)):
    @builder.arguments('r/m,bid')
    def encode_rx(self, reg_or_mask, idxbasedisp):
        self.writechar(opcode)
        index = idxbasedisp.index
        byte = (reg_or_mask & 0x0f) << 4 | index & 0xf
        self.writechar(chr(byte))
        displace = idxbasedisp.displace & BIT_MASK_12
        base = idxbasedisp.base & 0xf
        byte = displace >> 8 & 0xf | base << 4
        self.writechar(chr(byte))
        self.writechar(chr(displace & 0xff))
    return encode_rx

def build_rxy(mnemonic, (opcode1,opcode2)):
    @builder.arguments('r/m,bidl')
    def encode_rxy(self, reg_or_mask, idxbasedisp):
        self.writechar(opcode1)
        index = idxbasedisp.index
        byte = (reg_or_mask & 0x0f) << 4 | index & 0xf
        self.writechar(chr(byte))
        encode_base_displace_long(self, idxbasedisp)
        self.writechar(opcode2)
    return encode_rxy

def build_ri(mnemonic, (opcode,halfopcode)):
    @builder.arguments('r/m,i16')
    def encode_ri(self, reg_or_mask, imm16):
        self.writechar(opcode)
        byte = (reg_or_mask & 0xf) << 4 | (ord(halfopcode) & 0xf)
        self.writechar(chr(byte))
        self.writechar(chr(imm16 >> 8 & 0xff))
        self.writechar(chr(imm16 & 0xff))
    return encode_ri

def build_ril(mnemonic, (opcode,halfopcode)):
    @builder.arguments('r/m,i32')
    def encode_ri(self, reg_or_mask, imm32):
        self.writechar(opcode)
        byte = (reg_or_mask & 0xf) << 4 | (ord(halfopcode) & 0xf)
        self.writechar(chr(byte))
        # half word boundary, addressing bytes
        self.write_i32(imm32 >> 1 & BIT_MASK_32)
    return encode_ri


def build_si(mnemonic, (opcode,)):
    @builder.arguments('bd,u8')
    def encode_si(self, base_displace, uimm8):
        self.writechar(opcode)
        self.writechar(chr(uimm8))
        encode_base_displace(self, base_displace)
    return encode_si

def build_siy(mnemonic, (opcode1,opcode2)):
    @builder.arguments('bd,u8')
    def encode_siy(self, base_displace, uimm8):
        self.writechar(opcode1)
        self.writechar(chr(uimm8))
        encode_base_displace(self, base_displace)
        displace = base_displace.displace
        self.writechar(chr(displace >> 12 & 0xff))
        self.writechar(opcode2)
    return encode_siy

def build_ssa(mnemonic, (opcode1,)):
    @builder.arguments('l8bd,bd')
    def encode_ssa(self, len_base_disp, base_displace):
        self.writechar(opcode1)
        self.writechar(chr(len_base_disp.length & 0xff))
        encode_base_displace(self, len_base_disp)
        encode_base_displace(self, base_displace)
    return encode_ssa

def build_ssb(mnemonic, (opcode1,)):
    @builder.arguments('l8bd,l8bd')
    def encode_ssb(self, len_base_disp1, len_base_disp2):
        self.writechar(opcode1)
        byte = (len_base_disp1.length & 0xf) << 4 | len_base_disp2.length & 0xf
        self.writechar(chr(byte))
        encode_base_displace(self, len_base_disp1)
        encode_base_displace(self, len_base_disp2)
    return encode_ssb

def build_ssc(mnemonic, (opcode1,)):
    @builder.arguments('l4bd,bd,u4')
    def encode_ssc(self, len_base_disp, base_disp, uimm4):
        self.writechar(opcode1)
        byte = (len_base_disp.length & 0xf) << 4 | uimm4 & 0xf
        self.writechar(chr(byte))
        encode_base_displace(self, len_base_disp)
        encode_base_displace(self, base_disp)
    return encode_ssc

def build_ssd(mnemonic, (opcode,)):
    @builder.arguments('bid,bd,r')
    def encode_ssd(self, index_base_disp, base_disp, reg):
        self.writechar(opcode)
        byte = (index_base_disp.index & 0xf) << 4 | reg & 0xf
        self.writechar(chr(byte))
        encode_base_displace(self, index_base_disp)
        encode_base_displace(self, base_disp)
    return encode_ssd

def build_sse(mnemonic, (opcode,)):
    @builder.arguments('r,r,bd,bd')
    def encode_sse(self, reg1, reg3, base_disp2, base_disp4):
        self.writechar(opcode)
        byte = (reg1 & BIT_MASK_4) << 4 | reg3 & BIT_MASK_4
        self.writechar(chr(byte))
        encode_base_displace(self, base_disp2)
        encode_base_displace(self, base_disp4)
    return encode_sse

def build_ssf(mnemonic, (opcode,)):
    @builder.arguments('bd,l8bd')
    def encode_ssf(self, base_disp, len_base_disp):
        self.writechar(opcode)
        self.writechar(chr(len_base_disp.length & 0xff))
        encode_base_displace(self, base_disp)
        encode_base_displace(self, len_base_disp)
    return encode_ssf

def build_rs(mnemonic, (opcode,)):
    @builder.arguments('r,r,bd')
    def encode_rs(self, reg1, reg3, base_displace):
        self.writechar(opcode)
        self.writechar(chr((reg1 & BIT_MASK_4) << 4 | reg3 & BIT_MASK_4))
        encode_base_displace(self, base_displace)
    return encode_rs

def build_rsy(mnemonic, (opcode1,opcode2)):
    @builder.arguments('r,r,bdl')
    def encode_ssa(self, reg1, reg3, base_displace):
        self.writechar(opcode1)
        self.writechar(chr((reg1 & BIT_MASK_4) << 4 | reg3 & BIT_MASK_4))
        encode_base_displace_long(self, base_displace)
        self.writechar(opcode2)
    return encode_ssa

def build_rsi(mnemonic, (opcode,)):
    @builder.arguments('r,r,i16')
    def encode_ri(self, reg1, reg2, imm16):
        self.writechar(opcode)
        byte = (reg1 & BIT_MASK_4) << 4 | (reg2 & BIT_MASK_4)
        self.writechar(chr(byte))
        self.write_i16(imm16 >> 1 & BIT_MASK_16)
    return encode_ri

def build_rie(mnemonic, (opcode1,opcode2)):
    @builder.arguments('r,r,i16')
    def encode_ri(self, reg1, reg2, imm16):
        self.writechar(opcode1)
        byte = (reg1 & BIT_MASK_4) << 4 | (reg2 & BIT_MASK_4)
        self.writechar(chr(byte))
        self.write_i16(imm16 >> 1 & BIT_MASK_16)
        self.writechar(chr(0x0))
        self.writechar(opcode2)
    return encode_ri

_mnemonic_codes = {
    'AR':      (build_rr,    ['\x1A']),
    'AGR':     (build_rre,   ['\xB9\x08']),
    'AGFR':    (build_rre,   ['\xB9\x18']),
    'A':       (build_rx,    ['\x5A']),
    'AY':      (build_rxy,   ['\xE3','\x5A']),
    'AG':      (build_rxy,   ['\xE3','\x08']),
    'AGF':     (build_rxy,   ['\xE3','\x18']),
    'AHI':     (build_ri,    ['\xA7','\x0A']),
    #
    'BRASL':   (build_ril,   ['\xC0','\x05']),
    'BXH':     (build_rs,    ['\x86']),
    'BXHG':    (build_rsy,   ['\xEB','\x44']),
    'BRXH':    (build_rsi,   ['\x84']),
    'BRXLG':   (build_rie,   ['\xEC','\x45']),
    'BCR':     (build_rr,    ['\x07']),
    #
    'NI':      (build_si,    ['\x94']),
    'NIY':     (build_siy,   ['\xEB','\x54']),
    'NC':      (build_ssa,   ['\xD4']),
    'AP':      (build_ssb,   ['\xFA']),
    'SRP':     (build_ssc,   ['\xF0']),
    'MVCK':    (build_ssd,   ['\xD9']),

    'LAY':     (build_rxy,   ['\xE3','\x71']),
    'LMD':     (build_sse,   ['\xEF']),
    'LMG':     (build_rsy,   ['\xEB','\x04']),
    'LGHI':    (build_ri,    ['\xA7','\x09']),

    'PKA':     (build_ssf,   ['\xE9']),
    'STMG':    (build_rsy,   ['\xEB','\x24']),
}

def build_unpack_func(mnemonic, func):
    def function(self, *args):
        newargs = [None] * len(args)
        for i,arg in enumerate(unrolling_iterable(func._arguments_)):
            if arg == 'r' or arg == 'r/m':
                newargs[i] = args[i].value
            elif arg.startswith('i') or arg.startswith('u'):
                newargs[i] = args[i].value
            else:
                newargs[i] = args[i]
        return func(self, *newargs)
    function.__name__ = mnemonic
    return function

def build_instr_codes(clazz):
    for mnemonic, (builder, args) in _mnemonic_codes.items():
        func = builder(mnemonic, args)
        instrtype = builder.__name__.split("_")[1]
        name = mnemonic + "_" + instrtype
        setattr(clazz, name, func)
        setattr(clazz, mnemonic, build_unpack_func(mnemonic, func))

class AbstractZARCHBuilder(object):
    def write_i32(self, word):
        self.writechar(chr((word >> 24) & 0xFF))
        self.writechar(chr((word >> 16) & 0xFF))
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr(word & 0xFF))

    def write_i16(self, word):
        self.writechar(chr((word >> 8) & 0xFF))
        self.writechar(chr(word & 0xFF))

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

_classes = (AbstractZARCHBuilder,)

# Used to build the MachineCodeBlockWrapper
all_instructions = sorted([name for cls in _classes for name in cls.__dict__ \
                          if name.split('_')[0].isupper()])
