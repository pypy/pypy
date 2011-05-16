from pypy.jit.metainterp.history import AbstractValue, ConstInt
from pypy.jit.backend.x86 import rx86
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.backend.x86.arch import WORD, IS_X86_32, IS_X86_64
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.objectmodel import specialize, instantiate
from pypy.rlib.rarithmetic import intmask
from pypy.jit.metainterp.history import FLOAT
from pypy.jit.codewriter import longlong

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

    def find_unused_reg(self): return eax

class StackLoc(AssemblerLocation):
    _immutable_ = True
    def __init__(self, position, ebp_offset, num_words, type):
        assert ebp_offset < 0   # so no confusion with RegLoc.value
        self.position = position
        self.value = ebp_offset
        self.width = num_words * WORD
        # One of INT, REF, FLOAT
        self.type = type

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

    def find_unused_reg(self):
        if self.value == eax.value:
            return edx
        else:
            return eax

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

    def __repr__(self):
        dict = {'j': 'value', 'a': 'loc_a', 'm': 'loc_m', 'a':'loc_a'}
        attr = dict.get(self._location_code, '?')
        info = getattr(self, attr, '?')
        return '<AddressLoc %r: %s>' % (self._location_code, info)

    def location_code(self):
        return self._location_code

    def value_a(self):
        return self.loc_a

    def value_m(self):
        return self.loc_m

    def find_unused_reg(self):
        if self._location_code == 'm':
            if self.loc_m[0] == eax.value:
                return edx
        elif self._location_code == 'a':
            if self.loc_a[0] == eax.value:
                if self.loc_a[1] == edx.value:
                    return ecx
                return edx
            if self.loc_a[1] == eax.value:
                if self.loc_a[0] == edx.value:
                    return ecx
                return edx
        return eax

    def add_offset(self, ofs):
        result = instantiate(AddressLoc)
        result._location_code = self._location_code
        if self._location_code == 'm':
            result.loc_m = (self.loc_m[0], self.loc_m[1] + ofs)
        elif self._location_code == 'a':
            result.loc_a = self.loc_a[:3] + (self.loc_a[3] + ofs,)
        elif self._location_code == 'j':
            result.value = self.value + ofs
        else:
            raise AssertionError(self._location_code)
        return result

class ConstFloatLoc(AssemblerLocation):
    # XXX: We have to use this class instead of just AddressLoc because
    # we want a width of 8  (... I think.  Check this!)
    _immutable_ = True
    width = 8

    def __init__(self, address):
        self.value = address

    def __repr__(self):
        return '<ConstFloatLoc @%s>' % (self.value,)

    def location_code(self):
        return 'j'

if IS_X86_32:
    class FloatImmedLoc(AssemblerLocation):
        # This stands for an immediate float.  It cannot be directly used in
        # any assembler instruction.  Instead, it is meant to be decomposed
        # in two 32-bit halves.  On 64-bit, FloatImmedLoc() is a function
        # instead; see below.
        _immutable_ = True
        width = 8

        def __init__(self, floatstorage):
            self.aslonglong = floatstorage

        def low_part(self):
            return intmask(self.aslonglong)

        def high_part(self):
            return intmask(self.aslonglong >> 32)

        def low_part_loc(self):
            return ImmedLoc(self.low_part())

        def high_part_loc(self):
            return ImmedLoc(self.high_part())

        def __repr__(self):
            floatvalue = longlong.getrealfloat(self.aslonglong)
            return '<FloatImmedLoc(%s)>' % (floatvalue,)

        def location_code(self):
            raise NotImplementedError

