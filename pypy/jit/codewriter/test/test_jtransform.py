import py
import random
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.jit.codewriter.jtransform import Transformer
from pypy.jit.metainterp.history import getkind
from pypy.rpython.lltypesystem import lltype, llmemory, rclass, rstr, rlist
from pypy.translator.unsimplify import varoftype
from pypy.jit.codewriter import heaptracker, effectinfo
from pypy.jit.codewriter.flatten import ListOfKind

def const(x):
    return Constant(x, lltype.typeOf(x))

class FakeRTyper:
    class type_system: name = 'lltypesystem'
    instance_reprs = {}

class FakeCPU:
    rtyper = FakeRTyper()
    def calldescrof(self, FUNC, ARGS, RESULT):
        return ('calldescr', FUNC, ARGS, RESULT)
    def fielddescrof(self, STRUCT, name):
        return ('fielddescr', STRUCT, name)
    def arraydescrof(self, ARRAY):
        return FakeDescr(('arraydescr', ARRAY))
    def sizeof(self, STRUCT):
        return FakeDescr(('sizedescr', STRUCT))

class FakeDescr(tuple):
    def as_vtable_size_descr(self):
        return self

class FakeLink:
    args = []
    def __init__(self, exitcase):
        self.exitcase = self.llexitcase = exitcase

class FakeResidualCallControl:
    def guess_call_kind(self, op):
        return 'residual'
    def getcalldescr(self, op):
        return 'calldescr'
    def calldescr_canraise(self, calldescr):
        return True

class FakeRegularCallControl:
    def guess_call_kind(self, op):
        return 'regular'
    def graphs_from(self, op):
        return ['somegraph']
    def get_jitcode(self, graph, called_from=None):
        assert graph == 'somegraph'
        return 'somejitcode'

class FakeResidualIndirectCallControl:
    def guess_call_kind(self, op):
        return 'residual'
    def getcalldescr(self, op):
        return 'calldescr'
    def calldescr_canraise(self, calldescr):
        return True

class FakeRegularIndirectCallControl:
    def guess_call_kind(self, op):
        return 'regular'
    def graphs_from(self, op):
        return ['somegraph1', 'somegraph2']
    def getcalldescr(self, op):
        return 'calldescr'
    def get_jitcode(self, graph, called_from=None):
        assert graph in ('somegraph1', 'somegraph2')
        return 'somejitcode' + graph[-1]
    def calldescr_canraise(self, calldescr):
        return False

class FakeBuiltinCallControl:
    def guess_call_kind(self, op):
        return 'builtin'
    def getcalldescr(self, op, oopspecindex):
        return 'calldescr-%d' % oopspecindex
    def calldescr_canraise(self, calldescr):
        return False


def test_optimize_goto_if_not():
    v1 = Variable()
    v2 = Variable()
    v3 = Variable(); v3.concretetype = lltype.Bool
    sp1 = SpaceOperation('foobar', [], None)
    sp2 = SpaceOperation('foobaz', [], None)
    block = Block([v1, v2])
    block.operations = [sp1, SpaceOperation('int_gt', [v1, v2], v3), sp2]
    block.exitswitch = v3
    block.exits = exits = [FakeLink(False), FakeLink(True)]
    res = Transformer().optimize_goto_if_not(block)
    assert res == True
    assert block.operations == [sp1, sp2]
    assert block.exitswitch == ('int_gt', v1, v2)
    assert block.exits == exits

def test_optimize_goto_if_not__incoming():
    v1 = Variable(); v1.concretetype = lltype.Bool
    block = Block([v1])
    block.exitswitch = v1
    block.exits = [FakeLink(False), FakeLink(True)]
    assert not Transformer().optimize_goto_if_not(block)

def test_optimize_goto_if_not__exit():
    # this case occurs in practice, e.g. with RPython code like:
    #     return bool(p) and p.somefield > 0
    v1 = Variable()
    v2 = Variable()
    v3 = Variable(); v3.concretetype = lltype.Bool
    block = Block([v1, v2])
    block.operations = [SpaceOperation('int_gt', [v1, v2], v3)]
    block.exitswitch = v3
    block.exits = exits = [FakeLink(False), FakeLink(True)]
    block.exits[1].args = [v3]
    res = Transformer().optimize_goto_if_not(block)
    assert res == True
    assert block.operations == []
    assert block.exitswitch == ('int_gt', v1, v2)
    assert block.exits == exits
    assert exits[1].args == [const(True)]

