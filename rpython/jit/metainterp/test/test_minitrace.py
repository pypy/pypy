from rpython.jit.metainterp.minitrace import *

def test_int_add():
    history = History(2)
    metainterp = MetaInterp(history)
    miframe = MIFrame(metainterp)
    metainterp.framestack.append(miframe)

    i1 = miframe.registers_i[0] = IntFrontendOp(0, 15)
    i2 = miframe.registers_i[1] = IntFrontendOp(1, 7)

    r1 = miframe.opimpl_int_add(0, 1, 2)
    r2 = miframe.opimpl_int_add(1, 2, 3)

    assert r1 is miframe.registers_i[2]
    assert r2 is miframe.registers_i[3]

    assert r1.getint() == 22
    assert metainterp.history.trace == [(rop.INT_ADD, [i1, i2], None), (rop.INT_ADD, [i2, r1], None)]

def test_int_add_const():
    history = History(0)
    metainterp = MetaInterp(history)
    miframe = MIFrame(metainterp)
    metainterp.framestack.append(miframe)

    miframe.registers_i[0] = ConstInt(15)
    miframe.registers_i[1] = ConstInt(7)

    r1 = miframe.opimpl_int_add(0, 1, 2)

    assert r1 is miframe.registers_i[2]
    assert r1.getint() == 22
    assert r1.is_constant()
    assert metainterp.history.trace == []

def test_simulate_call():
    history = History(2)
    metainterp = MetaInterp(history)
    miframe = MIFrame(metainterp)
    metainterp.framestack.append(miframe)

    # setup inputs 0, 1
    i1 = miframe.registers_i[0] = IntFrontendOp(0, 15)
    i2 = miframe.registers_i[1] = IntFrontendOp(1, 7)

    # add 0, 1 = 2
    r1 = miframe.opimpl_int_add(0, 1, 2)

    # call function with args 2, 0 (function adds args)
    miframe2 = MIFrame(metainterp)
    metainterp.framestack.append(miframe2)
    miframe2.registers_i[0] = miframe.registers_i[2]
    miframe2.registers_i[1] = miframe.registers_i[0]
    r2 = miframe2.opimpl_int_add(0, 1, 2)

    # register 3 contains result
    miframe.registers_i[3] = miframe2.registers_i[2]

    # add 2 and 3 = 4
    r4 = miframe.opimpl_int_add(2, 3, 4)

    assert r4.getint() == 59
    assert not r4.is_constant()
    assert metainterp.history.trace == [(rop.INT_ADD, [i1, i2], None), (rop.INT_ADD, [r1, i1], None), (rop.INT_ADD, [r1, r2], None)]
