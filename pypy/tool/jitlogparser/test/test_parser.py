from pypy.tool.jitlogparser.parser import (SimpleParser, TraceForOpcode,
                                           Function, adjust_bridges,
                                           import_log)
from pypy.tool.jitlogparser.storage import LoopStorage
import py, sys

def parse(input, **kwds):
    return SimpleParser.parse_from_input(input, **kwds)


def test_parse():
    ops = parse('''
    [i7]
    i9 = int_lt(i7, 1003)
    guard_true(i9, descr=<Guard2>) []
    i13 = getfield_raw(151937600, descr=<SignedFieldDescr pypysig_long_struct.c_value 0>)
    ''').operations
    assert len(ops) == 3
    assert ops[0].name == 'int_lt'
    assert ops[1].name == 'guard_true'
    assert ops[1].descr is not None
    assert ops[0].res == 'i9'
    assert ops[0].repr() == 'i9 = int_lt(i7, 1003)'
    assert ops[2].descr is not None
    assert len(ops[2].args) == 1
    assert ops[-1].repr() == 'i13 = getfield_raw(151937600, descr=<SignedFieldDescr pypysig_long_struct.c_value 0>)'

def test_parse_non_code():
    ops = parse('''
    []
    debug_merge_point(0, "SomeRandomStuff")
    ''')
    res = Function.from_operations(ops.operations, LoopStorage())
    assert len(res.chunks) == 1
    assert res.chunks[0].repr()

def test_split():
    ops = parse('''
    [i0]
    debug_merge_point(0, "<code object stuff. file '/I/dont/exist.py'. line 200> #10 ADD")
    debug_merge_point(0, "<code object stuff. file '/I/dont/exist.py'. line 200> #11 SUB")
    i1 = int_add(i0, 1)
    debug_merge_point(0, "<code object stuff. file '/I/dont/exist.py'. line 200> #11 SUB")
    i2 = int_add(i1, 1)
    ''')
    res = Function.from_operations(ops.operations, LoopStorage())
    assert len(res.chunks) == 3
    assert len(res.chunks[0].operations) == 1
    assert len(res.chunks[1].operations) == 2
    assert len(res.chunks[2].operations) == 2
    assert res.chunks[2].bytecode_no == 11

def test_inlined_call():
    ops = parse("""
    []
    debug_merge_point(0, '<code object inlined_call. file 'source.py'. line 12> #28 CALL_FUNCTION')
    i18 = getfield_gc(p0, descr=<BoolFieldDescr pypy.interpreter.pyframe.PyFrame.inst_is_being_profiled 89>)
    debug_merge_point(1, '<code object inner. file 'source.py'. line 9> #0 LOAD_FAST')
    debug_merge_point(1, '<code object inner. file 'source.py'. line 9> #3 LOAD_CONST')
    debug_merge_point(1, '<code object inner. file 'source.py'. line 9> #7 RETURN_VALUE')
    debug_merge_point(0, '<code object inlined_call. file 'source.py'. line 12> #31 STORE_FAST')
    """)
    res = Function.from_operations(ops.operations, LoopStorage())
    assert len(res.chunks) == 3 # two chunks + inlined call
    assert isinstance(res.chunks[0], TraceForOpcode)
    assert isinstance(res.chunks[1], Function)
    assert isinstance(res.chunks[2], TraceForOpcode)
    assert res.chunks[1].path == "1"
    assert len(res.chunks[1].chunks) == 3

def test_name():
    ops = parse('''
    [i0]
    debug_merge_point(0, "<code object stuff. file '/I/dont/exist.py'. line 200> #10 ADD")
    debug_merge_point(0, "<code object stuff. file '/I/dont/exist.py'. line 201> #11 SUB")
    i1 = int_add(i0, 1)
    debug_merge_point(0, "<code object stuff. file '/I/dont/exist.py'. line 202> #11 SUB")
    i2 = int_add(i1, 1)
    ''')
    res = Function.from_operations(ops.operations, LoopStorage())
    assert res.repr() == res.chunks[0].repr()
    assert res.repr() == "stuff, file '/I/dont/exist.py', line 200"
    assert res.startlineno == 200
    assert res.filename == '/I/dont/exist.py'
    assert res.name == 'stuff'