def test_optimize_goto_if_not__unknownop():
    v3 = Variable(); v3.concretetype = lltype.Bool
    block = Block([])
    block.operations = [SpaceOperation('foobar', [], v3)]
    block.exitswitch = v3
    block.exits = [FakeLink(False), FakeLink(True)]
    assert not Transformer().optimize_goto_if_not(block)

def test_optimize_goto_if_not__ptr_eq():
    for opname in ['ptr_eq', 'ptr_ne']:
        v1 = Variable()
        v2 = Variable()
        v3 = Variable(); v3.concretetype = lltype.Bool
        block = Block([v1, v2])
        block.operations = [SpaceOperation(opname, [v1, v2], v3)]
        block.exitswitch = v3
        block.exits = exits = [FakeLink(False), FakeLink(True)]
        res = Transformer().optimize_goto_if_not(block)
        assert res == True
        assert block.operations == []
        assert block.exitswitch == (opname, v1, v2)
        assert block.exits == exits

def test_optimize_goto_if_not__ptr_iszero():
    for opname in ['ptr_iszero', 'ptr_nonzero']:
        v1 = Variable()
        v3 = Variable(); v3.concretetype = lltype.Bool
        block = Block([v1])
        block.operations = [SpaceOperation(opname, [v1], v3)]
        block.exitswitch = v3
        block.exits = exits = [FakeLink(False), FakeLink(True)]
        res = Transformer().optimize_goto_if_not(block)
        assert res == True
        assert block.operations == []
        assert block.exitswitch == (opname, v1, '-live-before')
        assert block.exits == exits

def test_symmetric():
    ops = {'int_add': 'int_add',
           'int_or': 'int_or',
           'int_gt': ('int_gt', 'int_lt'),
           'uint_eq': 'int_eq',
           'uint_le': ('uint_le', 'uint_ge'),
           'char_ne': 'int_ne',
           'char_lt': ('int_lt', 'int_gt'),
           'uint_xor': 'int_xor',
           'float_mul': 'float_mul',
           'float_gt': ('float_gt', 'float_lt'),
           }
    v3 = varoftype(lltype.Signed)
    for v1 in [varoftype(lltype.Signed), const(42)]:
        for v2 in [varoftype(lltype.Signed), const(43)]:
            for name1, name2 in ops.items():
                op = SpaceOperation(name1, [v1, v2], v3)
                op1 = Transformer(FakeCPU()).rewrite_operation(op)
                if isinstance(name2, str):
                    name2 = name2, name2
                if isinstance(v1, Constant) and isinstance(v2, Variable):
                    assert op1.args == [v2, v1]
                    assert op1.result == v3
                    assert op1.opname == name2[1]
                else:
                    assert op1.args == [v1, v2]
                    assert op1.result == v3
                    assert op1.opname == name2[0]

def test_symmetric_int_add_ovf():
    v3 = varoftype(lltype.Signed)
    for v1 in [varoftype(lltype.Signed), const(42)]:
        for v2 in [varoftype(lltype.Signed), const(43)]:
            op = SpaceOperation('int_add_nonneg_ovf', [v1, v2], v3)
            oplist = Transformer(FakeCPU()).rewrite_operation(op)
            op0, op1 = oplist
            assert op0.opname == 'int_add_ovf'
            if isinstance(v1, Constant) and isinstance(v2, Variable):
                assert op0.args == [v2, v1]
                assert op0.result == v3
            else:
                assert op0.args == [v1, v2]
                assert op0.result == v3
            assert op1.opname == '-live-'
            assert op1.args == []
            assert op1.result is None

def test_calls():
    for RESTYPE in [lltype.Signed, rclass.OBJECTPTR,
                    lltype.Float, lltype.Void]:
      for with_void in [False, True]:
        for with_i in [False, True]:
          for with_r in [False, True]:
            for with_f in [False, True]:
              ARGS = []
              if with_void: ARGS += [lltype.Void, lltype.Void]
              if with_i: ARGS += [lltype.Signed, lltype.Char]
              if with_r: ARGS += [rclass.OBJECTPTR, lltype.Ptr(rstr.STR)]
              if with_f: ARGS += [lltype.Float, lltype.Float]
              random.shuffle(ARGS)
              if RESTYPE == lltype.Float: with_f = True
              if with_f: expectedkind = 'irf'   # all kinds
              elif with_i: expectedkind = 'ir'  # integers and references
              else: expectedkind = 'r'          # only references
              yield residual_call_test, ARGS, RESTYPE, expectedkind
              yield direct_call_test, ARGS, RESTYPE, expectedkind
              yield indirect_residual_call_test, ARGS, RESTYPE, expectedkind
              yield indirect_regular_call_test, ARGS, RESTYPE, expectedkind

