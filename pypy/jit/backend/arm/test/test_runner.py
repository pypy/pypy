import py
from pypy.jit.backend.arm.runner import ArmCPU
from pypy.jit.backend.test.runner_test import LLtypeBackendTest, \
                                                boxfloat, \
                                                constfloat
from pypy.jit.backend.arm.test.support import skip_unless_arm
from pypy.jit.metainterp.history import (AbstractFailDescr,
                                         AbstractDescr,
                                         BasicFailDescr,
                                         BoxInt, Box, BoxPtr,
                                         LoopToken,
                                         ConstInt, ConstPtr,
                                         BoxObj, Const,
                                         ConstObj, BoxFloat, ConstFloat)
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.tool.oparser import parse
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.annlowlevel import llhelper
from pypy.jit.codewriter.effectinfo import EffectInfo

skip_unless_arm()

class FakeStats(object):
    pass

class TestARM(LLtypeBackendTest):

    def setup_class(cls):
        cls.cpu = ArmCPU(rtyper=None, stats=FakeStats())
        cls.cpu.setup_once()

    # for the individual tests see
    # ====> ../../test/runner_test.py
    def test_result_is_spilled(self):
        cpu = self.cpu
        inp = [BoxInt(i) for i in range(1, 15)]
        out = [BoxInt(i) for i in range(1, 15)]
        looptoken = LoopToken()
        operations = [
            ResOperation(rop.INT_ADD, [inp[0] , inp[1]], out[0]),
            ResOperation(rop.INT_ADD, [inp[2] , inp[3]], out[1]),
            ResOperation(rop.INT_ADD, [inp[4] , inp[5]], out[2]),
            ResOperation(rop.INT_ADD, [inp[6] , inp[7]], out[3]),
            ResOperation(rop.INT_ADD, [inp[8] , inp[9]], out[4]),
            ResOperation(rop.INT_ADD, [inp[10], inp[11]], out[5]),
            ResOperation(rop.INT_ADD, [inp[12], inp[13]], out[6]),
            ResOperation(rop.INT_ADD, [inp[0] , inp[1]], out[7]),
            ResOperation(rop.INT_ADD, [inp[2] , inp[3]], out[8]),
            ResOperation(rop.INT_ADD, [inp[4] , inp[5]], out[9]),
            ResOperation(rop.INT_ADD, [inp[6] , inp[7]], out[10]),
            ResOperation(rop.INT_ADD, [inp[8] , inp[9]], out[11]),
            ResOperation(rop.INT_ADD, [inp[10], inp[11]], out[12]),
            ResOperation(rop.INT_ADD, [inp[12], inp[13]], out[13]),
            ResOperation(rop.FINISH, out, None, descr=BasicFailDescr(1)),
            ]
        cpu.compile_loop(inp, operations, looptoken)
        for i in range(1, 15):
            self.cpu.set_future_value_int(i-1, i)
        res = self.cpu.execute_token(looptoken)
        output = [self.cpu.get_latest_value_int(i-1) for i in range(1, 15)]
        expected = [3, 7, 11, 15, 19, 23, 27, 3, 7, 11, 15, 19, 23, 27]
        assert output == expected

    def test_redirect_call_assember2(self):
        called = []
        def assembler_helper(failindex, virtualizable):
            return self.cpu.get_latest_value_int(0)

        FUNCPTR = lltype.Ptr(lltype.FuncType([lltype.Signed, llmemory.GCREF],
                                             lltype.Signed))
        class FakeJitDriverSD:
            index_of_virtualizable = -1
            _assembler_helper_ptr = llhelper(FUNCPTR, assembler_helper)
            assembler_helper_adr = llmemory.cast_ptr_to_adr(
                _assembler_helper_ptr)
        FakeJitDriverSD.portal_calldescr = self.cpu.calldescrof(
            lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Signed)),
                [lltype.Signed], lltype.Signed, EffectInfo.MOST_GENERAL)
        lt1, lt2, lt3 = [LoopToken() for x in range(3)]
        lt2.outermost_jitdriver_sd = FakeJitDriverSD()
        loop1 = parse('''
        [i0]
        i1 = call_assembler(i0, descr=lt2)
        guard_not_forced()[]
        finish(i1)
        ''', namespace=locals())
        loop2 = parse('''
        [i0]
        i1 = int_add(i0, 1)
        finish(i1)
        ''')
        loop3 = parse('''
        [i0]
        i1 = int_sub(i0, 1)
        finish(i1)
        ''')
        self.cpu.compile_loop(loop2.inputargs, loop2.operations, lt2)
        self.cpu.compile_loop(loop3.inputargs, loop3.operations, lt3)
        self.cpu.compile_loop(loop1.inputargs, loop1.operations, lt1)
        self.cpu.set_future_value_int(0, 11)
        res = self.cpu.execute_token(lt1)
        assert self.cpu.get_latest_value_int(0) == 12

        self.cpu.redirect_call_assembler(lt2, lt3)
        self.cpu.set_future_value_int(0, 11)
        res = self.cpu.execute_token(lt1)
        assert self.cpu.get_latest_value_int(0) == 10

    def test_new_array_with_const_length(self):
        """ Test for an issue with malloc_varsize when the size is an imm
        that gets lost around the call to malloc"""
        A = lltype.GcArray(lltype.Signed)
        arraydescr = self.cpu.arraydescrof(A)
        r1 = self.execute_operation(rop.NEW_ARRAY, [ConstInt(6)],
                                    'ref', descr=arraydescr)
        a = lltype.cast_opaque_ptr(lltype.Ptr(A), r1.value)
        assert a[0] == 0
        assert len(a) == 6

    def test_cond_call_gc_wb_array_card_marking_fast_path(self):
        py.test.skip('ignore this fast path for now')

    SFloat = lltype.GcForwardReference()
    SFloat.become(lltype.GcStruct('SFloat', ('parent', rclass.OBJECT),
          ('v1', lltype.Signed), ('v2', lltype.Signed),
          ('v3', lltype.Signed), ('v4', lltype.Signed),
          ('v5', lltype.Signed), ('v6', lltype.Signed),
          ('v7', lltype.Signed), ('v8', lltype.Signed),
          ('v9', lltype.Signed), ('v10', lltype.Signed),
          ('v11', lltype.Signed), ('v12', lltype.Signed),
          ('v13', lltype.Signed), ('v14', lltype.Signed),
          ('v15', lltype.Signed), ('v16', lltype.Signed),
          ('v17', lltype.Signed), ('v18', lltype.Signed),
          ('v19', lltype.Signed), ('v20', lltype.Signed),

          ('w1', lltype.Signed), ('w2', lltype.Signed),
          ('w3', lltype.Signed), ('w4', lltype.Signed),
          ('w5', lltype.Signed), ('w6', lltype.Signed),
          ('w7', lltype.Signed), ('w8', lltype.Signed),
          ('w9', lltype.Signed), ('w10', lltype.Signed),
          ('w11', lltype.Signed), ('w12', lltype.Signed),
          ('w13', lltype.Signed), ('w14', lltype.Signed),
          ('w15', lltype.Signed), ('w16', lltype.Signed),
          ('w17', lltype.Signed), ('w18', lltype.Signed),
          ('w19', lltype.Signed), ('w20', lltype.Signed),

          ('x1', lltype.Signed), ('x2', lltype.Signed),
          ('x3', lltype.Signed), ('x4', lltype.Signed),
          ('x5', lltype.Signed), ('x6', lltype.Signed),
          ('x7', lltype.Signed), ('x8', lltype.Signed),
          ('x9', lltype.Signed), ('x10', lltype.Signed),
          ('x11', lltype.Signed), ('x12', lltype.Signed),
          ('x13', lltype.Signed), ('x14', lltype.Signed),
          ('x15', lltype.Signed), ('x16', lltype.Signed),
          ('x17', lltype.Signed), ('x18', lltype.Signed),
          ('x19', lltype.Signed), ('x20', lltype.Signed),

          ('y1', lltype.Signed), ('y2', lltype.Signed),
          ('y3', lltype.Signed), ('y4', lltype.Signed),
          ('y5', lltype.Signed), ('y6', lltype.Signed),
          ('y7', lltype.Signed), ('y8', lltype.Signed),
          ('y9', lltype.Signed), ('y10', lltype.Signed),
          ('y11', lltype.Signed), ('y12', lltype.Signed),
          ('y13', lltype.Signed), ('y14', lltype.Signed),
          ('y15', lltype.Signed), ('y16', lltype.Signed),
          ('y17', lltype.Signed), ('y18', lltype.Signed),
          ('y19', lltype.Signed), ('y20', lltype.Signed),
          ('float', lltype.Float)))

    TFloat = lltype.GcStruct('TFloat', ('parent', SFloat),
                             ('next', lltype.Ptr(SFloat)))
    def test_float_field(self):
        if not self.cpu.supports_floats:
            py.test.skip('requires floats')
        floatdescr = self.cpu.fielddescrof(self.SFloat, 'float')
        t_box, T_box = self.alloc_instance(self.TFloat)
        self.execute_operation(rop.SETFIELD_GC, [t_box, boxfloat(3.4)],
                               'void', descr=floatdescr)
        res = self.execute_operation(rop.GETFIELD_GC, [t_box],
                                     'float', descr=floatdescr)
        assert res.getfloat() == 3.4
        #
        self.execute_operation(rop.SETFIELD_GC, [t_box, constfloat(-3.6)],
                               'void', descr=floatdescr)
        res = self.execute_operation(rop.GETFIELD_GC, [t_box],
                                     'float', descr=floatdescr)
        assert res.getfloat() == -3.6
