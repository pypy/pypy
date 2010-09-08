from pypy.jit.metainterp.history import AbstractValue, ConstInt
from pypy.jit.backend.x86 import rx86
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.backend.x86.arch import WORD, IS_X86_32, IS_X86_64
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import intmask
from pypy.jit.metainterp.history import FLOAT

#
# This module adds support for "locations", which can be either in a Const,
# or a RegLoc or a StackLoc.  It also adds operations like mc.ADD(), which
# take two locations as arguments, decode them, and calls the right
# mc.ADD_rr()/ADD_rb()/ADD_ri().
#

class AssemblerLocation(object):
    # XXX: Is adding "width" here correct?
    __slots__ = ('value', 'width')
    _immutable_ = True
    def _getregkey(self):
        return self.value

    def is_memory_reference(self):
        return self.location_code() in ('b', 's', 'j', 'a', 'm')

    def value_r(self): return self.value
    def value_b(self): return self.value
    def value_s(self): return self.value
    def value_j(self): return self.value
    def value_i(self): return self.value
    def value_x(self): return self.value
    def value_a(self): raise AssertionError("value_a undefined")
    def value_m(self): raise AssertionError("value_m undefined")

class StackLoc(AssemblerLocation):
    _immutable_ = True
    def __init__(self, position, ebp_offset, num_words, type):
        assert ebp_offset < 0   # so no confusion with RegLoc.value
        self.position = position
        self.value = ebp_offset
        self.width = num_words * WORD
        # One of INT, REF, FLOAT
        self.type = type

    def frame_size(self):
        return self.width // WORD

    def __repr__(self):
        return '%d(%%ebp)' % (self.value,)

    def location_code(self):
        return 'b'

    def assembler(self):
        return repr(self)

class RegLoc(AssemblerLocation):
    _immutable_ = True
    def __init__(self, regnum, is_xmm):
        assert regnum >= 0
        self.value = regnum
        self.is_xmm = is_xmm
        if self.is_xmm:
            self.width = 8
        else:
            self.width = WORD
    def __repr__(self):
        if self.is_xmm:
            return rx86.R.xmmnames[self.value]
        else:
            return rx86.R.names[self.value]

    def lowest8bits(self):
        assert not self.is_xmm
        return RegLoc(rx86.low_byte(self.value), False)

    def higher8bits(self):
        assert not self.is_xmm
        return RegLoc(rx86.high_byte(self.value), False)

    def location_code(self):
        if self.is_xmm:
            return 'x'
        else:
            return 'r'

    def assembler(self):
        return '%' + repr(self)

class ImmedLoc(AssemblerLocation):
    _immutable_ = True
    width = WORD
    def __init__(self, value):
        from pypy.rpython.lltypesystem import rffi, lltype
        # force as a real int
        self.value = rffi.cast(lltype.Signed, value)

    def location_code(self):
        return 'i'

    def getint(self):
        return self.value

    def __repr__(self):
        return "ImmedLoc(%d)" % (self.value)

    def lowest8bits(self):
        val = self.value & 0xFF
        if val > 0x7F:
            val -= 0x100
        return ImmedLoc(val)

class AddressLoc(AssemblerLocation):
    _immutable_ = True

    width = WORD
    # The address is base_loc + (scaled_loc << scale) + static_offset
    def __init__(self, base_loc, scaled_loc, scale=0, static_offset=0):
        assert 0 <= scale < 4
        assert isinstance(base_loc, ImmedLoc) or isinstance(base_loc, RegLoc)
        assert isinstance(scaled_loc, ImmedLoc) or isinstance(scaled_loc, RegLoc)

        if isinstance(base_loc, ImmedLoc):
            if isinstance(scaled_loc, ImmedLoc):
                self._location_code = 'j'
                self.value = base_loc.value + (scaled_loc.value << scale) + static_offset
            else:
                self._location_code = 'a'
                self.loc_a = (rx86.NO_BASE_REGISTER, scaled_loc.value, scale, base_loc.value + static_offset)
        else:
            if isinstance(scaled_loc, ImmedLoc):
                # FIXME: What if base_loc is ebp or esp?
                self._location_code = 'm'
                self.loc_m = (base_loc.value, (scaled_loc.value << scale) + static_offset)
            else:
                self._location_code = 'a'
                self.loc_a = (base_loc.value, scaled_loc.value, scale, static_offset)

    def location_code(self):
        return self._location_code

    def value_a(self):
        return self.loc_a

    def value_m(self):
        return self.loc_m