def get_direct_call_op(argtypes, restype):
    FUNC = lltype.FuncType(argtypes, restype)
    fnptr = lltype.functionptr(FUNC, "g")    # no graph
    c_fnptr = const(fnptr)
    vars = [varoftype(TYPE) for TYPE in argtypes]
    v_result = varoftype(restype)
    op = SpaceOperation('direct_call', [c_fnptr] + vars, v_result)
    return op

def residual_call_test(argtypes, restype, expectedkind):
    op = get_direct_call_op(argtypes, restype)
    tr = Transformer(FakeCPU(), FakeResidualCallControl())
    oplist = tr.rewrite_operation(op)
    op0, op1 = oplist
    reskind = getkind(restype)[0]
    assert op0.opname == 'residual_call_%s_%s' % (expectedkind, reskind)
    assert op0.result == op.result
    assert op0.args[0] == op.args[0]
    assert op0.args[1] == 'calldescr'
    assert len(op0.args) == 2 + len(expectedkind)
    for sublist, kind1 in zip(op0.args[2:], expectedkind):
        assert sublist.kind.startswith(kind1)
        assert list(sublist) == [v for v in op.args[1:]
                                 if getkind(v.concretetype) == sublist.kind]
    for v in op.args[1:]:
        kind = getkind(v.concretetype)
        assert kind == 'void' or kind[0] in expectedkind
    assert op1.opname == '-live-'
    assert op1.args == []

def direct_call_test(argtypes, restype, expectedkind):
    op = get_direct_call_op(argtypes, restype)
    tr = Transformer(FakeCPU(), FakeRegularCallControl())
    tr.graph = 'someinitialgraph'
    oplist = tr.rewrite_operation(op)
    op0, op1 = oplist
    reskind = getkind(restype)[0]
    assert op0.opname == 'inline_call_%s_%s' % (expectedkind, reskind)
    assert op0.result == op.result
    assert op0.args[0] == 'somejitcode'
    assert len(op0.args) == 1 + len(expectedkind)
    for sublist, kind1 in zip(op0.args[1:], expectedkind):
        assert sublist.kind.startswith(kind1)
        assert list(sublist) == [v for v in op.args[1:]
                                 if getkind(v.concretetype) == sublist.kind]
    for v in op.args[1:]:
        kind = getkind(v.concretetype)
        assert kind == 'void' or kind[0] in expectedkind
    assert op1.opname == '-live-'
    assert op1.args == []

def indirect_residual_call_test(argtypes, restype, expectedkind):
    # an indirect call that is residual in all cases is very similar to
    # a residual direct call
    op = get_direct_call_op(argtypes, restype)
    op.opname = 'indirect_call'
    op.args[0] = varoftype(op.args[0].concretetype)
    op.args.append(Constant(['somegraph1', 'somegraph2'], lltype.Void))
    tr = Transformer(FakeCPU(), FakeResidualIndirectCallControl())
    tr.graph = 'someinitialgraph'
    oplist = tr.rewrite_operation(op)
    op0, op1 = oplist
    reskind = getkind(restype)[0]
    assert op0.opname == 'residual_call_%s_%s' % (expectedkind, reskind)
    assert op0.result == op.result
    assert op0.args[0] == op.args[0]
    assert op0.args[1] == 'calldescr'
    assert len(op0.args) == 2 + len(expectedkind)
    for sublist, kind1 in zip(op0.args[2:], expectedkind):
        assert sublist.kind.startswith(kind1)
        assert list(sublist) == [v for v in op.args[1:]
                                 if getkind(v.concretetype)==sublist.kind]
    for v in op.args[1:]:
        kind = getkind(v.concretetype)
        assert kind == 'void' or kind[0] in expectedkind
    assert op1.opname == '-live-'
    assert op1.args == []

