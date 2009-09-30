
import py, sys, random
from pypy.jit.metainterp.history import (AbstractFailDescr,
                                         BasicFailDescr,
                                         BoxInt, Box, BoxPtr,
                                         LoopToken,
                                         ConstInt, ConstPtr,
                                         BoxObj, Const,
                                         ConstObj, BoxFloat, ConstFloat)
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.typesystem import deref
from pypy.rpython.lltypesystem import lltype, llmemory, rstr, rffi, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.executor import execute
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.jit.metainterp.test.oparser import parse
from pypy.rpython.annlowlevel import llhelper
from pypy.rpython.llinterp import LLException

class Runner(object):

    def execute_operation(self, opname, valueboxes, result_type, descr=None):
        inputargs, operations = self._get_single_operation_list(opname,
                                                                result_type,
                                                                valueboxes,
                                                                descr)
        executable_token = self.cpu.compile_loop(inputargs, operations)
        j = 0
        for box in valueboxes:
            if isinstance(box, BoxInt):
                self.cpu.set_future_value_int(j, box.getint())
                j += 1
            elif isinstance(box, (BoxPtr, BoxObj)):
                self.cpu.set_future_value_ref(j, box.getref_base())
                j += 1
            elif isinstance(box, BoxFloat):
                self.cpu.set_future_value_float(j, box.getfloat())
                j += 1
            else:
                assert isinstance(box, Const)
        res = self.cpu.execute_token(executable_token)
        if res is operations[-1].descr:
            self.guard_failed = False
        else:
            self.guard_failed = True
        if result_type == 'int':
            return BoxInt(self.cpu.get_latest_value_int(0))
        elif result_type == 'ref':
            return BoxPtr(self.cpu.get_latest_value_ref(0))
        elif result_type == 'float':
            return BoxFloat(self.cpu.get_latest_value_float(0))
        elif result_type == 'void':
            return None
        else:
            assert False

    def _get_single_operation_list(self, opnum, result_type, valueboxes,
                                   descr):
        if result_type == 'void':
            result = None
        elif result_type == 'int':
            result = BoxInt()
        elif result_type == 'ref':
            result = BoxPtr()
        elif result_type == 'float':
            result = BoxFloat()
        else:
            raise ValueError(result_type)
        if result is None:
            results = []
        else:
            results = [result]
        operations = [ResOperation(opnum, valueboxes, result),
                      ResOperation(rop.FINISH, results, None,
                                   descr=BasicFailDescr())]
        if operations[0].is_guard():
            operations[0].fail_args = []
            if not descr:
                descr = BasicFailDescr()
        operations[0].descr = descr
        inputargs = []
        for box in valueboxes:
            if isinstance(box, Box):
                assert box not in inputargs, "repeated box!"
                inputargs.append(box)
        return inputargs, operations

