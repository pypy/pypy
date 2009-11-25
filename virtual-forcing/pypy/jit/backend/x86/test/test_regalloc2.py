import py
from pypy.jit.metainterp.history import ResOperation, BoxInt, ConstInt,\
     BoxPtr, ConstPtr, BasicFailDescr, LoopToken
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.backend.x86.runner import CPU

def test_bug_rshift():
    v1 = BoxInt()
    v2 = BoxInt()
    v3 = BoxInt()
    v4 = BoxInt()
    inputargs = [v1]
    operations = [
        ResOperation(rop.INT_ADD, [v1, v1], v2),
        ResOperation(rop.INT_INVERT, [v2], v3),
        ResOperation(rop.UINT_RSHIFT, [v1, ConstInt(3)], v4),
        ResOperation(rop.FINISH, [v4, v3], None, descr=BasicFailDescr()),
        ]
    cpu = CPU(None, None)
    looptoken = LoopToken()
    cpu.compile_loop(inputargs, operations, looptoken)
    cpu.set_future_value_int(0, 9)
    cpu.execute_token(looptoken)
    assert cpu.get_latest_value_int(0) == (9 >> 3)
    assert cpu.get_latest_value_int(1) == (~18)

def test_bug_int_is_true_1():
    v1 = BoxInt()
    v2 = BoxInt()
    v3 = BoxInt()
    v4 = BoxInt()
    tmp5 = BoxInt()
    inputargs = [v1]
    operations = [
        ResOperation(rop.INT_MUL, [v1, v1], v2),
        ResOperation(rop.INT_MUL, [v2, v1], v3),
        ResOperation(rop.INT_IS_TRUE, [v2], tmp5),
        ResOperation(rop.BOOL_NOT, [tmp5], v4),
        ResOperation(rop.FINISH, [v4, v3, tmp5], None, descr=BasicFailDescr()),
            ]
    cpu = CPU(None, None)
    looptoken = LoopToken()
    cpu.compile_loop(inputargs, operations, looptoken)
    cpu.set_future_value_int(0, -10)
    cpu.execute_token(looptoken)
    assert cpu.get_latest_value_int(0) == 0
    assert cpu.get_latest_value_int(1) == -1000
    assert cpu.get_latest_value_int(2) == 1

