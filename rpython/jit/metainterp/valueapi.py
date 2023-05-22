from rpython.jit.metainterp.history import FloatFrontendOp, FrontendOp, IntFrontendOp, RefFrontendOp
from rpython.jit.metainterp.history import ConstFloat, ConstPtrJitCode, ConstInt, IntFrontendOp, Const
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.jit.codewriter import longlong


TYPE_INT = "INT"
TYPE_FLOAT = "FLOAT"
TYPE_REF = "REF"


class ValueAPI:
    def create_const(self, value):
        if value is None:
            op = Const()
        elif isinstance(value, bool):
            op = ConstInt(value)
        elif lltype.typeOf(value) == lltype.Signed:
            op = ConstInt(value)
        elif lltype.typeOf(value) is longlong.FLOATSTORAGE:
            op = ConstFloat(value)
        else:
            op = ConstPtrJitCode(value)
        return op

    def create_box(self, pos, value):
        if value is None:
            op = FrontendOp(pos)
        elif isinstance(value, bool):
            op = IntFrontendOp(pos)
            op.setint(int(value))
        elif lltype.typeOf(value) == lltype.Signed:
            op = IntFrontendOp(pos)
            op.setint(value)
        elif lltype.typeOf(value) is longlong.FLOATSTORAGE:
            op = FloatFrontendOp(pos)
            op.setfloatstorage(value)
        else:
            op = RefFrontendOp(pos)
            assert lltype.typeOf(value) == llmemory.GCREF
            op.setref_base(value)
        return op

    def is_constant(self, box_or_const):
        return (isinstance(box_or_const, Const)
            or isinstance(box_or_const, ConstInt)
            or isinstance(box_or_const, ConstFloat)
            or isinstance(box_or_const, ConstPtrJitCode))

    def get_value(self, box_or_const):
        if isinstance(box_or_const, ConstInt) or isinstance(box_or_const, IntFrontendOp):
            return box_or_const.getint()
        elif isinstance(box_or_const, ConstFloat) or isinstance(box_or_const, FloatFrontendOp):
            return box_or_const.getfloat()
        elif isinstance(box_or_const, ConstPtrJitCode) or isinstance(box_or_const, RefFrontendOp):
            return box_or_const.getref_base()
        else:
            return None

    def get_type(self, box_or_const):
        if isinstance(box_or_const, ConstInt) or isinstance(box_or_const, IntFrontendOp):
            return TYPE_INT
        elif isinstance(box_or_const, ConstFloat) or isinstance(box_or_const, FloatFrontendOp):
            return TYPE_FLOAT
        elif isinstance(box_or_const, ConstPtrJitCode) or isinstance(box_or_const, RefFrontendOp):
            return TYPE_REF
        else:
            return None

    def get_position(self, box_or_const):
        if isinstance(box_or_const, FrontendOp):
            return box_or_const.get_position()
        elif isinstance(box_or_const, IntFrontendOp):
            return box_or_const.get_position()
        elif isinstance(box_or_const, FloatFrontendOp):
            return box_or_const.get_position()
        elif isinstance(box_or_const, RefFrontendOp):
            return box_or_const.get_position()
        else:
            return None


valueapi = ValueAPI()