class BaseBackendTest(Runner):

    def test_compile_linear_loop(self):
        i0 = BoxInt()
        i1 = BoxInt()
        faildescr = BasicFailDescr()
        operations = [
            ResOperation(rop.INT_ADD, [i0, ConstInt(1)], i1),
            ResOperation(rop.FINISH, [i1], None, descr=faildescr)
            ]
        inputargs = [i0]
        executable_token = self.cpu.compile_loop(inputargs, operations)
        self.cpu.set_future_value_int(0, 2)
        fail = self.cpu.execute_token(executable_token)
        res = self.cpu.get_latest_value_int(0)
        assert res == 3        
        assert fail is faildescr

    def test_compile_loop(self):
        i0 = BoxInt()
        i1 = BoxInt()
        i2 = BoxInt()
        faildescr = BasicFailDescr()
        operations = [
            ResOperation(rop.INT_ADD, [i0, ConstInt(1)], i1),
            ResOperation(rop.INT_LE, [i1, ConstInt(9)], i2),
            ResOperation(rop.GUARD_TRUE, [i2], None, descr=faildescr),
            ResOperation(rop.JUMP, [i1], None),
            ]
        inputargs = [i0]
        operations[2].fail_args = [i1]
        operations[-1].jump_target = None
        
        executable_token = self.cpu.compile_loop(inputargs, operations)
        self.cpu.set_future_value_int(0, 2)
        fail = self.cpu.execute_token(executable_token)
        assert fail is faildescr
        res = self.cpu.get_latest_value_int(0)
        assert res == 10

    def test_backends_dont_keep_loops_alive(self):
        import weakref, gc
        self.cpu.dont_keepalive_stuff = True
        i0 = BoxInt()
        i1 = BoxInt()
        i2 = BoxInt()
        faildescr = BasicFailDescr()                
        operations = [
            ResOperation(rop.INT_ADD, [i0, ConstInt(1)], i1),
            ResOperation(rop.INT_LE, [i1, ConstInt(9)], i2),
            ResOperation(rop.GUARD_TRUE, [i2], None, descr=faildescr),
            ResOperation(rop.JUMP, [i1], None),
            ]
        inputargs = [i0]
        operations[2].fail_args = [i1]
        operations[-1].jump_target = None
        wr_i1 = weakref.ref(i1)
        wr_guard = weakref.ref(operations[2])
        executable_token = self.cpu.compile_loop(inputargs, operations)
        del i0, i1, i2
        del inputargs
        del operations
        gc.collect()
        assert not wr_i1() and not wr_guard()

    def test_compile_bridge(self):
        i0 = BoxInt()
        i1 = BoxInt()
        i2 = BoxInt()
        faildescr1 = BasicFailDescr()
        faildescr2 = BasicFailDescr()
        operations = [
            ResOperation(rop.INT_ADD, [i0, ConstInt(1)], i1),
            ResOperation(rop.INT_LE, [i1, ConstInt(9)], i2),
            ResOperation(rop.GUARD_TRUE, [i2], None, descr=faildescr1),
            ResOperation(rop.JUMP, [i1], None),
            ]
        inputargs = [i0]
        operations[2].fail_args = [i1]
        operations[-1].jump_target = None       
        executable_token = self.cpu.compile_loop(inputargs, operations)
        loop_token = LoopToken()
        loop_token.executable_token = executable_token

        i1b = BoxInt()
        i3 = BoxInt()
        bridge = [
            ResOperation(rop.INT_LE, [i1b, ConstInt(19)], i3),
            ResOperation(rop.GUARD_TRUE, [i3], None, descr=faildescr2),
            ResOperation(rop.JUMP, [i1b], None),            
        ]
        bridge[1].fail_args = [i1b]
        bridge[-1].jump_target = loop_token

        self.cpu.compile_bridge(faildescr1, [i1b], bridge)        

        self.cpu.set_future_value_int(0, 2)
        fail = self.cpu.execute_token(executable_token)
        assert fail is faildescr2
        res = self.cpu.get_latest_value_int(0)
        assert res == 20

    def test_finish(self):
        i0 = BoxInt()
        class UntouchableFailDescr(AbstractFailDescr):
            def __setattr__(self, name, value):
                py.test.fail("finish descrs should not be touched")
        faildescr = UntouchableFailDescr() # to check that is not touched
        operations = [
            ResOperation(rop.FINISH, [i0], None, descr=faildescr)
            ]
        executable_token = self.cpu.compile_loop([i0], operations)
        self.cpu.set_future_value_int(0, 99)
        fail = self.cpu.execute_token(executable_token)
        assert fail is faildescr
        res = self.cpu.get_latest_value_int(0)
        assert res == 99

        operations = [
            ResOperation(rop.FINISH, [ConstInt(42)], None, descr=faildescr)
            ]
        executable_token = self.cpu.compile_loop([], operations)
        fail = self.cpu.execute_token(executable_token)
        assert fail is faildescr        
        res = self.cpu.get_latest_value_int(0)
        assert res == 42

        operations = [
            ResOperation(rop.FINISH, [], None, descr=faildescr)
            ]
        executable_token = self.cpu.compile_loop([], operations)
        fail = self.cpu.execute_token(executable_token)
        assert fail is faildescr
        
    def test_do_call(self):
        cpu = self.cpu
        #
        def func(c):
            return chr(ord(c) + 1)
        FPTR = self.Ptr(self.FuncType([lltype.Char], lltype.Char))
        func_ptr = llhelper(FPTR, func)
        calldescr = cpu.calldescrof(deref(FPTR), (lltype.Char,), lltype.Char)
        x = cpu.do_call(
            [self.get_funcbox(cpu, func_ptr),
             BoxInt(ord('A'))],
            calldescr)
        assert x.value == ord('B')

    def test_call(self):

        def func_int(a, b):
            return a + b
        def func_char(c, c1):
            return chr(ord(c) + ord(c1))

        functions = [
            (func_int, lltype.Signed, 655360),
            (func_int, rffi.SHORT, 1213),
            (func_char, lltype.Char, 12)
            ]

        for func, TP, num in functions:
            cpu = self.cpu
            #
            FPTR = self.Ptr(self.FuncType([TP, TP], TP))
            func_ptr = llhelper(FPTR, func)
            FUNC = deref(FPTR)
            calldescr = cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)
            funcbox = self.get_funcbox(cpu, func_ptr)
            res = self.execute_operation(rop.CALL,
                                         [funcbox, BoxInt(num), BoxInt(num)],
                                         'int', descr=calldescr)
            assert res.value == 2 * num

    def test_lshift(self):
        res = execute(self.cpu, rop.INT_LSHIFT, None, BoxInt(10), ConstInt(4))
        assert res.value == 10 << 4
        res = self.execute_operation(rop.INT_LSHIFT, [BoxInt(10), BoxInt(4)],
                                     'int')
        assert res.value == 10 << 4
        res = self.execute_operation(rop.INT_LSHIFT, [BoxInt(-10), BoxInt(4)],
                                     'int')
        assert res.value == -10 << 4

    def test_uint_rshift(self):
        res = self.execute_operation(rop.UINT_RSHIFT, [BoxInt(-1), BoxInt(4)],
                                     'int')
        assert res.value == intmask(r_uint(-1) >> r_uint(4))
        res = self.execute_operation(rop.UINT_RSHIFT, [BoxInt(1), BoxInt(4)],
                                     'int')
        assert res.value == intmask(r_uint(1) >> r_uint(4))

    def test_binary_operations(self):
        minint = -sys.maxint-1
        for opnum, testcases in [
            (rop.INT_ADD, [(10, -2, 8)]),
            (rop.INT_SUB, [(10, -2, 12)]),
            (rop.INT_MUL, [(-6, -3, 18)]),
            (rop.INT_FLOORDIV, [(110, 3, 36),
                                (-110, 3, -36),
                                (110, -3, -36),
                                (-110, -3, 36),
                                (-110, -1, 110),
                                (minint, 1, minint)]),
            (rop.INT_MOD, [(11, 3, 2),
                           (-11, 3, -2),
                           (11, -3, 2),
                           (-11, -3, -2)]),
            (rop.INT_AND, [(0xFF00, 0x0FF0, 0x0F00)]),
            (rop.INT_OR, [(0xFF00, 0x0FF0, 0xFFF0)]),
            (rop.INT_XOR, [(0xFF00, 0x0FF0, 0xF0F0)]),
            (rop.INT_LSHIFT, [(-5, 2, -20),
                              (-5, 0, -5)]),
            (rop.INT_RSHIFT, [(-17, 2, -5),
                              (19, 1, 9)]),
            ]:
            for x, y, z in testcases:
                res = self.execute_operation(opnum, [BoxInt(x), BoxInt(y)],
                                             'int')
                assert res.value == z

    def test_compare_operations(self):
        random_numbers = [-sys.maxint-1, -1, 0, 1, sys.maxint]
        def pick():
            r = random.randrange(-99999, 100000)
            if r & 1:
                return r
            else:
                return random_numbers[r % len(random_numbers)]
        minint = -sys.maxint-1
        for opnum, operation in [
            (rop.INT_LT, lambda x, y: x <  y),
            (rop.INT_LE, lambda x, y: x <= y),
            (rop.INT_EQ, lambda x, y: x == y),
            (rop.INT_NE, lambda x, y: x != y),
            (rop.INT_GT, lambda x, y: x >  y),
            (rop.INT_GE, lambda x, y: x >= y),
            (rop.UINT_LT, lambda x, y: r_uint(x) <  r_uint(y)),
            (rop.UINT_LE, lambda x, y: r_uint(x) <= r_uint(y)),
            (rop.UINT_GT, lambda x, y: r_uint(x) >  r_uint(y)),
            (rop.UINT_GE, lambda x, y: r_uint(x) >= r_uint(y)),
            ]:
            for i in range(20):
                x = pick()
                y = pick()
                res = self.execute_operation(opnum, [BoxInt(x), BoxInt(y)],
                                             'int')
                z = int(operation(x, y))
                assert res.value == z

    def test_unary_operations(self):
        minint = -sys.maxint-1
        for opnum, testcases in [
            (rop.INT_IS_TRUE, [(0, 0), (1, 1), (2, 1), (-1, 1), (minint, 1)]),
            (rop.INT_NEG, [(0, 0), (123, -123), (-23127, 23127)]),
            (rop.INT_INVERT, [(0, ~0), (-1, ~(-1)), (123, ~123)]),
            (rop.BOOL_NOT, [(0, 1), (1, 0)]),
            ]:
            for x, y in testcases:
                res = self.execute_operation(opnum, [BoxInt(x)],
                                             'int')
                assert res.value == y

    def test_float_operations(self):
        from pypy.jit.metainterp.test.test_executor import get_float_tests
        for opnum, boxargs, rettype, retvalue in get_float_tests(self.cpu):
            if len(boxargs) == 2:
                args_variants = [(boxargs[0], boxargs[1]),
                                 (boxargs[0], boxargs[1].constbox()),
                                 (boxargs[0].constbox(), boxargs[1])]
            else:
                args_variants = [boxargs]
            for argboxes in args_variants:
                res = self.execute_operation(opnum, argboxes, rettype)
                assert res.value == retvalue

    def test_ovf_operations(self, reversed=False):
        minint = -sys.maxint-1
        boom = 'boom'
        for opnum, testcases in [
            (rop.INT_ADD_OVF, [(10, -2, 8),
                               (-1, minint, boom),
                               (sys.maxint//2, sys.maxint//2+2, boom)]),
            (rop.INT_SUB_OVF, [(-20, -23, 3),
                               (-2, sys.maxint, boom),
                               (sys.maxint//2, -(sys.maxint//2+2), boom)]),
            (rop.INT_MUL_OVF, [(minint/2, 2, minint),
                               (-2, -(minint/2), minint),
                               (minint/2, -2, boom)]),
            ]:
            v1 = BoxInt(testcases[0][0])
            v2 = BoxInt(testcases[0][1])
            v_res = BoxInt()
            #
            if not reversed:
                ops = [
                    ResOperation(opnum, [v1, v2], v_res),
                    ResOperation(rop.GUARD_NO_OVERFLOW, [], None,
                                 descr=BasicFailDescr()),
                    ResOperation(rop.FINISH, [v_res], None,
                                 descr=BasicFailDescr()),
                    ]
                ops[1].fail_args = []
            else:
                v_exc = self.cpu.ts.BoxRef()
                ops = [
                    ResOperation(opnum, [v1, v2], v_res),
                    ResOperation(rop.GUARD_OVERFLOW, [], None,
                                 descr=BasicFailDescr()),
                    ResOperation(rop.FINISH, [], None, descr=BasicFailDescr()),
                    ]
                ops[1].fail_args = [v_res]
            #
            executable_token = self.cpu.compile_loop([v1, v2], ops)
            for x, y, z in testcases:
                assert not self.cpu.get_exception()
                assert not self.cpu.get_exc_value()
                self.cpu.set_future_value_int(0, x)
                self.cpu.set_future_value_int(1, y)
                fail = self.cpu.execute_token(executable_token)
                if (z == boom) ^ reversed:
                    assert fail is ops[1].descr
                else:
                    assert fail is ops[-1].descr
                if z != boom:
                    assert self.cpu.get_latest_value_int(0) == z
                assert not self.cpu.get_exception()
                assert not self.cpu.get_exc_value()

    def test_ovf_operations_reversed(self):
        self.test_ovf_operations(reversed=True)

    def test_field_basic(self):
        t_box, T_box = self.alloc_instance(self.T)
        fielddescr = self.cpu.fielddescrof(self.S, 'value')
        assert not fielddescr.is_pointer_field()
        #
        self.cpu.do_setfield_gc(t_box, BoxInt(1333), fielddescr)
        r = self.cpu.do_getfield_gc(t_box, fielddescr)
        assert r.value == 1333
        #
        res = self.execute_operation(rop.SETFIELD_GC, [t_box, BoxInt(39082)],
                                     'void', descr=fielddescr)
        assert res is None
        res = self.execute_operation(rop.GETFIELD_GC, [t_box],
                                     'int', descr=fielddescr)
        assert res.value == 39082
        #
        fielddescr1 = self.cpu.fielddescrof(self.S, 'chr1')
        fielddescr2 = self.cpu.fielddescrof(self.S, 'chr2')
        shortdescr = self.cpu.fielddescrof(self.S, 'short')
        self.execute_operation(rop.SETFIELD_GC, [t_box, BoxInt(250)],
                               'void', descr=fielddescr2)
        self.execute_operation(rop.SETFIELD_GC, [t_box, BoxInt(133)],
                               'void', descr=fielddescr1)
        self.execute_operation(rop.SETFIELD_GC, [t_box, BoxInt(1331)],
                               'void', descr=shortdescr)
        res = self.execute_operation(rop.GETFIELD_GC, [t_box],
                                     'int', descr=fielddescr2)
        assert res.value == 250
        res = self.execute_operation(rop.GETFIELD_GC, [t_box],
                                     'int', descr=fielddescr1)
        assert res.value == 133
        res = self.execute_operation(rop.GETFIELD_GC, [t_box],
                                     'int', descr=shortdescr)
        assert res.value == 1331
        
        #
        u_box, U_box = self.alloc_instance(self.U)
        fielddescr2 = self.cpu.fielddescrof(self.S, 'next')
        assert fielddescr2.is_pointer_field()
        res = self.execute_operation(rop.SETFIELD_GC, [t_box, u_box],
                                     'void', descr=fielddescr2)
        assert res is None
        res = self.execute_operation(rop.GETFIELD_GC, [t_box],
                                     'ref', descr=fielddescr2)
        assert res.value == u_box.value
        #
        null_const = self.null_instance().constbox()
        res = self.execute_operation(rop.SETFIELD_GC, [t_box, null_const],
                                     'void', descr=fielddescr2)
        assert res is None
        res = self.execute_operation(rop.GETFIELD_GC, [t_box],
                                     'ref', descr=fielddescr2)
        assert res.value == null_const.value

    def test_passing_guards(self):
        for (opname, args) in [(rop.GUARD_TRUE, [BoxInt(1)]),
                               (rop.GUARD_FALSE, [BoxInt(0)]),
                               (rop.GUARD_VALUE, [BoxInt(42), BoxInt(42)]),
                               ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert not self.guard_failed


    def test_passing_guard_class(self):
        t_box, T_box = self.alloc_instance(self.T)
        #null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        self.execute_operation(rop.GUARD_CLASS, [t_box, T_box], 'void')
        assert not self.guard_failed
        #self.execute_operation(rop.GUARD_CLASS_INVERSE, [t_box, null_box],
        #                       'void')

    def test_failing_guards(self):
        for opname, args in [(rop.GUARD_TRUE, [BoxInt(0)]),
                             (rop.GUARD_FALSE, [BoxInt(1)]),
                             (rop.GUARD_VALUE, [BoxInt(42), BoxInt(41)]),
                             ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert self.guard_failed

    def test_failing_guard_class(self):
        t_box, T_box = self.alloc_instance(self.T)
        u_box, U_box = self.alloc_instance(self.U)        
        #null_box = ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF, lltype.nullptr(T)))
        for opname, args in [(rop.GUARD_CLASS, [t_box, U_box]),
                             (rop.GUARD_CLASS, [u_box, T_box]),
                             #(rop.GUARD_VALUE_INVERSE, [BoxInt(10), BoxInt(10)]),
                             ]:
            assert self.execute_operation(opname, args, 'void') == None
            assert self.guard_failed

    def test_ooops(self):
        u1_box, U_box = self.alloc_instance(self.U)
        u2_box, U_box = self.alloc_instance(self.U)
        r = self.execute_operation(rop.OOIS, [u1_box,
                                              u1_box.clonebox()], 'int')
        assert r.value == 1
        r = self.execute_operation(rop.OOISNOT, [u2_box,
                                                 u2_box.clonebox()], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OOIS, [u1_box, u2_box], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OOISNOT, [u2_box, u1_box], 'int')
        assert r.value == 1
        r = self.execute_operation(rop.OOISNULL, [u1_box], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OONONNULL, [u2_box], 'int')
        assert r.value == 1
        #
        null_box = self.null_instance()
        r = self.execute_operation(rop.OOIS, [null_box,
                                              null_box.clonebox()], 'int')
        assert r.value == 1
        r = self.execute_operation(rop.OOIS, [u1_box, null_box], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OOIS, [null_box, u2_box], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OOISNOT, [null_box,
                                                 null_box.clonebox()], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OOISNOT, [u2_box, null_box], 'int')
        assert r.value == 1
        r = self.execute_operation(rop.OOISNOT, [null_box, u1_box], 'int')
        assert r.value == 1
        r = self.execute_operation(rop.OOISNULL, [null_box], 'int')
        assert r.value == 1
        r = self.execute_operation(rop.OONONNULL, [null_box], 'int')
        assert r.value == 0

    def test_array_basic(self):
        a_box, A = self.alloc_array_of(lltype.Signed, 342)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        #
        r = self.cpu.do_arraylen_gc(a_box, arraydescr)
        assert r.value == 342
        self.cpu.do_setarrayitem_gc(a_box, BoxInt(311), BoxInt(170), arraydescr)
        r = self.cpu.do_getarrayitem_gc(a_box, BoxInt(311), arraydescr)
        assert r.value == 170
        #
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r.value == 342
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, BoxInt(310),
                                                         BoxInt(7441)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC, [a_box, BoxInt(310)],
                                   'int', descr=arraydescr)
        assert r.value == 7441
        #
        a_box, A = self.alloc_array_of(lltype.Char, 11)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r.value == 11
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, BoxInt(4),
                                                         BoxInt(150)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, BoxInt(3),
                                                         BoxInt(160)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC, [a_box, BoxInt(4)],
                                   'int', descr=arraydescr)
        assert r.value == 150
        r = self.execute_operation(rop.GETARRAYITEM_GC, [a_box, BoxInt(3)],
                                   'int', descr=arraydescr)
        assert r.value == 160
        
        #
        if isinstance(A, lltype.GcArray):
            A = lltype.Ptr(A)
        b_box, B = self.alloc_array_of(A, 3)
        arraydescr = self.cpu.arraydescrof(B)
        assert arraydescr.is_array_of_pointers()
        r = self.execute_operation(rop.ARRAYLEN_GC, [b_box],
                                   'int', descr=arraydescr)
        assert r.value == 3
        r = self.execute_operation(rop.SETARRAYITEM_GC, [b_box, BoxInt(1),
                                                         a_box],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC, [b_box, BoxInt(1)],
                                   'ref', descr=arraydescr)
        assert r.value == a_box.value
        #
        # Unsigned should work the same as Signed
        a_box, A = self.alloc_array_of(lltype.Unsigned, 342)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r.value == 342
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, BoxInt(310),
                                                         BoxInt(7441)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC, [a_box, BoxInt(310)],
                                   'int', descr=arraydescr)
        assert r.value == 7441
        #
        # Bool should work the same as Char
        a_box, A = self.alloc_array_of(lltype.Bool, 311)
        arraydescr = self.cpu.arraydescrof(A)
        assert not arraydescr.is_array_of_pointers()
        r = self.execute_operation(rop.ARRAYLEN_GC, [a_box],
                                   'int', descr=arraydescr)
        assert r.value == 311
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, BoxInt(304),
                                                         BoxInt(1)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, BoxInt(303),
                                                         BoxInt(0)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.SETARRAYITEM_GC, [a_box, BoxInt(302),
                                                         BoxInt(1)],
                                   'void', descr=arraydescr)
        assert r is None
        r = self.execute_operation(rop.GETARRAYITEM_GC, [a_box, BoxInt(304)],
                                   'int', descr=arraydescr)
        assert r.value == 1
        r = self.execute_operation(rop.GETARRAYITEM_GC, [a_box, BoxInt(303)],
                                   'int', descr=arraydescr)
        assert r.value == 0
        r = self.execute_operation(rop.GETARRAYITEM_GC, [a_box, BoxInt(302)],
                                   'int', descr=arraydescr)
        assert r.value == 1

    def test_string_basic(self):
        s_box = self.alloc_string("hello\xfe")
        r = self.execute_operation(rop.STRLEN, [s_box], 'int')
        assert r.value == 6
        r = self.execute_operation(rop.STRGETITEM, [s_box, BoxInt(5)], 'int')
        assert r.value == 254
        r = self.execute_operation(rop.STRSETITEM, [s_box, BoxInt(4),
                                                    BoxInt(153)], 'void')
        assert r is None
        r = self.execute_operation(rop.STRGETITEM, [s_box, BoxInt(5)], 'int')
        assert r.value == 254
        r = self.execute_operation(rop.STRGETITEM, [s_box, BoxInt(4)], 'int')
        assert r.value == 153

    def test_unicode_basic(self):
        u_box = self.cpu.do_newunicode(ConstInt(5))
        self.cpu.do_unicodesetitem(u_box, BoxInt(4), BoxInt(123))
        r = self.cpu.do_unicodegetitem(u_box, BoxInt(4))
        assert r.value == 123
        #
        u_box = self.alloc_unicode(u"hello\u1234")
        r = self.execute_operation(rop.UNICODELEN, [u_box], 'int')
        assert r.value == 6
        r = self.execute_operation(rop.UNICODEGETITEM, [u_box, BoxInt(5)],
                                   'int')
        assert r.value == 0x1234
        r = self.execute_operation(rop.UNICODESETITEM, [u_box, BoxInt(4),
                                                        BoxInt(31313)], 'void')
        assert r is None
        r = self.execute_operation(rop.UNICODEGETITEM, [u_box, BoxInt(5)],
                                   'int')
        assert r.value == 0x1234
        r = self.execute_operation(rop.UNICODEGETITEM, [u_box, BoxInt(4)],
                                   'int')
        assert r.value == 31313

    def test_same_as(self):
        r = self.execute_operation(rop.SAME_AS, [ConstInt(5)], 'int')
        assert r.value == 5
        u_box = self.alloc_unicode(u"hello\u1234")
        r = self.execute_operation(rop.SAME_AS, [u_box.constbox()], 'ref')
        assert r.value == u_box.value


class LLtypeBackendTest(BaseBackendTest):

    type_system = 'lltype'
    Ptr = lltype.Ptr
    FuncType = lltype.FuncType
    malloc = staticmethod(lltype.malloc)
    nullptr = staticmethod(lltype.nullptr)

    @classmethod
    def get_funcbox(cls, cpu, func_ptr):
        addr = llmemory.cast_ptr_to_adr(func_ptr)
        return BoxInt(cpu.cast_adr_to_int(addr))

    
    MY_VTABLE = rclass.OBJECT_VTABLE    # for tests only

    S = lltype.GcForwardReference()
    S.become(lltype.GcStruct('S', ('parent', rclass.OBJECT),
                                  ('value', lltype.Signed),
                                  ('chr1', lltype.Char),
                                  ('chr2', lltype.Char),
                                  ('short', rffi.SHORT),
                                  ('next', lltype.Ptr(S))))
    T = lltype.GcStruct('T', ('parent', S),
                             ('next', lltype.Ptr(S)))
    U = lltype.GcStruct('U', ('parent', T),
                             ('next', lltype.Ptr(S)))


    def alloc_instance(self, T):
        vtable_for_T = lltype.malloc(self.MY_VTABLE, immortal=True)
        vtable_for_T_addr = llmemory.cast_ptr_to_adr(vtable_for_T)
        cpu = self.cpu
        if not hasattr(cpu, '_cache_gcstruct2vtable'):
            cpu._cache_gcstruct2vtable = {}
        cpu._cache_gcstruct2vtable.update({T: vtable_for_T})
        t = lltype.malloc(T)
        if T == self.T:
            t.parent.parent.typeptr = vtable_for_T
        elif T == self.U:
            t.parent.parent.parent.typeptr = vtable_for_T
        t_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, t))
        T_box = ConstInt(self.cpu.cast_adr_to_int(vtable_for_T_addr))
        return t_box, T_box

    def null_instance(self):
        return BoxPtr(lltype.nullptr(llmemory.GCREF.TO))

    def alloc_array_of(self, ITEM, length):
        cpu = self.cpu
        A = lltype.GcArray(ITEM)
        a = lltype.malloc(A, length)
        a_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, a))
        return a_box, A

    def alloc_string(self, string):
        s = rstr.mallocstr(len(string))
        for i in range(len(string)):
            s.chars[i] = string[i]
        s_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s))
        return s_box

    def alloc_unicode(self, unicode):
        u = rstr.mallocunicode(len(unicode))
        for i in range(len(unicode)):
            u.chars[i] = unicode[i]
        u_box = BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, u))
        return u_box


    def test_casts(self):
        from pypy.rpython.lltypesystem import lltype, llmemory
        TP = lltype.GcStruct('x')
        x = lltype.malloc(TP)        
        x = lltype.cast_opaque_ptr(llmemory.GCREF, x)
        res = self.execute_operation(rop.CAST_PTR_TO_INT,
                                     [BoxPtr(x)],  'int').value
        assert res == self.cpu.cast_gcref_to_int(x)
        res = self.execute_operation(rop.CAST_PTR_TO_INT,
                                     [ConstPtr(x)],  'int').value
        assert res == self.cpu.cast_gcref_to_int(x)

    def test_ooops_non_gc(self):
        x = lltype.malloc(lltype.Struct('x'), flavor='raw')
        v = self.cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(x))
        r = self.execute_operation(rop.OOIS, [BoxInt(v), BoxInt(v)], 'int')
        assert r.value == 1
        r = self.execute_operation(rop.OOISNOT, [BoxInt(v), BoxInt(v)], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OOISNULL, [BoxInt(v)], 'int')
        assert r.value == 0
        r = self.execute_operation(rop.OONONNULL, [BoxInt(v)], 'int')
        assert r.value == 1
        lltype.free(x, flavor='raw')

    def test_new_plain_struct(self):
        cpu = self.cpu
        S = lltype.GcStruct('S', ('x', lltype.Char), ('y', lltype.Char))
        sizedescr = cpu.sizeof(S)
        r1 = self.execute_operation(rop.NEW, [], 'ref', descr=sizedescr)
        r2 = self.execute_operation(rop.NEW, [], 'ref', descr=sizedescr)
        assert r1.value != r2.value
        xdescr = cpu.fielddescrof(S, 'x')
        ydescr = cpu.fielddescrof(S, 'y')
        self.execute_operation(rop.SETFIELD_GC, [r1, BoxInt(150)],
                               'void', descr=ydescr)
        self.execute_operation(rop.SETFIELD_GC, [r1, BoxInt(190)],
                               'void', descr=xdescr)
        s = lltype.cast_opaque_ptr(lltype.Ptr(S), r1.value)
        assert s.x == chr(190)
        assert s.y == chr(150)

    def test_new_with_vtable(self):
        cpu = self.cpu
        t_box, T_box = self.alloc_instance(self.T)
        cpu.set_class_sizes({T_box.value: cpu.sizeof(self.T)})
        r1 = self.execute_operation(rop.NEW_WITH_VTABLE, [T_box], 'ref')
        r2 = self.execute_operation(rop.NEW_WITH_VTABLE, [T_box], 'ref')
        assert r1.value != r2.value
        descr1 = cpu.fielddescrof(self.S, 'chr1')
        descr2 = cpu.fielddescrof(self.S, 'chr2')
        descrshort = cpu.fielddescrof(self.S, 'short')
        self.execute_operation(rop.SETFIELD_GC, [r1, BoxInt(150)],
                               'void', descr=descr2)
        self.execute_operation(rop.SETFIELD_GC, [r1, BoxInt(190)],
                               'void', descr=descr1)
        self.execute_operation(rop.SETFIELD_GC, [r1, BoxInt(1313)],
                               'void', descr=descrshort)
        s = lltype.cast_opaque_ptr(lltype.Ptr(self.T), r1.value)
        assert s.parent.chr1 == chr(190)
        assert s.parent.chr2 == chr(150)
        r = self.cpu.do_getfield_gc(r1, descrshort)
        assert r.value == 1313
        self.cpu.do_setfield_gc(r1, BoxInt(1333), descrshort)
        r = self.cpu.do_getfield_gc(r1, descrshort)
        assert r.value == 1333
        r = self.execute_operation(rop.GETFIELD_GC, [r1], 'int',
                                   descr=descrshort)
        assert r.value == 1333
        t = lltype.cast_opaque_ptr(lltype.Ptr(self.T), t_box.value)
        assert s.parent.parent.typeptr == t.parent.parent.typeptr

    def test_new_array(self):
        A = lltype.GcArray(lltype.Signed)
        arraydescr = self.cpu.arraydescrof(A)
        r1 = self.execute_operation(rop.NEW_ARRAY, [BoxInt(342)],
                                    'ref', descr=arraydescr)
        r2 = self.execute_operation(rop.NEW_ARRAY, [BoxInt(342)],
                                    'ref', descr=arraydescr)
        assert r1.value != r2.value
        a = lltype.cast_opaque_ptr(lltype.Ptr(A), r1.value)
        assert a[0] == 0
        assert len(a) == 342

    def test_new_string(self):
        r1 = self.execute_operation(rop.NEWSTR, [BoxInt(342)], 'ref')
        r2 = self.execute_operation(rop.NEWSTR, [BoxInt(342)], 'ref')
        assert r1.value != r2.value
        a = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), r1.value)
        assert len(a.chars) == 342

    def test_new_unicode(self):
        r1 = self.execute_operation(rop.NEWUNICODE, [BoxInt(342)], 'ref')
        r2 = self.execute_operation(rop.NEWUNICODE, [BoxInt(342)], 'ref')
        assert r1.value != r2.value
        a = lltype.cast_opaque_ptr(lltype.Ptr(rstr.UNICODE), r1.value)
        assert len(a.chars) == 342

    def test_do_operations(self):
        cpu = self.cpu
        #
        A = lltype.GcArray(lltype.Char)
        descr_A = cpu.arraydescrof(A)
        a = lltype.malloc(A, 5)
        x = cpu.do_arraylen_gc(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, a)),
            descr_A)
        assert x.value == 5
        #
        a[2] = 'Y'
        x = cpu.do_getarrayitem_gc(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, a)), BoxInt(2),
            descr_A)
        assert x.value == ord('Y')
        #
        B = lltype.GcArray(lltype.Ptr(A))
        descr_B = cpu.arraydescrof(B)
        b = lltype.malloc(B, 4)
        b[3] = a
        x = cpu.do_getarrayitem_gc(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, b)), BoxInt(3),
            descr_B)
        assert isinstance(x, BoxPtr)
        assert x.getref(lltype.Ptr(A)) == a
        #
        s = rstr.mallocstr(6)
        x = cpu.do_strlen(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s)))
        assert x.value == 6
        #
        s.chars[3] = 'X'
        x = cpu.do_strgetitem(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s)), BoxInt(3))
        assert x.value == ord('X')
        #
        S = lltype.GcStruct('S', ('x', lltype.Char), ('y', lltype.Ptr(A)))
        descrfld_x = cpu.fielddescrof(S, 'x')
        s = lltype.malloc(S)
        s.x = 'Z'
        x = cpu.do_getfield_gc(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s)),
            descrfld_x)
        assert x.value == ord('Z')
        #
        cpu.do_setfield_gc(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s)),
            BoxInt(ord('4')),
            descrfld_x)
        assert s.x == '4'
        #
        descrfld_y = cpu.fielddescrof(S, 'y')
        s.y = a
        x = cpu.do_getfield_gc(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s)),
            descrfld_y)
        assert isinstance(x, BoxPtr)
        assert x.getref(lltype.Ptr(A)) == a
        #
        s.y = lltype.nullptr(A)
        cpu.do_setfield_gc(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, s)), x,
            descrfld_y)
        assert s.y == a
        #
        RS = lltype.Struct('S', ('x', lltype.Char))  #, ('y', lltype.Ptr(A)))
        descrfld_rx = cpu.fielddescrof(RS, 'x')
        rs = lltype.malloc(RS, immortal=True)
        rs.x = '?'
        x = cpu.do_getfield_raw(
            BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs))),
            descrfld_rx)
        assert x.value == ord('?')
        #
        cpu.do_setfield_raw(
            BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs))),
            BoxInt(ord('!')),
            descrfld_rx)
        assert rs.x == '!'
        #
        ### we don't support in the JIT for now GC pointers
        ### stored inside non-GC structs.
        #descrfld_ry = cpu.fielddescrof(RS, 'y')
        #rs.y = a
        #x = cpu.do_getfield_raw(
        #    BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs))),
        #    descrfld_ry)
        #assert isinstance(x, BoxPtr)
        #assert x.getref(lltype.Ptr(A)) == a
        #
        #rs.y = lltype.nullptr(A)
        #cpu.do_setfield_raw(
        #    BoxInt(cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(rs))), x,
        #    descrfld_ry)
        #assert rs.y == a
        #
        descrsize = cpu.sizeof(S)
        x = cpu.do_new(descrsize)
        assert isinstance(x, BoxPtr)
        x.getref(lltype.Ptr(S))
        #
        descrsize2 = cpu.sizeof(rclass.OBJECT)
        vtable2 = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        vtable2_int = cpu.cast_adr_to_int(llmemory.cast_ptr_to_adr(vtable2))
        cpu.set_class_sizes({vtable2_int: descrsize2})
        x = cpu.do_new_with_vtable(ConstInt(vtable2_int))
        assert isinstance(x, BoxPtr)
        # well...
        #assert x.getref(rclass.OBJECTPTR).typeptr == vtable2
        #
        arraydescr = cpu.arraydescrof(A)
        x = cpu.do_new_array(BoxInt(7), arraydescr)
        assert isinstance(x, BoxPtr)
        assert len(x.getref(lltype.Ptr(A))) == 7
        #
        cpu.do_setarrayitem_gc(
            x, BoxInt(5), BoxInt(ord('*')), descr_A)
        assert x.getref(lltype.Ptr(A))[5] == '*'
        #
        cpu.do_setarrayitem_gc(
            BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, b)),
            BoxInt(1), x,
            descr_B)
        assert b[1] == x.getref(lltype.Ptr(A))
        #
        x = cpu.do_newstr(BoxInt(5))
        assert isinstance(x, BoxPtr)
        assert len(x.getref(lltype.Ptr(rstr.STR)).chars) == 5
        #
        cpu.do_strsetitem(x, BoxInt(4), BoxInt(ord('/')))
        assert x.getref(lltype.Ptr(rstr.STR)).chars[4] == '/'
        #
        x = cpu.do_newstr(BoxInt(5))
        y = cpu.do_cast_ptr_to_int(x)
        assert isinstance(y, BoxInt)
        assert y.value == cpu.cast_gcref_to_int(x.value)

    def test_sorting_of_fields(self):
        S = self.S
        value = self.cpu.fielddescrof(S, 'value').sort_key()
        chr1 = self.cpu.fielddescrof(S, 'chr1').sort_key()
        chr2 = self.cpu.fielddescrof(S, 'chr2').sort_key()
        assert (sorted([chr2, chr1, value]) ==
                [value, chr1, chr2])
        assert len(dict.fromkeys([value, chr1, chr2]).keys()) == 3

    def test_exceptions(self):
        exc_tp = None
        exc_ptr = None
        def func(i):
            if i:
                raise LLException(exc_tp, exc_ptr)

        ops = '''
        [i0]
        i1 = same_as(1)
        call(ConstClass(fptr), i0, descr=calldescr)
        p0 = guard_exception(ConstClass(xtp)) [i1]
        finish(0, p0)
        '''
        FPTR = lltype.Ptr(lltype.FuncType([lltype.Signed], lltype.Void))
        fptr = llhelper(FPTR, func)
        calldescr = self.cpu.calldescrof(FPTR.TO, FPTR.TO.ARGS, FPTR.TO.RESULT)

        xtp = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        xtp.subclassrange_min = 1
        xtp.subclassrange_max = 3
        X = lltype.GcStruct('X', ('parent', rclass.OBJECT),
                            hints={'vtable':  xtp._obj})
        xptr = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(X))


        exc_tp = xtp
        exc_ptr = xptr
        loop = parse(ops, self.cpu, namespace=locals())
        executable_token = self.cpu.compile_loop(loop.inputargs,
                                                 loop.operations)
        self.cpu.set_future_value_int(0, 1)
        self.cpu.execute_token(executable_token)
        assert self.cpu.get_latest_value_int(0) == 0
        assert self.cpu.get_latest_value_ref(1) == xptr
        self.cpu.clear_exception()
        self.cpu.set_future_value_int(0, 0)
        self.cpu.execute_token(executable_token)
        assert self.cpu.get_latest_value_int(0) == 1
        self.cpu.clear_exception()

        ytp = lltype.malloc(rclass.OBJECT_VTABLE, immortal=True)
        ytp.subclassrange_min = 2
        ytp.subclassrange_max = 2
        assert rclass.ll_issubclass(ytp, xtp)
        Y = lltype.GcStruct('Y', ('parent', rclass.OBJECT),
                            hints={'vtable':  ytp._obj})
        yptr = lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(Y))

        # guard_exception uses an exact match
        exc_tp = ytp
        exc_ptr = yptr
        loop = parse(ops, self.cpu, namespace=locals())
        executable_token = self.cpu.compile_loop(loop.inputargs,
                                                 loop.operations)
        self.cpu.set_future_value_int(0, 1)
        self.cpu.execute_token(executable_token)
        assert self.cpu.get_latest_value_int(0) == 1
        self.cpu.clear_exception()

        exc_tp = xtp
        exc_ptr = xptr
        ops = '''
        [i0]
        i1 = same_as(1)
        call(ConstClass(fptr), i0, descr=calldescr)
        guard_no_exception() [i1]
        finish(0)
        '''
        loop = parse(ops, self.cpu, namespace=locals())
        executable_token = self.cpu.compile_loop(loop.inputargs,
                                                 loop.operations)
        self.cpu.set_future_value_int(0, 1)
        self.cpu.execute_token(executable_token)
        assert self.cpu.get_latest_value_int(0) == 1
        self.cpu.clear_exception()
        self.cpu.set_future_value_int(0, 0)
        self.cpu.execute_token(executable_token)
        assert self.cpu.get_latest_value_int(0) == 0
        self.cpu.clear_exception()

    def test_cond_call_gc_wb(self):
        def func_void(a, b):
            record.append((a, b))
        record = []
        #
        FUNC = self.FuncType([lltype.Signed, lltype.Signed], lltype.Void)
        func_ptr = llhelper(lltype.Ptr(FUNC), func_void)
        funcbox = self.get_funcbox(self.cpu, func_ptr)
        calldescr = self.cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT)
        for cond in [False, True]:
            value = random.randrange(-sys.maxint, sys.maxint)
            if cond:
                value |= 4096
            else:
                value &= ~4096
            del record[:]
            self.execute_operation(rop.COND_CALL_GC_WB,
                                   [BoxInt(value), ConstInt(4096),
                                    funcbox, BoxInt(655360), BoxInt(-2121)],
                                   'void', descr=calldescr)
            if cond:
                assert record == [(655360, -2121)]
            else:
                assert record == []


class OOtypeBackendTest(BaseBackendTest):

    type_system = 'ootype'
    Ptr = staticmethod(lambda x: x)
    FuncType = ootype.StaticMethod
    malloc = staticmethod(ootype.new)
    nullptr = staticmethod(ootype.null)

    @classmethod
    def get_funcbox(cls, cpu, func_ptr):
        return BoxObj(ootype.cast_to_object(func_ptr))

    S = ootype.Instance('S', ootype.ROOT, {'value': ootype.Signed,
                                           'chr1': ootype.Char,
                                           'chr2': ootype.Char})
    S._add_fields({'next': S})
    T = ootype.Instance('T', S)
    U = ootype.Instance('U', T)

    def alloc_instance(self, T):
        t = ootype.new(T)
        cls = ootype.classof(t)
        t_box = BoxObj(ootype.cast_to_object(t))
        T_box = ConstObj(ootype.cast_to_object(cls))
        return t_box, T_box

    def null_instance(self):
        return BoxObj(ootype.NULL)

    def alloc_array_of(self, ITEM, length):
        py.test.skip("implement me")

    def alloc_string(self, string):
        py.test.skip("implement me")

    def alloc_unicode(self, unicode):
        py.test.skip("implement me")