def test_bug_0():
    v1 = BoxInt()
    v2 = BoxInt()
    v3 = BoxInt()
    v4 = BoxInt()
    v5 = BoxInt()
    v6 = BoxInt()
    v7 = BoxInt()
    v8 = BoxInt()
    v9 = BoxInt()
    v10 = BoxInt()
    v11 = BoxInt()
    v12 = BoxInt()
    v13 = BoxInt()
    v14 = BoxInt()
    v15 = BoxInt()
    v16 = BoxInt()
    v17 = BoxInt()
    v18 = BoxInt()
    v19 = BoxInt()
    v20 = BoxInt()
    v21 = BoxInt()
    v22 = BoxInt()
    v23 = BoxInt()
    v24 = BoxInt()
    v25 = BoxInt()
    v26 = BoxInt()
    v27 = BoxInt()
    v28 = BoxInt()
    v29 = BoxInt()
    v30 = BoxInt()
    v31 = BoxInt()
    v32 = BoxInt()
    v33 = BoxInt()
    v34 = BoxInt()
    v35 = BoxInt()
    v36 = BoxInt()
    v37 = BoxInt()
    v38 = BoxInt()
    v39 = BoxInt()
    v40 = BoxInt()
    tmp41 = BoxInt()
    tmp42 = BoxInt()
    tmp43 = BoxInt()
    tmp44 = BoxInt()
    tmp45 = BoxInt()
    tmp46 = BoxInt()
    inputargs = [v1, v2, v3, v4, v5, v6, v7, v8, v9, v10]
    operations = [
        ResOperation(rop.UINT_GT, [v3, ConstInt(-48)], v11),
        ResOperation(rop.INT_XOR, [v8, v1], v12),
        ResOperation(rop.INT_GT, [v6, ConstInt(-9)], v13),
        ResOperation(rop.INT_LE, [v13, v2], v14),
        ResOperation(rop.INT_LE, [v11, v5], v15),
        ResOperation(rop.UINT_GE, [v13, v13], v16),
        ResOperation(rop.INT_OR, [v9, ConstInt(-23)], v17),
        ResOperation(rop.INT_LT, [v10, v13], v18),
        ResOperation(rop.INT_OR, [v15, v5], v19),
        ResOperation(rop.INT_XOR, [v17, ConstInt(54)], v20),
        ResOperation(rop.INT_MUL, [v8, v10], v21),
        ResOperation(rop.INT_OR, [v3, v9], v22),
        ResOperation(rop.INT_AND, [v11, ConstInt(-4)], tmp41),
        ResOperation(rop.INT_OR, [tmp41, ConstInt(1)], tmp42),
        ResOperation(rop.INT_MOD, [v12, tmp42], v23),
        ResOperation(rop.INT_IS_TRUE, [v6], v24),
        ResOperation(rop.UINT_RSHIFT, [v15, ConstInt(6)], v25),
        ResOperation(rop.INT_OR, [ConstInt(-4), v25], v26),
        ResOperation(rop.INT_INVERT, [v8], v27),
        ResOperation(rop.INT_SUB, [ConstInt(-113), v11], v28),
        ResOperation(rop.INT_NEG, [v7], v29),
        ResOperation(rop.INT_NEG, [v24], v30),
        ResOperation(rop.INT_FLOORDIV, [v3, ConstInt(53)], v31),
        ResOperation(rop.INT_MUL, [v28, v27], v32),
        ResOperation(rop.INT_AND, [v18, ConstInt(-4)], tmp43),
        ResOperation(rop.INT_OR, [tmp43, ConstInt(1)], tmp44),
        ResOperation(rop.INT_MOD, [v26, tmp44], v33),
        ResOperation(rop.INT_OR, [v27, v19], v34),
        ResOperation(rop.UINT_LT, [v13, ConstInt(1)], v35),
        ResOperation(rop.INT_AND, [v21, ConstInt(31)], tmp45),
        ResOperation(rop.INT_RSHIFT, [v21, tmp45], v36),
        ResOperation(rop.INT_AND, [v20, ConstInt(31)], tmp46),
        ResOperation(rop.UINT_RSHIFT, [v4, tmp46], v37),
        ResOperation(rop.UINT_GT, [v33, ConstInt(-11)], v38),
        ResOperation(rop.INT_NEG, [v7], v39),
        ResOperation(rop.INT_GT, [v24, v32], v40),
        ResOperation(rop.FINISH, [v40, v36, v37, v31, v16, v34, v35, v23, v22, v29, v14, v39, v30, v38], None, descr=BasicFailDescr()),
            ]
    cpu = CPU(None, None)
    looptoken = LoopToken()
    cpu.compile_loop(inputargs, operations, looptoken)
    cpu.set_future_value_int(0, -13)
    cpu.set_future_value_int(1, 10)
    cpu.set_future_value_int(2, 10)
    cpu.set_future_value_int(3, 8)
    cpu.set_future_value_int(4, -8)
    cpu.set_future_value_int(5, -16)
    cpu.set_future_value_int(6, -18)
    cpu.set_future_value_int(7, 46)
    cpu.set_future_value_int(8, -12)
    cpu.set_future_value_int(9, 26)
    cpu.execute_token(looptoken)
    assert cpu.get_latest_value_int(0) == 0
    assert cpu.get_latest_value_int(1) == 0
    assert cpu.get_latest_value_int(2) == 0
    assert cpu.get_latest_value_int(3) == 0
    assert cpu.get_latest_value_int(4) == 1
    assert cpu.get_latest_value_int(5) == -7
    assert cpu.get_latest_value_int(6) == 1
    assert cpu.get_latest_value_int(7) == 0
    assert cpu.get_latest_value_int(8) == -2
    assert cpu.get_latest_value_int(9) == 18
    assert cpu.get_latest_value_int(10) == 1
    assert cpu.get_latest_value_int(11) == 18
    assert cpu.get_latest_value_int(12) == -1
    assert cpu.get_latest_value_int(13) == 0