def indirect_regular_call_test(argtypes, restype, expectedkind):
    # a regular indirect call is preceded by a guard_value on the
    # function address, so that pyjitpl can know which jitcode to follow
    from pypy.jit.codewriter.flatten import IndirectCallTargets
    op = get_direct_call_op(argtypes, restype)
    op.opname = 'indirect_call'
    op.args[0] = varoftype(op.args[0].concretetype)
    op.args.append(Constant(['somegraph1', 'somegraph2'], lltype.Void))
    tr = Transformer(FakeCPU(), FakeRegularIndirectCallControl())
    tr.graph = 'someinitialgraph'
    oplist = tr.rewrite_operation(op)
    op0gv, op1gv, op0, op1 = oplist
    assert op0gv.opname == '-live-'
    assert op0gv.args == []
    assert op1gv.opname == 'int_guard_value'
    assert op1gv.args == [op.args[0]]
    assert op1gv.result is None
    #
    reskind = getkind(restype)[0]
    assert op0.opname == 'residual_call_%s_%s' % (expectedkind, reskind)
    assert op0.result == op.result
    assert op0.args[0] == op.args[0]
    assert op0.args[1] == 'calldescr'
    assert isinstance(op0.args[2], IndirectCallTargets)
    assert op0.args[2].lst == ['somejitcode1', 'somejitcode2']
    assert len(op0.args) == 3 + len(expectedkind)
    for sublist, kind1 in zip(op0.args[3:], expectedkind):
        assert sublist.kind.startswith(kind1)
        assert list(sublist) == [v for v in op.args[1:]
                                 if getkind(v.concretetype)==sublist.kind]
    for v in op.args[1:]:
        kind = getkind(v.concretetype)
        assert kind == 'void' or kind[0] in expectedkind
    # Note: we still expect a -live- here, even though canraise() returns
    # False, because this 'residual_call' will likely call further jitcodes
    # which can do e.g. guard_class or other stuff requiring anyway a -live-.
    assert op1.opname == '-live-'
    assert op1.args == []

def test_getfield():
    # XXX a more compact encoding would be possible, something along
    # the lines of  getfield_gc_r %r0, $offset, %r1
    # which would not need a Descr at all.
    S1 = lltype.Struct('S1')
    S2 = lltype.GcStruct('S2')
    S  = lltype.GcStruct('S', ('int', lltype.Signed),
                              ('ps1', lltype.Ptr(S1)),
                              ('ps2', lltype.Ptr(S2)),
                              ('flt', lltype.Float),
                              ('boo', lltype.Bool),
                              ('chr', lltype.Char),
                              ('unc', lltype.UniChar))
    for name, suffix in [('int', 'i'),
                         ('ps1', 'i'),
                         ('ps2', 'r'),
                         ('flt', 'f'),
                         ('boo', 'i'),
                         ('chr', 'i'),
                         ('unc', 'i')]:
        v_parent = varoftype(lltype.Ptr(S))
        c_name = Constant(name, lltype.Void)
        v_result = varoftype(getattr(S, name))
        op = SpaceOperation('getfield', [v_parent, c_name], v_result)
        op1 = Transformer(FakeCPU()).rewrite_operation(op)
        assert op1.opname == 'getfield_gc_' + suffix
        fielddescr = ('fielddescr', S, name)
        assert op1.args == [v_parent, fielddescr]
        assert op1.result == v_result

def test_getfield_typeptr():
    v_parent = varoftype(rclass.OBJECTPTR)
    c_name = Constant('typeptr', lltype.Void)
    v_result = varoftype(rclass.OBJECT.typeptr)
    op = SpaceOperation('getfield', [v_parent, c_name], v_result)
    oplist = Transformer(FakeCPU()).rewrite_operation(op)
    op0, op1 = oplist
    assert op0.opname == '-live-'
    assert op0.args == []
    assert op1.opname == 'guard_class'
    assert op1.args == [v_parent]
    assert op1.result == v_result

def test_setfield():
    # XXX a more compact encoding would be possible; see test_getfield()
    S1 = lltype.Struct('S1')
    S2 = lltype.GcStruct('S2')
    S  = lltype.GcStruct('S', ('int', lltype.Signed),
                              ('ps1', lltype.Ptr(S1)),
                              ('ps2', lltype.Ptr(S2)),
                              ('flt', lltype.Float),
                              ('boo', lltype.Bool),
                              ('chr', lltype.Char),
                              ('unc', lltype.UniChar))
    for name, suffix in [('int', 'i'),
                         ('ps1', 'i'),
                         ('ps2', 'r'),
                         ('flt', 'f'),
                         ('boo', 'i'),
                         ('chr', 'i'),
                         ('unc', 'i')]:
        v_parent = varoftype(lltype.Ptr(S))
        c_name = Constant(name, lltype.Void)
        v_newvalue = varoftype(getattr(S, name))
        op = SpaceOperation('setfield', [v_parent, c_name, v_newvalue],
                            varoftype(lltype.Void))
        op1 = Transformer(FakeCPU()).rewrite_operation(op)
        assert op1.opname == 'setfield_gc_' + suffix
        fielddescr = ('fielddescr', S, name)
        assert op1.args == [v_parent, fielddescr, v_newvalue]
        assert op1.result is None

