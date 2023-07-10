from rpython.jit.metainterp.history import ConstPtr, FloatFrontendOp, FrontendOp, IntFrontendOp, RefFrontendOp
from rpython.jit.metainterp.history import ConstFloat, ConstPtrJitCode, ConstInt, IntFrontendOp, Const
from rpython.rlib.rerased import Erased, erase_int, is_integer, new_erasing_pair, unerase_int
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.jit.codewriter import longlong
from rpython.rlib.objectmodel import specialize, always_inline

TYPE_VOID = "v"
TYPE_INT = "i"
TYPE_FLOAT = "f"
TYPE_REF = "r"

erase_box, unerase_box = new_erasing_pair("box")

CONST_FLAG = 0x100000000
MAX_INT = 0x7FFFFFFF
MAX_POS = 0xFFF
MASK_INT = 0xFFFFFFFF

# encoding for tagged pointer ints (before erase_int shift):
# in the constant case:
# |    63-33    |       32      | 31-0  |
# |   reserved  | constness (1) | value |
# in the non constant case:
# |    63-45    | 44-33 |       32      |  31-0  |
# |   reserved  |  pos  | constness (0) |  value |

def is_constant(v):
    return v & CONST_FLAG == CONST_FLAG

def is_positive(v):
    return (v >> 31) & 1 == 0

def encode_const_int(i):
    assert -MAX_INT - 1 <= i < MAX_INT
    return CONST_FLAG | (i & MASK_INT)

def decode_const_int(i):
    assert is_constant(i)
    if is_positive(i):
        return i & MAX_INT
    # value was negative, set all the top bits so it becomes negative again
    return i | (~MASK_INT)

def encode_int(pos, i):
    assert 0 <= pos <= MAX_POS
    assert -MAX_INT - 1 <= i < MAX_INT
    return (pos << 33) | (i & MASK_INT)

def decode_int(i):
    assert not is_constant(i)
    if is_positive(i):
        return (i >> 33) & MAX_POS, i & MAX_INT
    # salue was negative, set all the top bits so it becomes negative again
    return (i >> 33) & MAX_POS, i | (~MASK_INT)

class ValueAPI:
    NoValue = erase_box(None)
    CONST_FALSE = erase_int(0)
    CONST_TRUE = erase_int(1)
    CONST_NULL = erase_box(ConstPtr(ConstPtr.value))
    CONST_FZERO = erase_box(ConstFloat(longlong.ZEROF))

    @specialize.argtype(1)
    def create_const(self, value):
        if value is None:
            op = Const()
            op = erase_box(op)
        elif isinstance(value, bool):
            op = erase_int(encode_const_int(int(value)))
        elif lltype.typeOf(value) == lltype.Signed:
            op = erase_int(encode_const_int(value))
        elif lltype.typeOf(value) is longlong.FLOATSTORAGE:
            op = ConstFloat(value)
            op = erase_box(op)
        else:
            op = ConstPtrJitCode(value)
            op = erase_box(op)
        return op

    @specialize.argtype(2)
    def create_box(self, pos, value):
        if value is None:
            op = FrontendOp(pos)
            op = erase_box(op)
        elif isinstance(value, bool):
            op = erase_int(encode_int(pos, int(value)))
        elif lltype.typeOf(value) == lltype.Signed:
            op = erase_int(encode_int(pos, value))
        elif lltype.typeOf(value) is longlong.FLOATSTORAGE:
            op = FloatFrontendOp(pos, value)
            op = erase_box(op)
        else:
            assert lltype.typeOf(value) == llmemory.GCREF
            op = RefFrontendOp(pos, value)
            op = erase_box(op)
        return op

    def is_constant(self, box_or_const):
        if is_integer(box_or_const):
            return is_constant(unerase_int(box_or_const))

        unerased = unerase_box(box_or_const)
        return unerased.is_constant()
    
    @always_inline
    def get_value_int_and_constness(self, box_or_const):
        if is_integer(box_or_const):
            value = unerase_int(box_or_const)
            if is_constant(value):
                return decode_const_int(value), True
            else:
                _, i = decode_int(value)
                return i, False
        assert False # unreachable

    def get_value_int(self, box_or_const):
        if is_integer(box_or_const):
            value = unerase_int(box_or_const)
            if is_constant(value):
                return decode_const_int(value)
            else:
                _, i = decode_int(value)
                return i
        assert False # unreachable
        
    def get_value_float(self, box_or_const):
        unerased = unerase_box(box_or_const)
        assert isinstance(unerased, ConstFloat) or isinstance(unerased, FloatFrontendOp)
        return unerased.getfloat()
    
    def get_value_floatstorage(self, box_or_const):
        unerased = unerase_box(box_or_const)
        assert isinstance(unerased, ConstFloat) or isinstance(unerased, FloatFrontendOp)
        return unerased.getfloatstorage()
        
    def get_value_ref(self, box_or_const):
        unerased = unerase_box(box_or_const)
        assert isinstance(unerased, ConstPtrJitCode) or isinstance(unerased, RefFrontendOp)
        return unerased.getref_base()

    def get_type(self, box_or_const):
        if is_integer(box_or_const):
            return TYPE_INT

        unerased = unerase_box(box_or_const)
        return unerased.type

    def get_position(self, box):
        if is_integer(box):
            value = unerase_int(box)
            assert not is_constant(value)
            pos, _ = decode_int(value)
            return pos

        unerased = unerase_box(box)
        assert not unerased.is_constant()
        return unerased.get_position()
    
    def get_opencoder_index(self, box_or_const):
        unerased = unerase_box(box_or_const)
        assert isinstance(unerased, ConstPtrJitCode)
        return unerased.opencoder_index
    
    def set_opencoder_index(self, box_or_const, index):
        unerased = unerase_box(box_or_const)
        assert isinstance(unerased, ConstPtrJitCode)
        unerased.opencoder_index = index


valueapi = ValueAPI()