def test_bug_1():
    v1 = BoxInt()
    v2 = BoxInt()
    v3 = BoxInt()
    v4 = BoxInt()
    v5 = BoxInt()
    v6 = BoxInt()
    v7 = BoxInt()
    v8 = BoxInt()
    v9 = BoxInt()
    v10 = BoxInt()
    v11 = BoxInt()
    v12 = BoxInt()
    v13 = BoxInt()
    v14 = BoxInt()
    v15 = BoxInt()
    v16 = BoxInt()
    v17 = BoxInt()
    v18 = BoxInt()
    v19 = BoxInt()
    v20 = BoxInt()
    v21 = BoxInt()
    v22 = BoxInt()
    v23 = BoxInt()
    v24 = BoxInt()
    v25 = BoxInt()
    v26 = BoxInt()
    v27 = BoxInt()
    v28 = BoxInt()
    v29 = BoxInt()
    v30 = BoxInt()
    v31 = BoxInt()
    v32 = BoxInt()
    v33 = BoxInt()
    v34 = BoxInt()
    v35 = BoxInt()
    v36 = BoxInt()
    v37 = BoxInt()
    v38 = BoxInt()
    v39 = BoxInt()
    v40 = BoxInt()
    tmp41 = BoxInt()
    tmp42 = BoxInt()
    tmp43 = BoxInt()
    tmp44 = BoxInt()
    tmp45 = BoxInt()
    inputargs = [v1, v2, v3, v4, v5, v6, v7, v8, v9, v10]
    operations = [
        ResOperation(rop.UINT_LT, [v6, ConstInt(0)], v11),
        ResOperation(rop.INT_AND, [v3, ConstInt(31)], tmp41),
        ResOperation(rop.INT_RSHIFT, [v3, tmp41], v12),
        ResOperation(rop.INT_NEG, [v2], v13),
        ResOperation(rop.INT_ADD, [v11, v7], v14),
        ResOperation(rop.INT_OR, [v3, v2], v15),
        ResOperation(rop.INT_OR, [v12, v12], v16),
        ResOperation(rop.INT_NE, [v2, v5], v17),
        ResOperation(rop.INT_AND, [v5, ConstInt(31)], tmp42),
        ResOperation(rop.UINT_RSHIFT, [v14, tmp42], v18),
        ResOperation(rop.INT_AND, [v14, ConstInt(31)], tmp43),
        ResOperation(rop.INT_LSHIFT, [ConstInt(7), tmp43], v19),
        ResOperation(rop.INT_NEG, [v19], v20),
        ResOperation(rop.INT_MOD, [v3, ConstInt(1)], v21),
        ResOperation(rop.UINT_GE, [v15, v1], v22),
        ResOperation(rop.INT_AND, [v16, ConstInt(31)], tmp44),
        ResOperation(rop.INT_LSHIFT, [v8, tmp44], v23),
        ResOperation(rop.INT_IS_TRUE, [v17], v24),
        ResOperation(rop.INT_AND, [v5, ConstInt(31)], tmp45),
        ResOperation(rop.INT_LSHIFT, [v14, tmp45], v25),
        ResOperation(rop.INT_LSHIFT, [v5, ConstInt(17)], v26),
        ResOperation(rop.INT_EQ, [v9, v15], v27),
        ResOperation(rop.INT_GE, [ConstInt(0), v6], v28),
        ResOperation(rop.INT_NEG, [v15], v29),
        ResOperation(rop.INT_NEG, [v22], v30),
        ResOperation(rop.INT_ADD, [v7, v16], v31),
        ResOperation(rop.UINT_LT, [v19, v19], v32),
        ResOperation(rop.INT_ADD, [v2, ConstInt(1)], v33),
        ResOperation(rop.INT_NEG, [v5], v34),
        ResOperation(rop.INT_ADD, [v17, v24], v35),
        ResOperation(rop.UINT_LT, [ConstInt(2), v16], v36),
        ResOperation(rop.INT_NEG, [v9], v37),
        ResOperation(rop.INT_GT, [v4, v11], v38),
        ResOperation(rop.INT_LT, [v27, v22], v39),
        ResOperation(rop.INT_NEG, [v27], v40),
        ResOperation(rop.FINISH, [v40, v10, v36, v26, v13, v30, v21, v33, v18, v25, v31, v32, v28, v29, v35, v38, v20, v39, v34, v23, v37], None, descr=BasicFailDescr()),
            ]
    cpu = CPU(None, None)
    looptoken = LoopToken()
    cpu.compile_loop(inputargs, operations, looptoken)
    cpu.set_future_value_int(0, 17)
    cpu.set_future_value_int(1, -20)
    cpu.set_future_value_int(2, -6)
    cpu.set_future_value_int(3, 6)
    cpu.set_future_value_int(4, 1)
    cpu.set_future_value_int(5, 13)
    cpu.set_future_value_int(6, 13)
    cpu.set_future_value_int(7, 9)
    cpu.set_future_value_int(8, 49)
    cpu.set_future_value_int(9, 8)
    cpu.execute_token(looptoken)
    assert cpu.get_latest_value_int(0) == 0
    assert cpu.get_latest_value_int(1) == 8
    assert cpu.get_latest_value_int(2) == 1
    assert cpu.get_latest_value_int(3) == 131072
    assert cpu.get_latest_value_int(4) == 20
    assert cpu.get_latest_value_int(5) == -1
    assert cpu.get_latest_value_int(6) == 0
    assert cpu.get_latest_value_int(7) == -19
    assert cpu.get_latest_value_int(8) == 6
    assert cpu.get_latest_value_int(9) == 26
    assert cpu.get_latest_value_int(10) == 12
    assert cpu.get_latest_value_int(11) == 0
    assert cpu.get_latest_value_int(12) == 0
    assert cpu.get_latest_value_int(13) == 2
    assert cpu.get_latest_value_int(14) == 2
    assert cpu.get_latest_value_int(15) == 1
    assert cpu.get_latest_value_int(16) == -57344
    assert cpu.get_latest_value_int(17) == 1
    assert cpu.get_latest_value_int(18) == -1
    assert cpu.get_latest_value_int(19) == -2147483648
    assert cpu.get_latest_value_int(20) == -49