def test_name_no_first():
    ops = parse('''
    [i0]
    i3 = int_add(i0, 1)
    debug_merge_point(0, "<code object stuff. file '/I/dont/exist.py'. line 200> #10 ADD")
    debug_merge_point(0, "<code object stuff. file '/I/dont/exist.py'. line 201> #11 SUB")
    i1 = int_add(i0, 1)
    debug_merge_point(0, "<code object stuff. file '/I/dont/exist.py'. line 202> #11 SUB")
    i2 = int_add(i1, 1)
    ''')
    res = Function.from_operations(ops.operations, LoopStorage())
    assert res.repr() == res.chunks[1].repr()

def test_lineno():
    fname = str(py.path.local(__file__).join('..', 'x.py'))
    ops = parse('''
    [i0, i1]
    debug_merge_point(0, "<code object f. file '%(fname)s'. line 2> #0 LOAD_FAST")
    debug_merge_point(0, "<code object f. file '%(fname)s'. line 2> #3 LOAD_FAST")
    debug_merge_point(0, "<code object f. file '%(fname)s'. line 2> #6 BINARY_ADD")
    debug_merge_point(0, "<code object f. file '%(fname)s'. line 2> #7 RETURN_VALUE")
    ''' % locals())
    res = Function.from_operations(ops.operations, LoopStorage())
    assert res.chunks[1].lineno == 3

def test_linerange():
    if sys.version_info > (2, 6):
        py.test.skip("unportable test")
    fname = str(py.path.local(__file__).join('..', 'x.py'))
    ops = parse('''
    [i0, i1]
    debug_merge_point(0, "<code object g. file '%(fname)s'. line 5> #9 LOAD_FAST")
    debug_merge_point(0, "<code object g. file '%(fname)s'. line 5> #12 LOAD_CONST")
    debug_merge_point(0, "<code object g. file '%(fname)s'. line 5> #22 LOAD_CONST")
    debug_merge_point(0, "<code object g. file '%(fname)s'. line 5> #28 LOAD_CONST")
    debug_merge_point(0, "<code object g. file '%(fname)s'. line 5> #6 SETUP_LOOP")
    ''' % locals())
    res = Function.from_operations(ops.operations, LoopStorage())
    assert res.linerange == (7, 9)
    assert res.lineset == set([7, 8, 9])

def test_linerange_notstarts():
    if sys.version_info > (2, 6):
        py.test.skip("unportable test")
    fname = str(py.path.local(__file__).join('..', 'x.py'))
    ops = parse("""
    [p6, p1]
    debug_merge_point(0, '<code object h. file '%(fname)s'. line 11> #17 FOR_ITER')
    guard_class(p6, 144264192, descr=<Guard2>)
    p12 = getfield_gc(p6, descr=<GcPtrFieldDescr pypy.objspace.std.iterobject.W_AbstractSeqIterObject.inst_w_seq 12>)
    """ % locals())
    res = Function.from_operations(ops.operations, LoopStorage())
    assert res.lineset

def test_reassign_loops():
    main = parse('''
    [v0]
    guard_false(v0, descr=<Guard18>) []
    ''')
    main.count = 10
    bridge = parse('''
    # bridge out of Guard 18 with 13 ops
    [i0, i1]
    int_add(i0, i1)
    ''')
    bridge.count = 3
    entry_bridge = parse('''
    # Loop 3 : entry bridge
    []
    ''')
    loops = LoopStorage().reconnect_loops([main, bridge, entry_bridge])
    assert len(loops) == 2
    assert len(loops[0].operations[0].bridge.operations) == 1
    assert loops[0].operations[0].bridge.no == 18
    assert loops[0].operations[0].percentage == 30

