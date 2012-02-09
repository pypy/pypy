from pypy.rpython.lltypesystem import lltype, rffi
from pypy.objspace.flow.model import Constant
from pypy.translator.c.support import cdecl, c_string_constant
from pypy.translator.stm.llstm import size_of_voidp


def _stm_generic_get(funcgen, op, (expr_type, expr_ptr, expr_field)):
    T = funcgen.lltypemap(op.result)
    resulttypename = funcgen.db.gettype(T)
    cresulttypename = cdecl(resulttypename, '')
    newvalue = funcgen.expr(op.result, special_case_void=False)
    #
    assert T is not lltype.Void     # XXX
    fieldsize = rffi.sizeof(T)
    assert fieldsize in (1, 2, 4, 8)
    if T == lltype.Float:
        assert fieldsize == 8
        fieldsize = '8f'
    elif T == lltype.SingleFloat:
        assert fieldsize == 4
        fieldsize = '4f'
    if expr_type is not None:     # optimization for the common case
        return '%s = RPY_STM_FIELD(%s, %s, %s, %s, %s);' % (
            newvalue, cresulttypename, fieldsize,
            expr_type, expr_ptr, expr_field)
    else:
        return '%s = RPY_STM_ARRAY(%s, %s, %s, %s);' % (
            newvalue, cresulttypename, fieldsize,
            expr_ptr, expr_field)


def field_expr(funcgen, args):
    STRUCT = funcgen.lltypemap(args[0]).TO
    structdef = funcgen.db.gettypedefnode(STRUCT)
    fldname = structdef.c_struct_field_name(args[1].value)
    ptr = funcgen.expr(args[0])
    return ('%s %s' % (structdef.typetag, structdef.name), ptr, fldname)

def stm_getfield(funcgen, op):
    access_info = field_expr(funcgen, op.args)
    return _stm_generic_get(funcgen, op, access_info)

def array_expr(funcgen, args):
    ARRAY = funcgen.lltypemap(args[0]).TO
    ptr = funcgen.expr(args[0])
    index = funcgen.expr(args[1])
    arraydef = funcgen.db.gettypedefnode(ARRAY)
    return (None, ptr, arraydef.itemindex_access_expr(ptr, index))

def stm_getarrayitem(funcgen, op):
    access_info = array_expr(funcgen, op.args)
    return _stm_generic_get(funcgen, op, access_info)

def stm_getinteriorfield(funcgen, op):
    xxx
    expr = funcgen.interior_expr(op.args)
    return _stm_generic_get(funcgen, op, expr)


def stm_become_inevitable(funcgen, op):
    info = op.args[0].value
    string_literal = c_string_constant(info)
    return 'stm_try_inevitable(STM_EXPLAIN1(%s));' % (string_literal,)


def op_stm(funcgen, op):
    func = globals()[op.opname]
    return func(funcgen, op)
