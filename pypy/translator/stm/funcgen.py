from pypy.translator.c.support import c_string_constant


def stm_barrier(funcgen, op):
    level = op.args[0].value
    assert type(level) is str
    arg = funcgen.expr(op.args[1])
    result = funcgen.expr(op.result)
    return '%s = STM_BARRIER_%s(%s);' % (result, level, arg)

def stm_ptr_eq(funcgen, op):
    arg0 = funcgen.expr(op.args[0])
    arg1 = funcgen.expr(op.args[1])
    result = funcgen.expr(op.result)
    return '%s = STM_PTR_EQ(%s, %s);' % (result, arg0, arg1)

def stm_become_inevitable(funcgen, op):
    try:
        info = op.args[0].value
    except IndexError:
        info = "rstm.become_inevitable"    # cannot insert it in 'llop'
    string_literal = c_string_constant(info)
    return 'stm_try_inevitable(%s);' % (string_literal,)

def stm_jit_invoke_code(funcgen, op):
    XXX
    return funcgen.OP_DIRECT_CALL(op)


def op_stm(funcgen, op):
    func = globals()[op.opname]
    return func(funcgen, op)