def test_malloc_new():
    S = lltype.GcStruct('S')
    v = varoftype(lltype.Ptr(S))
    op = SpaceOperation('malloc', [Constant(S, lltype.Void),
                                   Constant({'flavor': 'gc'}, lltype.Void)], v)
    op1 = Transformer(FakeCPU()).rewrite_operation(op)
    assert op1.opname == 'new'
    assert op1.args == [('sizedescr', S)]

def test_malloc_new_with_vtable():
    vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
    S = lltype.GcStruct('S', ('parent', rclass.OBJECT))
    heaptracker.set_testing_vtable_for_gcstruct(S, vtable, 'S')
    v = varoftype(lltype.Ptr(S))
    op = SpaceOperation('malloc', [Constant(S, lltype.Void),
                                   Constant({'flavor': 'gc'}, lltype.Void)], v)
    cpu = FakeCPU()
    op1 = Transformer(cpu).rewrite_operation(op)
    assert op1.opname == 'new_with_vtable'
    assert op1.args == [('sizedescr', S)]
    #assert heaptracker.descr2vtable(cpu, op1.args[0]) == vtable [type check]
    vtable_int = heaptracker.adr2int(llmemory.cast_ptr_to_adr(vtable))
    assert heaptracker.vtable2descr(cpu, vtable_int) == op1.args[0]

def test_malloc_new_with_destructor():
    vtable = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
    S = lltype.GcStruct('S', ('parent', rclass.OBJECT), rtti=True)
    DESTRUCTOR = lltype.FuncType([lltype.Ptr(S)], lltype.Void)
    destructor = lltype.functionptr(DESTRUCTOR, 'destructor')
    lltype.attachRuntimeTypeInfo(S, destrptr=destructor)
    heaptracker.set_testing_vtable_for_gcstruct(S, vtable, 'S')
    v = varoftype(lltype.Ptr(S))
    op = SpaceOperation('malloc', [Constant(S, lltype.Void),
                                   Constant({'flavor': 'gc'}, lltype.Void)], v)
    tr = Transformer(FakeCPU(), FakeResidualCallControl())
    oplist = tr.rewrite_operation(op)
    op0, op1 = oplist
    assert op0.opname == 'residual_call_r_r'
    assert op0.args[0].value == 'alloc_with_del'    # pseudo-function as a str
    assert list(op0.args[2]) == []
    assert op1.opname == '-live-'
    assert op1.args == []

def test_rename_on_links():
    v1 = Variable()
    v2 = Variable()
    v3 = Variable()
    block = Block([v1])
    block.operations = [SpaceOperation('cast_pointer', [v1], v2)]
    block2 = Block([v3])
    block.closeblock(Link([v2], block2))
    Transformer().optimize_block(block)
    assert block.inputargs == [v1]
    assert block.operations == []
    assert block.exits[0].target is block2
    assert block.exits[0].args == [v1]

def test_int_eq():
    v1 = varoftype(lltype.Signed)
    v2 = varoftype(lltype.Signed)
    v3 = varoftype(lltype.Bool)
    c0 = const(0)
    #
    for opname, reducedname in [('int_eq', 'int_is_zero'),
                                ('int_ne', 'int_is_true')]:
        op = SpaceOperation(opname, [v1, v2], v3)
        op1 = Transformer().rewrite_operation(op)
        assert op1.opname == opname
        assert op1.args == [v1, v2]
        #
        op = SpaceOperation(opname, [v1, c0], v3)
        op1 = Transformer().rewrite_operation(op)
        assert op1.opname == reducedname
        assert op1.args == [v1]
        #
        op = SpaceOperation(opname, [c0, v2], v3)
        op1 = Transformer().rewrite_operation(op)
        assert op1.opname == reducedname
        assert op1.args == [v2]

