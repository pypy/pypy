from pypy.rpython.lltypesystem import lltype, rffi
from pypy.objspace.flow.model import Constant
from pypy.translator.c.support import cdecl
from pypy.translator.stm.rstm import size_of_voidp


def stm_getfield(funcgen, op):
    STRUCT = funcgen.lltypemap(op.args[0]).TO
    structdef = funcgen.db.gettypedefnode(STRUCT)
    baseexpr_is_const = isinstance(op.args[0], Constant)
    basename = funcgen.expr(op.args[0])
    fieldname = op.args[1].value
    T = funcgen.lltypemap(op.result)
    fieldtypename = funcgen.db.gettype(T)
    cfieldtypename = cdecl(fieldtypename, '')
    newvalue = funcgen.expr(op.result, special_case_void=False)
    #
    assert T is not lltype.Void     # XXX
    fieldsize = rffi.sizeof(T)
    if fieldsize >= size_of_voidp:
        assert 1      # xxx assert somehow that the field is aligned
        assert fieldsize == size_of_voidp     # XXX
        expr = structdef.ptr_access_expr(basename,
                                         fieldname,
                                         baseexpr_is_const)
        return '%s = (%s)stm_read_word((long*)&%s);' % (
            newvalue, cfieldtypename, expr)
    else:
        # assume that the object is aligned, and any possible misalignment
        # comes from the field offset, so that it can be resolved at
        # compile-time (by using C macros)
        return '%s = stm_read_partial_word(%s, %s, offsetof(%s, %s));' % (
            newvalue, cfieldtypename, basename,
            cdecl(funcgen.db.gettype(STRUCT), ''),
            structdef.c_struct_field_name(fieldname))

def stm_setfield(funcgen, op):
    STRUCT = funcgen.lltypemap(op.args[0]).TO
    structdef = funcgen.db.gettypedefnode(STRUCT)
    baseexpr_is_const = isinstance(op.args[0], Constant)
    basename = funcgen.expr(op.args[0])
    fieldname = op.args[1].value
    T = funcgen.lltypemap(op.args[2])
    fieldtypename = funcgen.db.gettype(T)
    newvalue = funcgen.expr(op.args[2], special_case_void=False)
    #
    assert T is not lltype.Void     # XXX
    fieldsize = rffi.sizeof(T)
    if fieldsize >= size_of_voidp:
        assert 1      # xxx assert somehow that the field is aligned
        assert fieldsize == size_of_voidp     # XXX
        expr = structdef.ptr_access_expr(basename,
                                         fieldname,
                                         baseexpr_is_const)
        return 'stm_write_word((long*)&%s, (long)%s);' % (
            expr, newvalue)
    else:
        cfieldtypename = cdecl(fieldtypename, '')
        return ('stm_write_partial_word(sizeof(%s), (char*)%s, '
                'offsetof(%s, %s), (long)%s);' % (
            cfieldtypename, basename,
            cdecl(funcgen.db.gettype(STRUCT), ''),
            structdef.c_struct_field_name(fieldname), newvalue))


def op_stm(funcgen, op):
    func = globals()[op.opname]
    return func(funcgen, op)