if IS_X86_64:
    def FloatImmedLoc(floatstorage):
        from pypy.rlib.longlong2float import float2longlong
        value = intmask(float2longlong(floatstorage))
        return ImmedLoc(value)


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

        def insn_with_64_bit_immediate(self, loc1, loc2):
            # These are the worst cases:
            val2 = loc2.value_i()
            code1 = loc1.location_code()
            if code1 == 'j':
                checkvalue = loc1.value_j()
            elif code1 == 'm':
                checkvalue = loc1.value_m()[1]
            elif code1 == 'a':
                checkvalue = loc1.value_a()[3]
            else:
                checkvalue = 0
            if not rx86.fits_in_32bits(checkvalue):
                # INSN_ji, and both operands are 64-bit; or INSN_mi or INSN_ai
                # and the constant offset in the address is 64-bit.
                # Hopefully this doesn't happen too often
                freereg = loc1.find_unused_reg()
                self.PUSH_r(freereg.value)
                self.MOV_ri(freereg.value, val2)
                INSN(self, loc1, freereg)
                self.POP_r(freereg.value)
            else:
                # For this case, we should not need the scratch register more than here.
                self._load_scratch(val2)
                INSN(self, loc1, X86_64_SCRATCH_REG)

        def invoke(self, codes, val1, val2):
            methname = name + "_" + codes
            _rx86_getattr(self, methname)(val1, val2)
        invoke._annspecialcase_ = 'specialize:arg(1)'

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

            for possible_code2 in unrolling_location_codes:
                if code2 == possible_code2:
                    val2 = getattr(loc2, "value_" + possible_code2)()
                    #
                    # Fake out certain operations for x86_64
                    if self.WORD == 8 and possible_code2 == 'i' and not rx86.fits_in_32bits(val2):
                        insn_with_64_bit_immediate(self, loc1, loc2)
                        return
                    #
                    # Regular case
                    for possible_code1 in unrolling_location_codes:
                        if code1 == possible_code1:
                            val1 = getattr(loc1, "value_" + possible_code1)()
                            # More faking out of certain operations for x86_64
                            if possible_code1 == 'j' and not rx86.fits_in_32bits(val1):
                                val1 = self._addr_as_reg_offset(val1)
                                invoke(self, "m" + possible_code2, val1, val2)
                            elif possible_code2 == 'j' and not rx86.fits_in_32bits(val2):
                                val2 = self._addr_as_reg_offset(val2)
                                invoke(self, possible_code1 + "m", val1, val2)
                            elif possible_code1 == 'm' and not rx86.fits_in_32bits(val1[1]):
                                val1 = self._fix_static_offset_64_m(val1)
                                invoke(self, "a" + possible_code2, val1, val2)
                            elif possible_code2 == 'm' and not rx86.fits_in_32bits(val2[1]):
                                val2 = self._fix_static_offset_64_m(val2)
                                invoke(self, possible_code1 + "a", val1, val2)
                            else:
                                if possible_code1 == 'a' and not rx86.fits_in_32bits(val1[3]):
                                    val1 = self._fix_static_offset_64_a(val1)
                                if possible_code2 == 'a' and not rx86.fits_in_32bits(val2[3]):
                                    val2 = self._fix_static_offset_64_a(val2)
                                invoke(self, possible_code1 + possible_code2, val1, val2)
                            return

        return func_with_new_name(INSN, "INSN_" + name)

    def _unaryop(name):
        def INSN(self, loc):
            code = loc.location_code()
            for possible_code in unrolling_location_codes:
                if code == possible_code:
                    val = getattr(loc, "value_" + possible_code)()
                    if self.WORD == 8 and possible_code == 'i' and not rx86.fits_in_32bits(val):
                        self._load_scratch(val)
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
                        if self.WORD == 4:
                            _rx86_getattr(self, name + "_l")(val)
                            self.add_pending_relocation()
                        else:
                            # xxx can we avoid "MOV r11, $val; JMP/CALL *r11"
                            # in case it would fit a 32-bit displacement?
                            # Hard, because we don't know yet where this insn
                            # will end up...
                            assert self.WORD == 8
                            self._load_scratch(val)
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

    def _fix_static_offset_64_m(self, (basereg, static_offset)):
        # For cases where an AddressLoc has the location_code 'm', but
        # where the static offset does not fit in 32-bits.  We have to fall
        # back to the X86_64_SCRATCH_REG.  Note that this returns a location
        # encoded as mode 'a'.  These are all possibly rare cases; don't try
        # to reuse a past value of the scratch register at all.
        self._scratch_register_known = False
        self.MOV_ri(X86_64_SCRATCH_REG.value, static_offset)
        return (basereg, X86_64_SCRATCH_REG.value, 0, 0)

    def _fix_static_offset_64_a(self, (basereg, scalereg,
                                       scale, static_offset)):
        # For cases where an AddressLoc has the location_code 'a', but
        # where the static offset does not fit in 32-bits.  We have to fall
        # back to the X86_64_SCRATCH_REG.  In one case it is even more
        # annoying.  These are all possibly rare cases; don't try to reuse a
        # past value of the scratch register at all.
        self._scratch_register_known = False
        self.MOV_ri(X86_64_SCRATCH_REG.value, static_offset)
        #
        if basereg != rx86.NO_BASE_REGISTER:
            self.LEA_ra(X86_64_SCRATCH_REG.value,
                        (basereg, X86_64_SCRATCH_REG.value, 0, 0))
        return (X86_64_SCRATCH_REG.value, scalereg, scale, 0)

    def _load_scratch(self, value):
        if (self._scratch_register_known
            and value == self._scratch_register_value):
            return
        if self._reuse_scratch_register:
            self._scratch_register_known = True
            self._scratch_register_value = value
        self.MOV_ri(X86_64_SCRATCH_REG.value, value)

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
    TEST8 = _binaryop('TEST8')

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
    MOVSX8 = _binaryop('MOVSX8')
    MOVZX16 = _binaryop('MOVZX16')
    MOVSX16 = _binaryop('MOVSX16')
    MOV32 = _binaryop('MOV32')
    MOVSX32 = _binaryop('MOVSX32')
    # Avoid XCHG because it always implies atomic semantics, which is
    # slower and does not pair well for dispatch.
    #XCHG = _binaryop('XCHG')

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
    
    SQRTSD = _binaryop('SQRTSD')

    ANDPD = _binaryop('ANDPD')
    XORPD = _binaryop('XORPD')

    PADDQ = _binaryop('PADDQ')
    PSUBQ = _binaryop('PSUBQ')
    PAND  = _binaryop('PAND')
    POR   = _binaryop('POR')
    PXOR  = _binaryop('PXOR')
    PCMPEQD = _binaryop('PCMPEQD')

    CALL = _relative_unaryop('CALL')
    JMP = _relative_unaryop('JMP')

def imm(x):
    # XXX: ri386 migration shim
    if isinstance(x, ConstInt):
        return ImmedLoc(x.getint())
    else:
        return ImmedLoc(x)

imm0 = imm(0)
imm1 = imm(1)

all_extra_instructions = [name for name in LocationCodeBuilder.__dict__
                          if name[0].isupper()]
all_extra_instructions.sort()