def test_ptr_eq():
    v1 = varoftype(rclass.OBJECTPTR)
    v2 = varoftype(rclass.OBJECTPTR)
    v3 = varoftype(lltype.Bool)
    c0 = const(lltype.nullptr(rclass.OBJECT))
    #
    for opname, reducedname in [('ptr_eq', 'ptr_iszero'),
                                ('ptr_ne', 'ptr_nonzero')]:
        op = SpaceOperation(opname, [v1, v2], v3)
        op1 = Transformer().rewrite_operation(op)
        assert op1.opname == opname
        assert op1.args == [v1, v2]
        #
        op = SpaceOperation(opname, [v1, c0], v3)
        op1 = Transformer().rewrite_operation(op)
        assert op1.opname == reducedname
        assert op1.args == [v1]
        #
        op = SpaceOperation(opname, [c0, v2], v3)
        op1 = Transformer().rewrite_operation(op)
        assert op1.opname == reducedname
        assert op1.args == [v2]

def test_nongc_ptr_eq():
    v1 = varoftype(rclass.NONGCOBJECTPTR)
    v2 = varoftype(rclass.NONGCOBJECTPTR)
    v3 = varoftype(lltype.Bool)
    c0 = const(lltype.nullptr(rclass.NONGCOBJECT))
    #
    for opname, reducedname in [('ptr_eq', 'int_is_zero'),
                                ('ptr_ne', 'int_is_true')]:
        op = SpaceOperation(opname, [v1, v2], v3)
        op1 = Transformer().rewrite_operation(op)
        assert op1.opname == opname.replace('ptr_', 'int_')
        assert op1.args == [v1, v2]
        #
        op = SpaceOperation(opname, [v1, c0], v3)
        op1 = Transformer().rewrite_operation(op)
        assert op1.opname == reducedname
        assert op1.args == [v1]
        #
        op = SpaceOperation(opname, [c0, v2], v3)
        op1 = Transformer().rewrite_operation(op)
        assert op1.opname == reducedname
        assert op1.args == [v2]
    #
    op = SpaceOperation('ptr_iszero', [v1], v3)
    op1 = Transformer().rewrite_operation(op)
    assert op1.opname == 'int_is_zero'
    assert op1.args == [v1]
    #
    op = SpaceOperation('ptr_nonzero', [v1], v3)
    op1 = Transformer().rewrite_operation(op)
    assert op1.opname == 'int_is_true'
    assert op1.args == [v1]

def test_str_getinteriorarraysize():
    v = varoftype(lltype.Ptr(rstr.STR))
    v_result = varoftype(lltype.Signed)
    op = SpaceOperation('getinteriorarraysize',
                        [v, Constant('chars', lltype.Void)],
                        v_result)
    op1 = Transformer().rewrite_operation(op)
    assert op1.opname == 'strlen'
    assert op1.args == [v]
    assert op1.result == v_result

def test_unicode_getinteriorarraysize():
    v = varoftype(lltype.Ptr(rstr.UNICODE))
    v_result = varoftype(lltype.Signed)
    op = SpaceOperation('getinteriorarraysize',
                        [v, Constant('chars', lltype.Void)],
                        v_result)
    op1 = Transformer().rewrite_operation(op)
    assert op1.opname == 'unicodelen'
    assert op1.args == [v]
    assert op1.result == v_result

def test_str_getinteriorfield():
    v = varoftype(lltype.Ptr(rstr.STR))
    v_index = varoftype(lltype.Signed)
    v_result = varoftype(lltype.Char)
    op = SpaceOperation('getinteriorfield',
                        [v, Constant('chars', lltype.Void), v_index],
                        v_result)
    op1 = Transformer().rewrite_operation(op)
    assert op1.opname == 'strgetitem'
    assert op1.args == [v, v_index]
    assert op1.result == v_result

def test_unicode_getinteriorfield():
    v = varoftype(lltype.Ptr(rstr.UNICODE))
    v_index = varoftype(lltype.Signed)
    v_result = varoftype(lltype.UniChar)
    op = SpaceOperation('getinteriorfield',
                        [v, Constant('chars', lltype.Void), v_index],
                        v_result)
    op1 = Transformer().rewrite_operation(op)
    assert op1.opname == 'unicodegetitem'
    assert op1.args == [v, v_index]
    assert op1.result == v_result

def test_str_setinteriorfield():
    v = varoftype(lltype.Ptr(rstr.STR))
    v_index = varoftype(lltype.Signed)
    v_newchr = varoftype(lltype.Char)
    v_void = varoftype(lltype.Void)
    op = SpaceOperation('setinteriorfield',
                        [v, Constant('chars', lltype.Void), v_index, v_newchr],
                        v_void)
    op1 = Transformer().rewrite_operation(op)
    assert op1.opname == 'strsetitem'
    assert op1.args == [v, v_index, v_newchr]
    assert op1.result == v_void