class ConstFloatLoc(AssemblerLocation):
    # XXX: We have to use this class instead of just AddressLoc because
    # AddressLoc is "untyped" and also we to have need some sort of unique
    # identifier that we can use in _getregkey (for jump.py)

    _immutable_ = True

    width = 8

    def __init__(self, address, const_id):
        self.value = address
        self.const_id = const_id

    def _getregkey(self):
        # XXX: 1000 is kind of magic: We just don't want to be confused
        # with any registers
        return 1000 + self.const_id

    def location_code(self):
        return 'j'

REGLOCS = [RegLoc(i, is_xmm=False) for i in range(16)]
XMMREGLOCS = [RegLoc(i, is_xmm=True) for i in range(16)]
eax, ecx, edx, ebx, esp, ebp, esi, edi, r8, r9, r10, r11, r12, r13, r14, r15 = REGLOCS
xmm0, xmm1, xmm2, xmm3, xmm4, xmm5, xmm6, xmm7, xmm8, xmm9, xmm10, xmm11, xmm12, xmm13, xmm14, xmm15 = XMMREGLOCS

# We use a scratch register to simulate having 64-bit immediates. When we
# want to do something like:
#     mov rax, [0xDEADBEEFDEADBEEF]
# we actually do:
#     mov r11, 0xDEADBEEFDEADBEEF
#     mov rax, [r11]
# 
# NB: You can use the scratch register as a temporary register in
# assembler.py, but care must be taken when doing so. A call to a method in
# LocationCodeBuilder could clobber the scratch register when certain
# location types are passed in.
X86_64_SCRATCH_REG = r11

# XXX: a GPR scratch register is definitely needed, but we could probably do
# without an xmm scratch reg.
X86_64_XMM_SCRATCH_REG = xmm15

unrolling_location_codes = unrolling_iterable(list("rbsmajix"))

@specialize.arg(1)
def _rx86_getattr(obj, methname):
    if hasattr(rx86.AbstractX86CodeBuilder, methname):
        return getattr(obj, methname)
    else:
        raise AssertionError(methname + " undefined")

