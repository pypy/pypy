import py
py.test.skip("JIT disabled for now")
from pypy.rpython.lltypesystem import lltype
from pypy.jit.hintannotator.annotator import HintAnnotatorPolicy
from pypy.jit.timeshifter import rvalue
from pypy.jit.timeshifter.test.test_timeshift import Whatever
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests
from pypy.jit.codegen.model import GenVar
from pypy.jit.codegen.llgraph.rgenop import rgenop
from pypy.module.pypyjit.newbool import NewBoolDesc


class DummyDesc(NewBoolDesc):
    def __init__(self):
        self.boolkind = rgenop.kindToken(lltype.Bool)
        self.boolboxes = [rvalue.redbox_from_prebuilt_value(rgenop, False),
                          rvalue.redbox_from_prebuilt_value(rgenop, True)]

desc = DummyDesc()


class DummyJITState:
    def __init__(self):
        self.curbuilder = DummyBuilder()


class DummyBuilder:
    def __init__(self):
        self.operations = []

    def genop1(self, opname, gv_arg):
        gv_res = GenVar()
        self.operations.append((opname, gv_arg, gv_res))
        return gv_res

    def genop2(self, opname, gv_arg1, gv_arg2):
        gv_res = GenVar()
        self.operations.append((opname, gv_arg1, gv_arg2, gv_res))
        return gv_res


def test_getboolbox():
    for b1 in [False, True]:
        for b2 in [False, True]:
            jitstate = DummyJITState()
            box = desc.getboolbox(jitstate, rgenop.genconst(b1), b2)
            assert box.genvar.revealconst(lltype.Bool) == b1 ^ b2
            assert not jitstate.curbuilder.operations

    gv1 = GenVar()
    jitstate = DummyJITState()
    box = desc.getboolbox(jitstate, gv1, False)
    assert box.genvar == gv1
    assert not jitstate.curbuilder.operations

    jitstate = DummyJITState()
    box = desc.getboolbox(jitstate, gv1, True)
    assert jitstate.curbuilder.operations == [
        ("bool_not", gv1, box.genvar),
        ]

def test_genbooleq():
    gv1 = GenVar()
    gv2 = GenVar()
    gf = rgenop.genconst(False)
    gt = rgenop.genconst(True)

    for b1 in [False, True]:
        for b2 in [False, True]:
            for rev in [False, True]:
                jitstate = DummyJITState()
                box = desc.genbooleq(jitstate,
                                     rgenop.genconst(b1),
                                     rgenop.genconst(b2),
                                     rev)
                assert box.genvar.revealconst(lltype.Bool) == (b1 == b2) ^ rev
                assert not jitstate.curbuilder.operations

    for b2 in [False, True]:
        for rev in [False, True]:
            for flip in [False, True]:
                jitstate = DummyJITState()
                args = [gv1, rgenop.genconst(b2), rev]
                if flip:
                    args[0], args[1] = args[1], args[0]
                box = desc.genbooleq(jitstate, *args)

                should_neg = (b2 == rev)
                if should_neg:
                    assert jitstate.curbuilder.operations == [
                        ("bool_not", gv1, box.genvar),
                        ]
                else:
                    assert box.genvar == gv1
                    assert not jitstate.curbuilder.operations

    for rev in [False, True]:
        jitstate = DummyJITState()
        box = desc.genbooleq(jitstate, gv1, gv2, rev)
        ops = jitstate.curbuilder.operations
        _, _, gvi1 = ops[0]
        _, _, gvi2 = ops[1]
        assert ops == [
            ("cast_bool_to_int", gv1, gvi1),
            ("cast_bool_to_int", gv2, gvi2),
            (["int_eq", "int_ne"][rev], gvi1, gvi2, box.genvar),
            ]

# ____________________________________________________________

from pypy.objspace.std.boolobject import W_BoolObject
from pypy.interpreter.baseobjspace import W_Root

def newbool(space, flag):
    if flag:
        return W_BoolObject.w_True
    else:
        return W_BoolObject.w_False

class MyPolicy(HintAnnotatorPolicy):
    novirtualcontainer = True
    def look_inside_graph(self, graph):
        if graph.func is newbool:
            return NewBoolDesc
        else:
            return True


class TestNewBool(TimeshiftingTests):

    def test_simple(self):
        def f(n):
            w_res = newbool(None, n > 5)
            return int(w_res.boolval)

        res = self.timeshift(f, [7], policy=MyPolicy())
        assert res == 1
        self.check_insns({'int_gt': 1, 'cast_bool_to_int': 1})

    def test_ptreq1(self):
        def f(n):
            w_res = newbool(None, n > 5)
            return int(w_res is W_BoolObject.w_True)

        res = self.timeshift(f, [3], policy=MyPolicy())
        assert res == 0
        self.check_insns({'int_gt': 1, 'cast_bool_to_int': 1})

    def test_ptreq2(self):
        def f(n):
            w_res = newbool(None, n > 5)
            return int(w_res is W_BoolObject.w_False)

        res = self.timeshift(f, [3], policy=MyPolicy())
        assert res == 1
        self.check_insns({'int_gt': 1, 'bool_not': 1, 'cast_bool_to_int': 1})

    def test_force(self):
        def f(n):
            w_res = newbool(None, n > 5)
            return w_res
        f.convert_result = lambda res: 'foo'

        res = self.timeshift(f, [3], policy=MyPolicy())
        self.check_insns({'int_gt': 1,
                          'cast_bool_to_int': 1, 'getarrayitem': 1,
                          'cast_pointer': Whatever()})

    def test_merge_bools(self):
        def f(n):
            if n > 5:
                w_res = newbool(None, n >= 10)
            else:
                w_res = newbool(None, n < -10)
            return int(w_res.boolval)

        res = self.timeshift(f, [-3], policy=MyPolicy())
        assert res == 0
        self.check_insns({'int_gt': 1, 'int_ge': 1, 'int_lt': 1,
                          'cast_bool_to_int': 1})

    def test_merge_with_virtual_root(self):
        def f(n):
            if n > 5:
                w_res = newbool(None, n >= 10)
            else:
                w_res = W_Root()
            return w_res
        f.convert_result = lambda res: 'foo'

        res = self.timeshift(f, [-3], policy=MyPolicy())
        self.check_insns({'int_gt': 1, 'int_ge': 1,
                          'cast_bool_to_int': 1, 'getarrayitem': 1,
                          'malloc': 1, 'setfield': 1,
                          'cast_pointer': Whatever()})

    def test_ptreq3(self):
        def f(n):
            w1 = newbool(None, n >= 10)
            w2 = W_Root()
            return int(w1 is w2) + int(w2 is w1)

        res = self.timeshift(f, [123], policy=MyPolicy())
        assert res == 0
        self.check_insns({'int_ge': 1})

    def test_ptreq4(self):
        w2 = W_Root()

        def f(n):
            w1 = newbool(None, n >= 10)
            return int(w1 is w2) + int(w2 is w1)

        res = self.timeshift(f, [123], policy=MyPolicy())
        assert res == 0
        self.check_insns({'int_ge': 1})