def test_unicode_setinteriorfield():
    v = varoftype(lltype.Ptr(rstr.UNICODE))
    v_index = varoftype(lltype.Signed)
    v_newchr = varoftype(lltype.UniChar)
    v_void = varoftype(lltype.Void)
    op = SpaceOperation('setinteriorfield',
                        [v, Constant('chars', lltype.Void), v_index, v_newchr],
                        v_void)
    op1 = Transformer().rewrite_operation(op)
    assert op1.opname == 'unicodesetitem'
    assert op1.args == [v, v_index, v_newchr]
    assert op1.result == v_void

def test_promote_1():
    v1 = varoftype(lltype.Signed)
    v2 = varoftype(lltype.Signed)
    op = SpaceOperation('hint',
                        [v1, Constant({'promote': True}, lltype.Void)],
                        v2)
    oplist = Transformer().rewrite_operation(op)
    op0, op1, op2 = oplist
    assert op0.opname == '-live-'
    assert op0.args == []
    assert op1.opname == 'int_guard_value'
    assert op1.args == [v1]
    assert op1.result is None
    assert op2 is None

def test_promote_2():
    v1 = varoftype(lltype.Signed)
    v2 = varoftype(lltype.Signed)
    op = SpaceOperation('hint',
                        [v1, Constant({'promote': True}, lltype.Void)],
                        v2)
    returnblock = Block([varoftype(lltype.Signed)])
    returnblock.operations = ()
    block = Block([v1])
    block.operations = [op]
    block.closeblock(Link([v2], returnblock))
    Transformer().optimize_block(block)
    assert len(block.operations) == 2
    assert block.operations[0].opname == '-live-'
    assert block.operations[0].args == []
    assert block.operations[1].opname == 'int_guard_value'
    assert block.operations[1].args == [v1]
    assert block.operations[1].result is None
    assert block.exits[0].args == [v1]

def test_int_abs():
    v1 = varoftype(lltype.Signed)
    v2 = varoftype(lltype.Signed)
    op = SpaceOperation('int_abs', [v1], v2)
    tr = Transformer(FakeCPU(), FakeRegularCallControl())
    tr.graph = "somemaingraph"
    oplist = tr.rewrite_operation(op)
    assert oplist[0].opname == 'inline_call_ir_i'
    assert oplist[0].args[0] == 'somejitcode'

def test_str_newstr():
    c_STR = Constant(rstr.STR, lltype.Void)
    c_flavor = Constant({'flavor': 'gc'}, lltype.Void)
    v1 = varoftype(lltype.Signed)
    v2 = varoftype(lltype.Ptr(rstr.STR))
    op = SpaceOperation('malloc_varsize', [c_STR, c_flavor, v1], v2)
    op1 = Transformer().rewrite_operation(op)
    assert op1.opname == 'newstr'
    assert op1.args == [v1]
    assert op1.result == v2

def test_str_concat():
    # test that the oopspec is present and correctly transformed
    PSTR = lltype.Ptr(rstr.STR)
    FUNC = lltype.FuncType([PSTR, PSTR], PSTR)
    func = lltype.functionptr(FUNC, 'll_strconcat',
                              _callable=rstr.LLHelpers.ll_strconcat)
    v1 = varoftype(PSTR)
    v2 = varoftype(PSTR)
    v3 = varoftype(PSTR)
    op = SpaceOperation('direct_call', [const(func), v1, v2], v3)
    tr = Transformer(FakeCPU(), FakeBuiltinCallControl())
    op1 = tr.rewrite_operation(op)
    assert op1.opname == 'residual_call_r_r'
    assert op1.args[0].value == func
    assert op1.args[1] == 'calldescr-%d' % effectinfo.EffectInfo.OS_STR_CONCAT
    assert op1.args[2] == ListOfKind('ref', [v1, v2])
    assert op1.result == v3

