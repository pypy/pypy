from rpython.jit.metainterp.history import ResOperation, BoxInt, ConstInt,\
     BasicFailDescr, JitCellToken, BasicFinalDescr, TargetToken, ConstPtr,\
     BoxPtr, BoxFloat, ConstFloat
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.backend.x86.arch import WORD
from rpython.jit.tool.oparser import parse
from rpython.rtyper.lltypesystem import lltype, rffi, rclass, llmemory, rstr
from rpython.rtyper.llinterp import LLException
from rpython.rtyper.annlowlevel import llhelper
from rpython.jit.codewriter.effectinfo import EffectInfo
from rpython.jit.codewriter import longlong, heaptracker

CPU = getcpuclass()

def test_bug_rshift():
    v1 = BoxInt()
    v2 = BoxInt()
    v3 = BoxInt()
    v4 = BoxInt()
    zero = BoxInt()
    inputargs = [v1]
    operations = [
        ResOperation(rop.INT_ADD, [v1, v1], v2),
        ResOperation(rop.INT_INVERT, [v2], v3),
        ResOperation(rop.UINT_RSHIFT, [v1, ConstInt(3)], v4),
        ResOperation(rop.SAME_AS, [ConstInt(0)], zero),
        ResOperation(rop.GUARD_TRUE, [zero], None, descr=BasicFailDescr()),
        ResOperation(rop.FINISH, [], None, descr=BasicFinalDescr())
        ]
    operations[-2].setfailargs([v4, v3])
    cpu = CPU(None, None)
    cpu.setup_once()
    looptoken = JitCellToken()
    cpu.compile_loop(inputargs, operations, looptoken)
    deadframe = cpu.execute_token(looptoken, 9)
    assert cpu.get_int_value(deadframe, 0) == (9 >> 3)
    assert cpu.get_int_value(deadframe, 1) == (~18)