def test_adjust_bridges():
    main = parse('''
    [v0]
    guard_false(v0, descr=<Guard13>)
    guard_true(v0, descr=<Guard5>)
    ''')
    bridge = parse('''
    # bridge out of Guard 13
    []
    int_add(0, 1)
    ''')
    LoopStorage().reconnect_loops([main, bridge])
    assert adjust_bridges(main, {})[1].name == 'guard_true'
    assert adjust_bridges(main, {'loop-13': True})[1].name == 'int_add'

def test_parsing_strliteral():
    loop = parse("""
    debug_merge_point(0, 'StrLiteralSearch at 11/51 [17, 8, 3, 1, 1, 1, 1, 51, 0, 19, 51, 1]')
    """)
    ops = Function.from_operations(loop.operations, LoopStorage())
    chunk = ops.chunks[0]
    assert chunk.bytecode_name == 'StrLiteralSearch'

def test_parsing_assembler():
    backend_dump = "554889E5534154415541564157488DA500000000488B042590C5540148C7042590C554010000000048898570FFFFFF488B042598C5540148C7042598C554010000000048898568FFFFFF488B0425A0C5540148C70425A0C554010000000048898560FFFFFF488B0425A8C5540148C70425A8C554010000000048898558FFFFFF4C8B3C2550525B0149BB30E06C96FC7F00004D8B334983C60149BB30E06C96FC7F00004D89334981FF102700000F8D000000004983C7014C8B342580F76A024983EE014C89342580F76A024983FE000F8C00000000E9AEFFFFFF488B042588F76A024829E0483B042580EC3C01760D49BB05F30894FC7F000041FFD3554889E5534154415541564157488DA550FFFFFF4889BD70FFFFFF4889B568FFFFFF48899560FFFFFF48898D58FFFFFF4D89C7E954FFFFFF49BB00F00894FC7F000041FFD34440484C3D030300000049BB00F00894FC7F000041FFD34440484C3D070304000000"
    dump_start = 0x7f3b0b2e63d5
    loop = parse("""
    # Loop 0 : loop with 19 ops
    [p0, p1, p2, p3, i4]
    debug_merge_point(0, '<code object f. file 'x.py'. line 2> #15 COMPARE_OP')
    +166: i6 = int_lt(i4, 10000)
    guard_true(i6, descr=<Guard3>) [p1, p0, p2, p3, i4]
    debug_merge_point(0, '<code object f. file 'x.py'. line 2> #27 INPLACE_ADD')
    +179: i8 = int_add(i4, 1)
    debug_merge_point(0, '<code object f. file 'x.py'. line 2> #31 JUMP_ABSOLUTE')
    +183: i10 = getfield_raw(40564608, descr=<SignedFieldDescr pypysig_long_struct.c_value 0>)
    +191: i12 = int_sub(i10, 1)
    +195: setfield_raw(40564608, i12, descr=<SignedFieldDescr pypysig_long_struct.c_value 0>)
    +203: i14 = int_lt(i12, 0)
    guard_false(i14, descr=<Guard4>) [p1, p0, p2, p3, i8, None]
    debug_merge_point(0, '<code object f. file 'x.py'. line 2> #9 LOAD_FAST')
    +213: jump(p0, p1, p2, p3, i8, descr=<Loop0>)
    +218: --end of the loop--""", backend_dump=backend_dump,
                 dump_start=dump_start,
                 backend_tp='x86_64')
    cmp = loop.operations[1]
    assert 'jge' in cmp.asm
    assert '0x2710' in cmp.asm
    assert 'jmp' in loop.operations[-1].asm

def test_import_log():
    _, loops = import_log(str(py.path.local(__file__).join('..',
                                                           'logtest.log')))
    for loop in loops:
        loop.force_asm()
    assert 'jge' in loops[0].operations[3].asm

def test_import_log_2():
    _, loops = import_log(str(py.path.local(__file__).join('..',
                                                           'logtest2.log')))
    for loop in loops:
        loop.force_asm()
    assert 'cmp' in loops[1].operations[1].asm
    # bridge
    assert 'jo' in loops[3].operations[3].asm