def test_unicode_concat():
    # test that the oopspec is present and correctly transformed
    PSTR = lltype.Ptr(rstr.UNICODE)
    FUNC = lltype.FuncType([PSTR, PSTR], PSTR)
    func = lltype.functionptr(FUNC, 'll_strconcat',
                              _callable=rstr.LLHelpers.ll_strconcat)
    v1 = varoftype(PSTR)
    v2 = varoftype(PSTR)
    v3 = varoftype(PSTR)
    op = SpaceOperation('direct_call', [const(func), v1, v2], v3)
    tr = Transformer(FakeCPU(), FakeBuiltinCallControl())
    op1 = tr.rewrite_operation(op)
    assert op1.opname == 'residual_call_r_r'
    assert op1.args[0].value == func
    assert op1.args[1] == 'calldescr-%d' % effectinfo.EffectInfo.OS_UNI_CONCAT
    assert op1.args[2] == ListOfKind('ref', [v1, v2])
    assert op1.result == v3
    #
    # check the callinfo_for_oopspec
    got = effectinfo.callinfo_for_oopspec(effectinfo.EffectInfo.OS_UNI_CONCAT)
    assert got[0] == op1.args[1]    # the calldescr
    assert heaptracker.int2adr(got[1]) == llmemory.cast_ptr_to_adr(func)

def test_str_slice():
    # test that the oopspec is present and correctly transformed
    PSTR = lltype.Ptr(rstr.STR)
    INT = lltype.Signed
    FUNC = lltype.FuncType([PSTR, INT, INT], PSTR)
    func = lltype.functionptr(FUNC, '_ll_stringslice',
                            _callable=rstr.LLHelpers._ll_stringslice)
    v1 = varoftype(PSTR)
    v2 = varoftype(INT)
    v3 = varoftype(INT)
    v4 = varoftype(PSTR)
    op = SpaceOperation('direct_call', [const(func), v1, v2, v3], v4)
    tr = Transformer(FakeCPU(), FakeBuiltinCallControl())
    op1 = tr.rewrite_operation(op)
    assert op1.opname == 'residual_call_ir_r'
    assert op1.args[0].value == func
    assert op1.args[1] == 'calldescr-%d' % effectinfo.EffectInfo.OS_STR_SLICE
    assert op1.args[2] == ListOfKind('int', [v2, v3])
    assert op1.args[3] == ListOfKind('ref', [v1])
    assert op1.result == v4

def test_unicode_slice():
    # test that the oopspec is present and correctly transformed
    PUNICODE = lltype.Ptr(rstr.UNICODE)
    INT = lltype.Signed
    FUNC = lltype.FuncType([PUNICODE, INT, INT], PUNICODE)
    func = lltype.functionptr(FUNC, '_ll_stringslice',
                            _callable=rstr.LLHelpers._ll_stringslice)
    v1 = varoftype(PUNICODE)
    v2 = varoftype(INT)
    v3 = varoftype(INT)
    v4 = varoftype(PUNICODE)
    op = SpaceOperation('direct_call', [const(func), v1, v2, v3], v4)
    tr = Transformer(FakeCPU(), FakeBuiltinCallControl())
    op1 = tr.rewrite_operation(op)
    assert op1.opname == 'residual_call_ir_r'
    assert op1.args[0].value == func
    assert op1.args[1] == 'calldescr-%d' % effectinfo.EffectInfo.OS_UNI_SLICE
    assert op1.args[2] == ListOfKind('int', [v2, v3])
    assert op1.args[3] == ListOfKind('ref', [v1])
    assert op1.result == v4

def test_list_ll_arraycopy():
    from pypy.rlib.rgc import ll_arraycopy
    LIST = lltype.GcArray(lltype.Signed)
    PLIST = lltype.Ptr(LIST)
    INT = lltype.Signed
    FUNC = lltype.FuncType([PLIST]*2+[INT]*3, lltype.Void)
    func = lltype.functionptr(FUNC, 'll_arraycopy', _callable=ll_arraycopy)
    v1 = varoftype(PLIST)
    v2 = varoftype(PLIST)
    v3 = varoftype(INT)
    v4 = varoftype(INT)
    v5 = varoftype(INT)
    v6 = varoftype(lltype.Void)
    op = SpaceOperation('direct_call', [const(func), v1, v2, v3, v4, v5], v6)
    tr = Transformer(FakeCPU(), FakeBuiltinCallControl())
    op1 = tr.rewrite_operation(op)
    assert op1.opname == 'residual_call_ir_v'
    assert op1.args[0].value == func
    assert op1.args[1] == 'calldescr-%d' % effectinfo.EffectInfo.OS_ARRAYCOPY
    assert op1.args[2] == ListOfKind('int', [v3, v4, v5])
    assert op1.args[3] == ListOfKind('ref', [v1, v2])