def test_bug_int_is_true_1():
    v1 = BoxInt()
    v2 = BoxInt()
    v3 = BoxInt()
    v4 = BoxInt()
    zero = BoxInt()
    tmp5 = BoxInt()
    inputargs = [v1]
    operations = [
        ResOperation(rop.INT_MUL, [v1, v1], v2),
        ResOperation(rop.INT_MUL, [v2, v1], v3),
        ResOperation(rop.INT_IS_TRUE, [v2], tmp5),
        ResOperation(rop.INT_IS_ZERO, [tmp5], v4),
        ResOperation(rop.SAME_AS, [ConstInt(0)], zero),
        ResOperation(rop.GUARD_TRUE, [zero], None, descr=BasicFailDescr()),
        ResOperation(rop.FINISH, [], None, descr=BasicFinalDescr())
            ]
    operations[-2].setfailargs([v4, v3, tmp5])
    cpu = CPU(None, None)
    cpu.setup_once()
    looptoken = JitCellToken()
    cpu.compile_loop(inputargs, operations, looptoken)
    deadframe = cpu.execute_token(looptoken, -10)
    assert cpu.get_int_value(deadframe, 0) == 0
    assert cpu.get_int_value(deadframe, 1) == -1000
    assert cpu.get_int_value(deadframe, 2) == 1

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
    zero = BoxInt()
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
        ResOperation(rop.SAME_AS, [ConstInt(0)], zero),
        ResOperation(rop.GUARD_TRUE, [zero], None, descr=BasicFailDescr()),
        ResOperation(rop.FINISH, [], None, descr=BasicFinalDescr())
            ]
    operations[-2].setfailargs([v40, v36, v37, v31, v16, v34, v35, v23,
                                v22, v29, v14, v39, v30, v38])
    cpu = CPU(None, None)
    cpu.setup_once()
    looptoken = JitCellToken()
    cpu.compile_loop(inputargs, operations, looptoken)
    deadframe = cpu.execute_token(looptoken, -13, 10, 10, 8, -8,
                                  -16, -18, 46, -12, 26)
    assert cpu.get_int_value(deadframe, 0) == 0
    assert cpu.get_int_value(deadframe, 1) == 0
    assert cpu.get_int_value(deadframe, 2) == 0
    assert cpu.get_int_value(deadframe, 3) == 0
    assert cpu.get_int_value(deadframe, 4) == 1
    assert cpu.get_int_value(deadframe, 5) == -7
    assert cpu.get_int_value(deadframe, 6) == 1
    assert cpu.get_int_value(deadframe, 7) == 0
    assert cpu.get_int_value(deadframe, 8) == -2
    assert cpu.get_int_value(deadframe, 9) == 18
    assert cpu.get_int_value(deadframe, 10) == 1
    assert cpu.get_int_value(deadframe, 11) == 18
    assert cpu.get_int_value(deadframe, 12) == -1
    assert cpu.get_int_value(deadframe, 13) == 0

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
    zero = BoxInt()
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
        ResOperation(rop.SAME_AS, [ConstInt(0)], zero),
        ResOperation(rop.GUARD_TRUE, [zero], None, descr=BasicFailDescr()),
        ResOperation(rop.FINISH, [], None, descr=BasicFinalDescr())
            ]
    operations[-2].setfailargs([v40, v10, v36, v26, v13, v30, v21, v33,
                                v18, v25, v31, v32, v28, v29, v35, v38,
                                v20, v39, v34, v23, v37])
    cpu = CPU(None, None)
    cpu.setup_once()
    looptoken = JitCellToken()
    cpu.compile_loop(inputargs, operations, looptoken)
    deadframe = cpu.execute_token(looptoken, 17, -20, -6, 6, 1,
                                  13, 13, 9, 49, 8)
    assert cpu.get_int_value(deadframe, 0) == 0
    assert cpu.get_int_value(deadframe, 1) == 8
    assert cpu.get_int_value(deadframe, 2) == 1
    assert cpu.get_int_value(deadframe, 3) == 131072
    assert cpu.get_int_value(deadframe, 4) == 20
    assert cpu.get_int_value(deadframe, 5) == -1
    assert cpu.get_int_value(deadframe, 6) == 0
    assert cpu.get_int_value(deadframe, 7) == -19
    assert cpu.get_int_value(deadframe, 8) == 6
    assert cpu.get_int_value(deadframe, 9) == 26
    assert cpu.get_int_value(deadframe, 10) == 12
    assert cpu.get_int_value(deadframe, 11) == 0
    assert cpu.get_int_value(deadframe, 12) == 0
    assert cpu.get_int_value(deadframe, 13) == 2
    assert cpu.get_int_value(deadframe, 14) == 2
    assert cpu.get_int_value(deadframe, 15) == 1
    assert cpu.get_int_value(deadframe, 16) == -57344
    assert cpu.get_int_value(deadframe, 17) == 1
    assert cpu.get_int_value(deadframe, 18) == -1
    if WORD == 4:
        assert cpu.get_int_value(deadframe, 19) == -2147483648
    elif WORD == 8:
        assert cpu.get_int_value(deadframe, 19) == 19327352832
    assert cpu.get_int_value(deadframe, 20) == -49

def getllhelper(cpu, f, ARGS, RES):
    FPTR = lltype.Ptr(lltype.FuncType(ARGS, RES))
    fptr = llhelper(FPTR, f)
    calldescr = cpu.calldescrof(FPTR.TO, FPTR.TO.ARGS, FPTR.TO.RESULT,
                                EffectInfo.MOST_GENERAL)
    return rffi.cast(lltype.Signed, fptr), calldescr

def getexception(cpu, count):
    xtp = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
    xtp.subclassrange_min = 1
    xtp.subclassrange_max = 3
    X = lltype.GcStruct('X', ('parent', rclass.OBJECT),
                        hints={'vtable':  xtp._obj})
    xptr = lltype.malloc(X)
    vtableptr = X._hints['vtable']._as_ptr()

    def f(*args):
        raise LLException(vtableptr, xptr)

    fptr, funcdescr = getllhelper(cpu, f, [lltype.Signed] * count, lltype.Void)
    
    return heaptracker.adr2int(llmemory.cast_ptr_to_adr(vtableptr)), fptr, funcdescr

def getnoexception(cpu, count):
    def f(*args):
        return sum(args)

    return getllhelper(cpu, f, [lltype.Signed] * count, lltype.Signed)

