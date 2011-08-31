from pypy.rpython.lltypesystem import llmemory
from pypy.rlib.libffi import Func, types
from pypy.jit.metainterp.history import AbstractDescr
from pypy.jit.codewriter.effectinfo import EffectInfo
from pypy.jit.metainterp.optimizeopt.test.test_optimizebasic import BaseTestBasic
from pypy.jit.metainterp.optimizeopt.test.test_optimizebasic import LLtypeMixin

class MyCallDescr(AbstractDescr):
    """
    Fake calldescr to be used inside the tests.

    The particularity is that it provides an __eq__ method, so that it
    comparses by value by comparing the arg_types and typeinfo fields, so you
    can check that the signature of a call is really what you want.
    """

    def __init__(self, arg_types, typeinfo, flags):
        self.arg_types = arg_types
        self.typeinfo = typeinfo   # return type
        self.flags = flags

    def __eq__(self, other):
        return (self.arg_types == other.arg_types and
                self.typeinfo == other.typeinfo and
                self.flags == other.get_ffi_flags())

class FakeLLObject(object):

    def __init__(self, **kwds):
        self.__dict__.update(kwds)
        self._TYPE = llmemory.GCREF

    def _identityhash(self):
        return id(self)


class TestFfiCall(BaseTestBasic, LLtypeMixin):

    enable_opts = "intbounds:rewrite:virtualize:string:heap:ffi"

    class namespace:
        cpu = LLtypeMixin.cpu
        FUNC = LLtypeMixin.FUNC
        vable_token_descr = LLtypeMixin.valuedescr
        valuedescr = LLtypeMixin.valuedescr

        int_float__int_42 = MyCallDescr('if', 'i', 42)
        int_float__int_43 = MyCallDescr('if', 'i', 43)
        funcptr = FakeLLObject()
        func = FakeLLObject(_fake_class=Func,
                            argtypes=[types.sint, types.double],
                            restype=types.sint,
                            flags=42)
        func2 = FakeLLObject(_fake_class=Func,
                             argtypes=[types.sint, types.double],
                             restype=types.sint,
                             flags=43)
        #
        def calldescr(cpu, FUNC, oopspecindex, extraeffect=None):
            if extraeffect == EffectInfo.EF_RANDOM_EFFECTS:
                f = None   # means "can force all" really
            else:
                f = []
            einfo = EffectInfo(f, f, f, f, oopspecindex=oopspecindex,
                               extraeffect=extraeffect)
            return cpu.calldescrof(FUNC, FUNC.ARGS, FUNC.RESULT, einfo)
        #
        libffi_prepare =  calldescr(cpu, FUNC, EffectInfo.OS_LIBFFI_PREPARE)
        libffi_push_arg = calldescr(cpu, FUNC, EffectInfo.OS_LIBFFI_PUSH_ARG)
        libffi_call =     calldescr(cpu, FUNC, EffectInfo.OS_LIBFFI_CALL,
                                    EffectInfo.EF_RANDOM_EFFECTS)
    
    namespace = namespace.__dict__

    # ----------------------------------------------------------------------
    # this group of tests is the most important, as they represent the "real"
    # cases you actually get when using rlib.libffi
    
    def test_ffi_call_opt(self):
        ops = """
        [i0, f1]
        call(0, ConstPtr(func),                       descr=libffi_prepare)
        call(0, ConstPtr(func), i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func), f1,                   descr=libffi_push_arg)
        i3 = call_may_force(0, ConstPtr(func), 12345, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, f1)
        """
        expected = """
        [i0, f1]
        i3 = call_release_gil(12345, i0, f1, descr=int_float__int_42)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, f1)
        """
        loop = self.optimize_loop(ops, expected)

    def test_ffi_call_nonconst(self):
        ops = """
        [i0, f1, p2]
        call(0, p2,                       descr=libffi_prepare)
        call(0, p2, i0,                   descr=libffi_push_arg)
        call(0, p2, f1,                   descr=libffi_push_arg)
        i3 = call_may_force(0, p2, 12345, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, f1, p2)
        """
        expected = ops
        loop = self.optimize_loop(ops, expected)

    def test_handle_virtualizables(self):
        # this test needs an explanation to understand what goes on: see the
        # comment in optimize_FORCE_TOKEN
        ops = """
        [i0, f1, p2]
        call(0, ConstPtr(func),                       descr=libffi_prepare)
        call(0, ConstPtr(func), i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func), f1,                   descr=libffi_push_arg)
        i4 = force_token()
        setfield_gc(p2, i4, descr=vable_token_descr)
        i3 = call_may_force(0, ConstPtr(func), 12345, descr=libffi_call)
        guard_not_forced() [p2]
        guard_no_exception() [p2]
        jump(i3, f1, p2)
        """
        expected = """
        [i0, f1, p2]
        i4 = force_token()
        setfield_gc(p2, i4, descr=vable_token_descr)
        i3 = call_release_gil(12345, i0, f1, descr=int_float__int_42)
        guard_not_forced() [p2]
        guard_no_exception() [p2]
        jump(i3, f1, p2)
        """
        loop = self.optimize_loop(ops, expected)

    # ----------------------------------------------------------------------
    # in pratice, the situations described in these tests should never happen,
    # but we still want to ensure correctness

    def test_rollback_if_op_in_between(self):
        ops = """
        [i0, f1]
        call(0, ConstPtr(func),                       descr=libffi_prepare)
        call(0, ConstPtr(func), i0,                   descr=libffi_push_arg)
        i1 = int_add(i0, 1)
        call(0, ConstPtr(func), f1,                   descr=libffi_push_arg)
        i3 = call_may_force(0, ConstPtr(func), 12345, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, f1)
        """
        expected = ops
        loop = self.optimize_loop(ops, expected)

    def test_rollback_multiple_calls(self):
        ops = """
        [i0, i2, f1]
        call(0, ConstPtr(func),                        descr=libffi_prepare)
        call(0, ConstPtr(func),  i0,                   descr=libffi_push_arg)
        #
        # this is the culprit!
        call(0, ConstPtr(func2),                       descr=libffi_prepare)
        #
        call(0, ConstPtr(func),  f1,                   descr=libffi_push_arg)
        i3 = call_may_force(0, ConstPtr(func),  12345, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        call(0, ConstPtr(func2), i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func2), f1,                   descr=libffi_push_arg)
        i4 = call_may_force(0, ConstPtr(func2), 67890, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, i4, f1)
        """
        expected = ops
        loop = self.optimize_loop(ops, expected)

    def test_rollback_multiple_prepare(self):
        ops = """
        [i0, i2, f1]
        call(0, ConstPtr(func),                        descr=libffi_prepare)
        #
        # this is the culprit!
        call(0, ConstPtr(func2),                       descr=libffi_prepare)
        #
        call(0, ConstPtr(func),  i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func),  f1,                   descr=libffi_push_arg)
        i3 = call_may_force(0, ConstPtr(func),  12345, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        call(0, ConstPtr(func2), i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func2), f1,                   descr=libffi_push_arg)
        i4 = call_may_force(0, ConstPtr(func2), 67890, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, i4, f1)
        """
        expected = ops
        loop = self.optimize_loop(ops, expected)

    def test_optimize_nested_call(self):
        ops = """
        [i0, i2, f1]
        call(0, ConstPtr(func),                        descr=libffi_prepare)
        #
        # this "nested" call is nicely optimized
        call(0, ConstPtr(func2),                       descr=libffi_prepare)
        call(0, ConstPtr(func2), i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func2), f1,                   descr=libffi_push_arg)
        i4 = call_may_force(0, ConstPtr(func2), 67890, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        #
        call(0, ConstPtr(func),  i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func),  f1,                   descr=libffi_push_arg)
        i3 = call_may_force(0, ConstPtr(func),  12345, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, i4, f1)
        """
        expected = """
        [i0, i2, f1]
        call(0, ConstPtr(func),                        descr=libffi_prepare)
        #
        # this "nested" call is nicely optimized
        i4 = call_release_gil(67890, i0, f1, descr=int_float__int_43)
        guard_not_forced() []
        guard_no_exception() []
        #
        call(0, ConstPtr(func),  i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func),  f1,                   descr=libffi_push_arg)
        i3 = call_may_force(0, ConstPtr(func),  12345, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, i4, f1)
        """
        loop = self.optimize_loop(ops, expected)

    def test_rollback_force_token(self):
        ops = """
        [i0, f1, p2]
        call(0, ConstPtr(func),                       descr=libffi_prepare)
        call(0, ConstPtr(func), i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func), f1,                   descr=libffi_push_arg)
        i4 = force_token()
        i5 = int_add(i0, 1) # culprit!
        setfield_gc(p2, i4, descr=vable_token_descr)
        i3 = call_may_force(0, ConstPtr(func), 12345, descr=libffi_call)
        guard_not_forced() [p2]
        guard_no_exception() [p2]
        jump(i3, f1, p2)
        """
        expected = ops
        loop = self.optimize_loop(ops, expected)

    def test_allow_setfields_in_between(self):
        ops = """
        [i0, f1, p2]
        call(0, ConstPtr(func),                       descr=libffi_prepare)
        call(0, ConstPtr(func), i0,                   descr=libffi_push_arg)
        call(0, ConstPtr(func), f1,                   descr=libffi_push_arg)
        setfield_gc(p2, i0,                           descr=valuedescr)
        i3 = call_may_force(0, ConstPtr(func), 12345, descr=libffi_call)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, f1, p2)
        """
        expected = """
        [i0, f1, p2]
        setfield_gc(p2, i0, descr=valuedescr)
        i3 = call_release_gil(12345, i0, f1, descr=int_float__int_42)
        guard_not_forced() []
        guard_no_exception() []
        jump(i3, f1, p2)
        """
        loop = self.optimize_loop(ops, expected)
