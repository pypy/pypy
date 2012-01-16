from pypy.rpython.lltypesystem import lltype, rffi
from pypy.objspace.flow.model import Constant
from pypy.translator.c.support import cdecl, c_string_constant
from pypy.translator.stm.llstm import size_of_voidp


def _stm_generic_get(funcgen, op, expr, simple_struct=False):
    T = funcgen.lltypemap(op.result)
    resulttypename = funcgen.db.gettype(T)
    cresulttypename = cdecl(resulttypename, '')
    newvalue = funcgen.expr(op.result, special_case_void=False)
    #
    assert T is not lltype.Void     # XXX
    fieldsize = rffi.sizeof(T)
    if fieldsize >= size_of_voidp or T == lltype.SingleFloat:
        assert 1      # xxx assert somehow that the field is aligned
        if T == lltype.Float:
            funcname = 'stm_read_double'
        elif T == lltype.SingleFloat:
            funcname = 'stm_read_float'
        elif fieldsize == size_of_voidp:
            funcname = 'stm_read_word'
        elif fieldsize == 8:    # 32-bit only: read a 64-bit field
            funcname = 'stm_read_doubleword'
        else:
            raise NotImplementedError(fieldsize)
        return '%s = (%s)%s((long*)&%s);' % (
            newvalue, cresulttypename, funcname, expr)
    else:
        if simple_struct:
            # assume that the object is aligned, and any possible misalignment
            # comes from the field offset, so that it can be resolved at
            # compile-time (by using C macros)
            STRUCT = funcgen.lltypemap(op.args[0]).TO
            structdef = funcgen.db.gettypedefnode(STRUCT)
            basename = funcgen.expr(op.args[0])
            fieldname = op.args[1].value
            return '%s = STM_read_partial_word(%s, %s, offsetof(%s, %s));' % (
                newvalue, cresulttypename, basename,
                cdecl(funcgen.db.gettype(STRUCT), ''),
                structdef.c_struct_field_name(fieldname))
        #
        else:
            return '%s = stm_read_partial_word(sizeof(%s), &%s);' % (
                newvalue, cresulttypename, expr)

def _stm_generic_set(funcgen, op, targetexpr, T):
    basename = funcgen.expr(op.args[0])
    newvalue = funcgen.expr(op.args[-1], special_case_void=False)
    #
    assert T is not lltype.Void     # XXX
    fieldsize = rffi.sizeof(T)
    if fieldsize >= size_of_voidp or T == lltype.SingleFloat:
        assert 1      # xxx assert somehow that the field is aligned
        if T == lltype.Float:
            funcname = 'stm_write_double'
            newtype = 'double'
        elif T == lltype.SingleFloat:
            funcname = 'stm_write_float'
            newtype = 'float'
        elif fieldsize == size_of_voidp:
            funcname = 'stm_write_word'
            newtype = 'long'
        elif fieldsize == 8:    # 32-bit only: read a 64-bit field
            funcname = 'stm_write_doubleword'
            newtype = 'long long'
        else:
            raise NotImplementedError(fieldsize)
        return '%s((long*)&%s, (%s)%s);' % (
            funcname, targetexpr, newtype, newvalue)
    else:
        itemtypename = funcgen.db.gettype(T)
        citemtypename = cdecl(itemtypename, '')
        return ('stm_write_partial_word(sizeof(%s), &%s, %s);' % (
            citemtypename, targetexpr, newvalue))


def field_expr(funcgen, args):
    STRUCT = funcgen.lltypemap(args[0]).TO
    structdef = funcgen.db.gettypedefnode(STRUCT)
    baseexpr_is_const = isinstance(args[0], Constant)
    return structdef.ptr_access_expr(funcgen.expr(args[0]),
                                     args[1].value,
                                     baseexpr_is_const)

def stm_getfield(funcgen, op):
    expr = field_expr(funcgen, op.args)
    return _stm_generic_get(funcgen, op, expr, simple_struct=True)

def stm_setfield(funcgen, op):
    expr = field_expr(funcgen, op.args)
    T = op.args[2].concretetype
    return _stm_generic_set(funcgen, op, expr, T)

def array_expr(funcgen, args):
    ARRAY = funcgen.lltypemap(args[0]).TO
    ptr = funcgen.expr(args[0])
    index = funcgen.expr(args[1])
    arraydef = funcgen.db.gettypedefnode(ARRAY)
    return arraydef.itemindex_access_expr(ptr, index)

def stm_getarrayitem(funcgen, op):
    expr = array_expr(funcgen, op.args)
    return _stm_generic_get(funcgen, op, expr)

def stm_setarrayitem(funcgen, op):
    expr = array_expr(funcgen, op.args)
    T = op.args[2].concretetype
    return _stm_generic_set(funcgen, op, expr, T)

def stm_getinteriorfield(funcgen, op):
    expr = funcgen.interior_expr(op.args)
    return _stm_generic_get(funcgen, op, expr)

def stm_setinteriorfield(funcgen, op):
    expr = funcgen.interior_expr(op.args[:-1])
    T = op.args[-1].concretetype
    return _stm_generic_set(funcgen, op, expr, T)


def stm_become_inevitable(funcgen, op):
    info = op.args[0].value
    string_literal = c_string_constant(info)
    return 'stm_try_inevitable(STM_EXPLAIN1(%s));' % (string_literal,)


def op_stm(funcgen, op):
    func = globals()[op.opname]
    return func(funcgen, op)