def getvtable(cpu, S=None):
    cls1 = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
    cls1.subclassrange_min = 1
    cls1.subclassrange_max = 3
    if S is not None:
        descr = cpu.sizeof(S)
        if not hasattr(cpu.tracker, '_all_size_descrs_with_vtable'):
            cpu.tracker._all_size_descrs_with_vtable = []
        cpu.tracker._all_size_descrs_with_vtable.append(descr)
        descr._corresponding_vtable = cls1
    return llmemory.cast_adr_to_int(llmemory.cast_ptr_to_adr(cls1), "symbolic")

def test_bug_2():
    cpu = CPU(None, None)
    cpu.setup_once()

    S4 = lltype.Struct('Sx', ("f0", lltype.Char), ("f1", lltype.Signed), ("f2", lltype.Signed), ("f3", lltype.Signed))
    S5 = lltype.GcArray(S4)
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
    tmp11 = BoxInt()
    tmp12 = BoxPtr()
    faildescr0 = BasicFailDescr()
    tmp13 = BoxPtr()
    faildescr1 = BasicFailDescr()
    finishdescr2 = BasicFinalDescr()
    const_ptr14 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.STR, 1)))
    const_ptr15 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.UNICODE, 489)))
    const_ptr16 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.UNICODE, 16)))
    const_ptr17 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S5, 299)))
    inputargs = [v1, v2, v3, v4, v5, v6, v7, v8, v9, v10]

    xtp, func, funcdescr = getexception(cpu, 3)
    xtp2, func2, func2descr = getexception(cpu, 2)

    operations = [
        ResOperation(rop.STRGETITEM, [const_ptr14, ConstInt(0)], tmp11),
        ResOperation(rop.LABEL, [v1, v2, tmp11, v3, v4, v5, v6, v7, v8, v9, v10], None, TargetToken()),
        ResOperation(rop.UNICODESETITEM, [const_ptr15, v4, ConstInt(22)], None),
        ResOperation(rop.CALL, [ConstInt(func), v2, v1, v9], None, descr=funcdescr),
        ResOperation(rop.GUARD_EXCEPTION, [ConstInt(xtp)], tmp12, descr=faildescr0),
        ResOperation(rop.UNICODESETITEM, [const_ptr16, ConstInt(13), ConstInt(9)], None),
        ResOperation(rop.SETINTERIORFIELD_GC, [const_ptr17, v3, v7], None, cpu.interiorfielddescrof(S5, 'f3')),
        ResOperation(rop.CALL, [ConstInt(func2), v7, v10], None, descr=func2descr),
        ResOperation(rop.GUARD_NO_EXCEPTION, [], tmp13, descr=faildescr1),
        ResOperation(rop.FINISH, [], None, descr=finishdescr2),
        ]
    operations[4].setfailargs([v4, v8, v10, v2, v9, v7, v6, v1])
    operations[8].setfailargs([v3, v9, v2, v6, v4])
    looptoken = JitCellToken()
    cpu.compile_loop(inputargs, operations, looptoken)
    loop_args = [1, -39, 46, 21, 16, 6, -4611686018427387905, 12, 14, 2]
    frame = cpu.execute_token(looptoken, *loop_args)
    assert cpu.get_int_value(frame, 0) == 46
    assert cpu.get_int_value(frame, 1) == 14
    assert cpu.get_int_value(frame, 2) == -39
    assert cpu.get_int_value(frame, 3) == 6
    assert cpu.get_int_value(frame, 4) == 21
    S4 = lltype.GcStruct('Sx', ("parent", rclass.OBJECT), ("f0", lltype.Signed))
    S5 = lltype.GcStruct('Sx', ("f0", lltype.Signed))
    S6 = lltype.GcArray(lltype.Signed)
    S7 = lltype.GcStruct('Sx', ("parent", rclass.OBJECT), ("f0", lltype.Char))
    S8 = lltype.Struct('Sx', ("f0", lltype.Char), ("f1", lltype.Signed), ("f2", lltype.Signed), ("f3", lltype.Signed))
    S9 = lltype.GcArray(S8)
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
    p20 = BoxPtr()
    tmp21 = BoxPtr()
    faildescr3 = BasicFailDescr()
    tmp22 = BoxPtr()
    faildescr4 = BasicFailDescr()
    tmp23 = BoxInt()
    tmp24 = BoxInt()
    tmp25 = BoxInt()
    tmp26 = BoxInt()
    tmp27 = BoxInt()
    tmp28 = BoxInt()
    tmp29 = BoxInt()
    faildescr5 = BasicFailDescr()
    tmp30 = BoxPtr()
    faildescr6 = BasicFailDescr()
    finishdescr7 = BasicFinalDescr()
    const_ptr31 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S4)))
    const_ptr32 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.STR, 46)))
    const_ptr33 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S5)))
    const_ptr34 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.UNICODE, 26)))
    const_ptr35 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.UNICODE, 15)))
    const_ptr36 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S7)))
    const_ptr37 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.STR, 484)))
    const_ptr38 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S9, 299)))
    inputargs = [v1, v2, v3, v4, v5]

    func3, func3descr = getnoexception(cpu, 5)
    xtp3, func4, func4descr = getexception(cpu, 10)

    operations = [
        ResOperation(rop.GUARD_EXCEPTION, [ConstInt(xtp2)], tmp21, descr=faildescr3),
        ResOperation(rop.INT_IS_ZERO, [v4], v6),
        ResOperation(rop.INT_NE, [v6, ConstInt(13)], v7),
        ResOperation(rop.GETFIELD_GC, [const_ptr31], v8, cpu.fielddescrof(S4, 'f0')),
        ResOperation(rop.STRSETITEM, [const_ptr32, v6, ConstInt(0)], None),
        ResOperation(rop.NEWSTR, [ConstInt(5)], tmp22),
        ResOperation(rop.STRSETITEM, [tmp22, ConstInt(0), ConstInt(42)], None),
        ResOperation(rop.STRSETITEM, [tmp22, ConstInt(1), ConstInt(42)], None),
        ResOperation(rop.STRSETITEM, [tmp22, ConstInt(2), ConstInt(20)], None),
        ResOperation(rop.STRSETITEM, [tmp22, ConstInt(3), ConstInt(48)], None),
        ResOperation(rop.STRSETITEM, [tmp22, ConstInt(4), ConstInt(6)], None),
        ResOperation(rop.GETFIELD_GC, [const_ptr33], v9, cpu.fielddescrof(S5, 'f0')),
        ResOperation(rop.UNICODESETITEM, [const_ptr34, ConstInt(24), ConstInt(65533)], None),
        ResOperation(rop.GETFIELD_GC, [const_ptr31], v10, cpu.fielddescrof(S4, 'f0')),
        ResOperation(rop.INT_NE, [v10, ConstInt(25)], v11),
        ResOperation(rop.CALL, [ConstInt(func3), v5, v1, v8, v3, v2], v12, descr=func3descr),
        ResOperation(rop.GUARD_NO_EXCEPTION, [], None, descr=faildescr4),
        ResOperation(rop.UNICODELEN, [const_ptr35], tmp23),
        ResOperation(rop.NEW_ARRAY, [v2], p20, cpu.arraydescrof(S6)),
        ResOperation(rop.GETFIELD_GC, [const_ptr36], v13, cpu.fielddescrof(S7, 'f0')),
        ResOperation(rop.INT_OR, [v8, ConstInt(2)], tmp24),
        ResOperation(rop.INT_FLOORDIV, [ConstInt(8), tmp24], v14),
        ResOperation(rop.GETARRAYITEM_GC, [p20, ConstInt(3)], v15, cpu.arraydescrof(S6)),
        ResOperation(rop.COPYSTRCONTENT, [tmp22, const_ptr37, ConstInt(1), ConstInt(163), ConstInt(0)], None),
        ResOperation(rop.COPYUNICODECONTENT, [const_ptr35, const_ptr34, ConstInt(13), ConstInt(0), v6], None),
        ResOperation(rop.STRGETITEM, [tmp22, v6], tmp25),
        ResOperation(rop.STRGETITEM, [tmp22, ConstInt(0)], tmp26),
        ResOperation(rop.GETINTERIORFIELD_GC, [const_ptr38, v13], v16, cpu.interiorfielddescrof(S9, 'f0')),
        ResOperation(rop.INT_GE, [v4, v5], v17),
        ResOperation(rop.INT_OR, [v13, ConstInt(2)], tmp27),
        ResOperation(rop.INT_FLOORDIV, [ConstInt(12), tmp27], v18),
        ResOperation(rop.INT_AND, [v1, ConstInt(-4)], tmp28),
        ResOperation(rop.INT_OR, [tmp28, ConstInt(2)], tmp29),
        ResOperation(rop.INT_FLOORDIV, [v15, tmp29], v19),
        ResOperation(rop.GUARD_FALSE, [v17], None, descr=faildescr5),
        ResOperation(rop.UNICODESETITEM, [const_ptr34, ConstInt(20), ConstInt(65522)], None),
        ResOperation(rop.CALL, [ConstInt(func4), v3, v9, v10, v8, v11, v5, v13, v14, v15, v6], None, descr=func4descr),
        ResOperation(rop.GUARD_NO_EXCEPTION, [], tmp30, descr=faildescr6),
        ResOperation(rop.FINISH, [], None, descr=finishdescr7),
        ]
    operations[0].setfailargs([])
    operations[16].setfailargs([v5, v9])
    operations[34].setfailargs([])
    operations[37].setfailargs([v12, v19, v10, v7, v4, v8, v18, v15, v9])
    cpu.compile_bridge(faildescr1, inputargs, operations, looptoken)
    frame = cpu.execute_token(looptoken, *loop_args)
    #assert cpu.get_int_value(frame, 0) == -9223372036854775766
    assert cpu.get_int_value(frame, 1) == 0
    #assert cpu.get_int_value(frame, 2) == -9223372036854775808
    assert cpu.get_int_value(frame, 3) == 1
    assert cpu.get_int_value(frame, 4) == 6
    #assert cpu.get_int_value(frame, 5) == -9223372036854775808
    assert cpu.get_int_value(frame, 6) == 0
    assert cpu.get_int_value(frame, 7) == 0
    #assert cpu.get_int_value(frame, 8) == 26
    S4 = lltype.GcStruct('Sx', ("parent", rclass.OBJECT), ("f0", lltype.Signed), ("f1", lltype.Signed))
    S5 = lltype.GcStruct('Sx', ("parent", rclass.OBJECT), ("f0", lltype.Signed))
    S6 = lltype.GcStruct('Sx', ("f0", lltype.Signed), ("f1", rffi.UCHAR))
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
    tmp19 = BoxPtr()
    faildescr8 = BasicFailDescr()
    tmp20 = BoxInt()
    tmp21 = BoxInt()
    tmp22 = BoxInt()
    tmp23 = BoxInt()
    faildescr9 = BasicFailDescr()
    tmp24 = BoxInt()
    tmp25 = BoxInt()
    tmp26 = BoxInt()
    tmp27 = BoxPtr()
    tmp28 = BoxPtr()
    faildescr10 = BasicFailDescr()
    finishdescr11 = BasicFinalDescr()
    const_ptr29 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S4)))
    const_ptr30 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.UNICODE, 26)))
    const_ptr31 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.UNICODE, 1)))
    const_ptr32 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S5)))
    const_ptr33 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S6)))
    const_ptr34 = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(rstr.STR, 26)))
    inputargs = [v1, v2, v3, v4, v5, v6, v7, v8, v9]
    operations = [
        ResOperation(rop.GUARD_EXCEPTION, [ConstInt(xtp3)], tmp19, descr=faildescr8),
        ResOperation(rop.SETFIELD_GC, [const_ptr29, v7], None, cpu.fielddescrof(S4, 'f0')),
        ResOperation(rop.UNICODEGETITEM, [const_ptr30, ConstInt(21)], tmp20),
        ResOperation(rop.UNICODEGETITEM, [const_ptr30, ConstInt(10)], tmp21),
        ResOperation(rop.UINT_RSHIFT, [v9, ConstInt(40)], v10),
        ResOperation(rop.UNICODEGETITEM, [const_ptr30, ConstInt(25)], tmp22),
        ResOperation(rop.INT_NE, [ConstInt(-8), v9], v11),
        ResOperation(rop.INT_MUL_OVF, [v3, ConstInt(-4)], tmp23),
        ResOperation(rop.GUARD_OVERFLOW, [], None, descr=faildescr9),
        ResOperation(rop.UNICODESETITEM, [const_ptr31, ConstInt(0), ConstInt(50175)], None),
        ResOperation(rop.UINT_GT, [v8, ConstInt(-6)], v12),
        ResOperation(rop.GETFIELD_GC, [const_ptr32], v13, cpu.fielddescrof(S5, 'f0')),
        ResOperation(rop.INT_AND, [ConstInt(8), v8], v14),
        ResOperation(rop.INT_INVERT, [v1], v15),
        ResOperation(rop.SETFIELD_GC, [const_ptr33, ConstInt(3)], None, cpu.fielddescrof(S6, 'f1')),
        ResOperation(rop.INT_GE, [v14, v6], v16),
        ResOperation(rop.INT_AND, [v5, ConstInt(-4)], tmp24),
        ResOperation(rop.INT_OR, [tmp24, ConstInt(2)], tmp25),
        ResOperation(rop.INT_FLOORDIV, [v9, tmp25], v17),
        ResOperation(rop.STRLEN, [const_ptr34], tmp26),
        ResOperation(rop.NEWSTR, [ConstInt(7)], tmp27),
        ResOperation(rop.STRSETITEM, [tmp27, ConstInt(0), ConstInt(21)], None),
        ResOperation(rop.STRSETITEM, [tmp27, ConstInt(1), ConstInt(79)], None),
        ResOperation(rop.STRSETITEM, [tmp27, ConstInt(2), ConstInt(7)], None),
        ResOperation(rop.STRSETITEM, [tmp27, ConstInt(3), ConstInt(2)], None),
        ResOperation(rop.STRSETITEM, [tmp27, ConstInt(4), ConstInt(229)], None),
        ResOperation(rop.STRSETITEM, [tmp27, ConstInt(5), ConstInt(233)], None),
        ResOperation(rop.STRSETITEM, [tmp27, ConstInt(6), ConstInt(208)], None),
        ResOperation(rop.INT_LT, [ConstInt(-31), v10], v18),
        ResOperation(rop.SAME_AS, [ConstPtr(lltype.nullptr(llmemory.GCREF.TO))], tmp28),
        ResOperation(rop.GUARD_NONNULL_CLASS, [tmp28, ConstInt(xtp2)], None, descr=faildescr10),
        ResOperation(rop.FINISH, [v4], None, descr=finishdescr11),
        ]
    operations[0].setfailargs([])
    operations[8].setfailargs([tmp23, v5, v3, v11, v6])
    operations[30].setfailargs([v6])
    cpu.compile_bridge(faildescr6, inputargs, operations, looptoken)
    frame = cpu.execute_token(looptoken, *loop_args)
    #assert cpu.get_int_value(frame, 0) == -9223372036854775808
    v1 = BoxInt()
    v2 = BoxInt()
    p3 = BoxPtr()
    tmp4 = BoxInt()
    tmp5 = BoxPtr()
    faildescr12 = BasicFailDescr()
    finishdescr13 = BasicFinalDescr()
    inputargs = [v1]

    _, func5, func5descr = getexception(cpu, 0)
    vt = getvtable(cpu, S4)

    operations = [
        ResOperation(rop.INT_AND, [v1, ConstInt(63)], tmp4),
        ResOperation(rop.INT_LSHIFT, [ConstInt(10), tmp4], v2),
        ResOperation(rop.NEW_WITH_VTABLE, [ConstInt(vt)], p3),
        ResOperation(rop.CALL, [ConstInt(func5)], None, descr=func5descr),
        ResOperation(rop.GUARD_EXCEPTION, [ConstInt(xtp2)], tmp5, descr=faildescr12),
        ResOperation(rop.FINISH, [], None, descr=finishdescr13),
        ]
    operations[4].setfailargs([v2])
    cpu.compile_bridge(faildescr10, inputargs, operations, looptoken)
    frame = cpu.execute_token(looptoken, *loop_args)
    #assert cpu.get_int_value(frame, 0) == 10
