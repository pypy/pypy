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
            op = erase_int(value)
        elif lltype.typeOf(value) == lltype.Signed:
            op = erase_int(value)
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
            op = IntFrontendOp(pos)
            op.setint(int(value))
            op = erase_box(op)
        elif lltype.typeOf(value) == lltype.Signed:
            op = IntFrontendOp(pos)
            op.setint(value)
            op = erase_box(op)
        elif lltype.typeOf(value) is longlong.FLOATSTORAGE:
            op = FloatFrontendOp(pos)
            op.setfloatstorage(value)
            op = erase_box(op)
        else:
            op = RefFrontendOp(pos)
            assert lltype.typeOf(value) == llmemory.GCREF
            op.setref_base(value)
            op = erase_box(op)
        return op

    def is_constant(self, box_or_const):
        if is_integer(box_or_const):
            return True

        unerased = unerase_box(box_or_const)
        return unerased.is_constant()
    
    @always_inline
    def get_value_int_and_constness(self, box_or_const):
        if is_integer(box_or_const):
            return unerase_int(box_or_const), True
        
        unerased = unerase_box(box_or_const)
        assert isinstance(unerased, IntFrontendOp)
        return unerased.getint(), False

    def get_value_int(self, box_or_const):
        if is_integer(box_or_const):
            return unerase_int(box_or_const)
        
        unerased = unerase_box(box_or_const)
        assert isinstance(unerased, IntFrontendOp)
        return unerased.getint()
        
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

    def get_position(self, box_or_const):
        unerased = unerase_box(box_or_const)
        return unerased.get_position()
        
    def set_position(self, box_or_const, pos):
        unerased = unerase_box(box_or_const)
        return unerased.set_position(pos)
    
    def get_opencoder_index(self, box_or_const):
        unerased = unerase_box(box_or_const)
        assert isinstance(unerased, ConstPtrJitCode)
        return unerased.opencoder_index
    
    def set_opencoder_index(self, box_or_const, index):
        unerased = unerase_box(box_or_const)
        assert isinstance(unerased, ConstPtrJitCode)
        unerased.opencoder_index = index


valueapi = ValueAPI()