class LocationCodeBuilder(object):
    _mixin_ = True

    _reuse_scratch_register = False
    _scratch_register_known = False
    _scratch_register_value = 0

    def _binaryop(name):
        def INSN(self, loc1, loc2):
            code1 = loc1.location_code()
            code2 = loc2.location_code()

            # You can pass in the scratch register as a location, but you
            # must be careful not to combine it with location types that
            # might need to use the scratch register themselves.
            if loc2 is X86_64_SCRATCH_REG:
                assert code1 != 'j'
            if loc1 is X86_64_SCRATCH_REG and not name.startswith("MOV"):
                assert code2 not in ('j', 'i')

            for possible_code1 in unrolling_location_codes:
                if code1 == possible_code1:
                    for possible_code2 in unrolling_location_codes:
                        if code2 == possible_code2:
                            val1 = getattr(loc1, "value_" + possible_code1)()
                            val2 = getattr(loc2, "value_" + possible_code2)()
                            # Fake out certain operations for x86_64
                            if self.WORD == 8 and possible_code2 == 'i' and not rx86.fits_in_32bits(val2):
                                if possible_code1 == 'j':
                                    # This is the worst case: INSN_ji, and both operands are 64-bit
                                    # Hopefully this doesn't happen too often
                                    self.PUSH_r(eax.value)
                                    self.MOV_ri(eax.value, val1)
                                    self.MOV_ri(X86_64_SCRATCH_REG.value, val2)
                                    methname = name + "_mr"
                                    _rx86_getattr(self, methname)((eax.value, 0), X86_64_SCRATCH_REG.value)
                                    self.POP_r(eax.value)
                                else:
                                    self.MOV_ri(X86_64_SCRATCH_REG.value, val2)
                                    methname = name + "_" + possible_code1 + "r"
                                    _rx86_getattr(self, methname)(val1, X86_64_SCRATCH_REG.value)
                            elif self.WORD == 8 and possible_code1 == 'j':
                                reg_offset = self._addr_as_reg_offset(val1)
                                methname = name + "_" + "m" + possible_code2
                                _rx86_getattr(self, methname)(reg_offset, val2)
                            elif self.WORD == 8 and possible_code2 == 'j':
                                reg_offset = self._addr_as_reg_offset(val2)
                                methname = name + "_" + possible_code1 + "m"
                                _rx86_getattr(self, methname)(val1, reg_offset)
                            else:
                                methname = name + "_" + possible_code1 + possible_code2
                                _rx86_getattr(self, methname)(val1, val2)

        return func_with_new_name(INSN, "INSN_" + name)

    def _unaryop(name):
        def INSN(self, loc):
            code = loc.location_code()
            for possible_code in unrolling_location_codes:
                if code == possible_code:
                    val = getattr(loc, "value_" + possible_code)()
                    if self.WORD == 8 and possible_code == 'i' and not rx86.fits_in_32bits(val):
                        self.MOV_ri(X86_64_SCRATCH_REG.value, val)
                        _rx86_getattr(self, name + "_r")(X86_64_SCRATCH_REG.value)
                    else:
                        methname = name + "_" + possible_code
                        _rx86_getattr(self, methname)(val)

        return func_with_new_name(INSN, "INSN_" + name)

    def _relative_unaryop(name):
        def INSN(self, loc):
            code = loc.location_code()
            for possible_code in unrolling_location_codes:
                if code == possible_code:
                    val = getattr(loc, "value_" + possible_code)()
                    if possible_code == 'i':
                        offset = intmask(val - (self.tell() + 5))
                        if rx86.fits_in_32bits(offset):
                            _rx86_getattr(self, name + "_l")(val)
                        else:
                            assert self.WORD == 8
                            self.MOV_ri(X86_64_SCRATCH_REG.value, val)
                            _rx86_getattr(self, name + "_r")(X86_64_SCRATCH_REG.value)
                    else:
                        methname = name + "_" + possible_code
                        _rx86_getattr(self, methname)(val)

        return func_with_new_name(INSN, "INSN_" + name)

    def _16_bit_binaryop(name):
        def INSN(self, loc1, loc2):
            # Select 16-bit operand mode
            self.writechar('\x66')
            # XXX: Hack to let immediate() in rx86 know to do a 16-bit encoding
            self._use_16_bit_immediate = True
            getattr(self, name)(loc1, loc2)
            self._use_16_bit_immediate = False

        return INSN

    def _addr_as_reg_offset(self, addr):
        # Encodes a (64-bit) address as an offset from the scratch register.
        # If we are within a "reuse_scratch_register" block, we remember the
        # last value we loaded to the scratch register and encode the address
        # as an offset from that if we can
        if self._scratch_register_known:
            offset = addr - self._scratch_register_value
            if rx86.fits_in_32bits(offset):
                return (X86_64_SCRATCH_REG.value, offset)
            # else: fall through

        if self._reuse_scratch_register:
            self._scratch_register_known = True
            self._scratch_register_value = addr

        self.MOV_ri(X86_64_SCRATCH_REG.value, addr)
        return (X86_64_SCRATCH_REG.value, 0)

    def begin_reuse_scratch_register(self):
        # Flag the beginning of a block where it is okay to reuse the value
        # of the scratch register. In theory we shouldn't have to do this if
        # we were careful to mark all possible targets of a jump or call, and
        # "forget" the value of the scratch register at those positions, but
        # for now this seems safer.
        self._reuse_scratch_register = True

    def end_reuse_scratch_register(self):
        self._reuse_scratch_register = False
        self._scratch_register_known = False

    AND = _binaryop('AND')
    OR  = _binaryop('OR')
    XOR = _binaryop('XOR')
    NOT = _unaryop('NOT')
    SHL = _binaryop('SHL')
    SHR = _binaryop('SHR')
    SAR = _binaryop('SAR')
    TEST = _binaryop('TEST')

    ADD = _binaryop('ADD')
    SUB = _binaryop('SUB')
    IMUL = _binaryop('IMUL')
    NEG = _unaryop('NEG')

    CMP = _binaryop('CMP')
    CMP16 = _16_bit_binaryop('CMP')
    MOV = _binaryop('MOV')
    MOV8 = _binaryop('MOV8')
    MOV16 = _16_bit_binaryop('MOV')
    MOVZX8 = _binaryop('MOVZX8')
    MOVZX16 = _binaryop('MOVZX16')
    MOV32 = _binaryop('MOV32')
    XCHG = _binaryop('XCHG')

    PUSH = _unaryop('PUSH')
    POP = _unaryop('POP')

    LEA = _binaryop('LEA')

    MOVSD = _binaryop('MOVSD')
    ADDSD = _binaryop('ADDSD')
    SUBSD = _binaryop('SUBSD')
    MULSD = _binaryop('MULSD')
    DIVSD = _binaryop('DIVSD')
    UCOMISD = _binaryop('UCOMISD')
    CVTSI2SD = _binaryop('CVTSI2SD')
    CVTTSD2SI = _binaryop('CVTTSD2SI')

    ANDPD = _binaryop('ANDPD')
    XORPD = _binaryop('XORPD')

    CALL = _relative_unaryop('CALL')
    JMP = _relative_unaryop('JMP')

def imm(x):
    # XXX: ri386 migration shim
    if isinstance(x, ConstInt):
        return ImmedLoc(x.getint())
    else:
        return ImmedLoc(x)

all_extra_instructions = [name for name in LocationCodeBuilder.__dict__
                          if name[0].isupper()]
all_extra_instructions.sort()
