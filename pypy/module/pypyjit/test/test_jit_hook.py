
import py
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.pycode import PyCode
from rpython.jit.metainterp.history import JitCellToken, ConstInt, ConstPtr,\
     BasicFailDescr
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp.logger import Logger
from rpython.rtyper.annlowlevel import (cast_instance_to_base_ptr,
                                      cast_base_ptr_to_instance)
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.rclass import OBJECT
from pypy.module.pypyjit.interp_jit import pypyjitdriver
from pypy.module.pypyjit.policy import pypy_hooks
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.typesystem import llhelper
from rpython.rlib.jit import JitDebugInfo, AsmInfo, Counters


class MockJitDriverSD(object):
    class warmstate(object):
        @staticmethod
        def get_location_str(boxes):
            ll_code = lltype.cast_opaque_ptr(lltype.Ptr(OBJECT),
                                             boxes[2].getref_base())
            pycode = cast_base_ptr_to_instance(PyCode, ll_code)
            return pycode.co_name

    jitdriver = pypyjitdriver


class MockSD(object):
    class cpu(object):
        ts = llhelper

    jitdrivers_sd = [MockJitDriverSD]


class AppTestJitHook(object):
    spaceconfig = dict(usemodules=('pypyjit',))

    def setup_class(cls):
        if cls.runappdirect:
            py.test.skip("Can't run this test with -A")
        w_f = cls.space.appexec([], """():
        def function():
            pass
        return function
        """)
        cls.w_f = w_f
        ll_code = cast_instance_to_base_ptr(w_f.code)
        code_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, ll_code)
        logger = Logger(MockSD())

        oplist = parse("""
        [i1, i2, p2]
        i3 = int_add(i1, i2)
        debug_merge_point(0, 0, 0, 0, 0, ConstPtr(ptr0))
        guard_nonnull(p2) []
        guard_true(i3) []
        """, namespace={'ptr0': code_gcref}).operations
        greenkey = [ConstInt(0), ConstInt(0), ConstPtr(code_gcref)]
        offset = {}
        for i, op in enumerate(oplist):
            if i != 1:
                offset[op] = i

        token = JitCellToken()
        token.number = 0
        di_loop = JitDebugInfo(MockJitDriverSD, logger, token, oplist, 'loop',
                   greenkey)
        di_loop_optimize = JitDebugInfo(MockJitDriverSD, logger, JitCellToken(),
                                        oplist, 'loop', greenkey)
        di_loop.asminfo = AsmInfo(offset, 0x42, 12)
        di_bridge = JitDebugInfo(MockJitDriverSD, logger, JitCellToken(),
                                 oplist, 'bridge', fail_descr=BasicFailDescr())
        di_bridge.asminfo = AsmInfo(offset, 0, 0)

        def interp_on_compile():
            di_loop.oplist = cls.oplist
            pypy_hooks.after_compile(di_loop)

        def interp_on_compile_bridge():
            pypy_hooks.after_compile_bridge(di_bridge)

        def interp_on_optimize():
            di_loop_optimize.oplist = cls.oplist
            pypy_hooks.before_compile(di_loop_optimize)

        def interp_on_abort():
            pypy_hooks.on_abort(Counters.ABORT_TOO_LONG, pypyjitdriver,
                                greenkey, 'blah', Logger(MockSD), [])

        space = cls.space
        cls.w_on_compile = space.wrap(interp2app(interp_on_compile))
        cls.w_on_compile_bridge = space.wrap(interp2app(interp_on_compile_bridge))
        cls.w_on_abort = space.wrap(interp2app(interp_on_abort))
        cls.w_int_add_num = space.wrap(rop.INT_ADD)
        cls.w_dmp_num = space.wrap(rop.DEBUG_MERGE_POINT)
        cls.w_on_optimize = space.wrap(interp2app(interp_on_optimize))
        cls.orig_oplist = oplist
        cls.w_sorted_keys = space.wrap(sorted(Counters.counter_names))

    def setup_method(self, meth):
        self.__class__.oplist = self.orig_oplist[:]

    def test_on_compile(self):
        import pypyjit
        all = []

        def hook(info):
            all.append(info)

        self.on_compile()
        pypyjit.set_compile_hook(hook)
        assert not all
        self.on_compile()
        assert len(all) == 1
        info = all[0]
        assert info.jitdriver_name == 'pypyjit'
        assert info.greenkey[0].co_name == 'function'
        assert info.greenkey[1] == 0
        assert info.greenkey[2] == False
        assert info.loop_no == 0
        assert info.type == 'loop'
        assert info.asmaddr == 0x42
        assert info.asmlen == 12
        raises(TypeError, 'info.bridge_no')
        assert len(info.operations) == 4
        int_add = info.operations[0]
        dmp = info.operations[1]
        assert isinstance(dmp, pypyjit.DebugMergePoint)
        assert dmp.pycode is self.f.func_code
        assert dmp.greenkey == (self.f.func_code, 0, False)
        assert dmp.call_depth == 0
        assert dmp.call_id == 0
        assert dmp.offset == -1
        assert int_add.name == 'int_add'
        assert int_add.num == self.int_add_num
        assert int_add.offset == 0
        self.on_compile_bridge()
        expected = ('<JitLoopInfo pypyjit, 4 operations, starting at '
                    '<(%s, 0, False)>>' % repr(self.f.func_code))
        assert repr(all[0]) == expected
        assert len(all) == 2
        pypyjit.set_compile_hook(None)
        self.on_compile()
        assert len(all) == 2

    def test_on_compile_exception(self):
        import pypyjit, sys, cStringIO

        def hook(*args):
            1/0

        pypyjit.set_compile_hook(hook)
        s = cStringIO.StringIO()
        prev = sys.stderr
        sys.stderr = s
        try:
            self.on_compile()
        finally:
            sys.stderr = prev
        assert 'jit hook' in s.getvalue()
        assert 'ZeroDivisionError' in s.getvalue()

    def test_on_compile_crashes(self):
        import pypyjit
        loops = []
        def hook(loop):
            loops.append(loop)
        pypyjit.set_compile_hook(hook)
        self.on_compile()
        loop = loops[0]
        op = loop.operations[2]
        # Should not crash the interpreter
        raises(IndexError, op.getarg, 2)
        assert op.name == 'guard_nonnull'
        raises(NotImplementedError, op.getarg(0).getint)

    def test_non_reentrant(self):
        import pypyjit
        l = []

        def hook(*args):
            l.append(None)
            self.on_compile()
            self.on_compile_bridge()

        pypyjit.set_compile_hook(hook)
        self.on_compile()
        assert len(l) == 1 # and did not crash
        self.on_compile_bridge()
        assert len(l) == 2 # and did not crash

    def test_on_compile_types(self):
        import pypyjit
        l = []

        def hook(info):
            l.append(info)

        pypyjit.set_compile_hook(hook)
        self.on_compile()
        op = l[0].operations[1]
        assert isinstance(op, pypyjit.ResOperation)
        assert 'function' in repr(op)

    def test_on_abort(self):
        import pypyjit
        l = []

        def hook(jitdriver_name, greenkey, reason, operations):
            l.append((jitdriver_name, reason, operations))

        pypyjit.set_abort_hook(hook)
        self.on_abort()
        assert l == [('pypyjit', 'ABORT_TOO_LONG', [])]

    def test_on_optimize(self):
        import pypyjit
        l = []

        def hook(info):
            l.append(info.jitdriver_name)

        def optimize_hook(info):
            return []

        pypyjit.set_compile_hook(hook)
        pypyjit.set_optimize_hook(optimize_hook)
        self.on_optimize()
        self.on_compile()
        assert l == ['pypyjit']

    def test_creation(self):
        from pypyjit import Box, ResOperation

        op = ResOperation(self.int_add_num, [Box(1), Box(3)], Box(4))
        assert op.num == self.int_add_num
        assert op.name == 'int_add'
        box = op.getarg(0)
        assert box.getint() == 1
        box2 = op.result
        assert box2.getint() == 4
        op.setarg(0, box2)
        assert op.getarg(0).getint() == 4
        op.result = box
        assert op.result.getint() == 1

    def test_creation_dmp(self):
        from pypyjit import DebugMergePoint, Box

        def f():
            pass

        op = DebugMergePoint([Box(0)], 'repr', 'pypyjit', 2, 3, (f.func_code, 0, 0))
        assert op.bytecode_no == 0
        assert op.pycode is f.func_code
        assert repr(op) == 'repr'
        assert op.jitdriver_name == 'pypyjit'
        assert op.num == self.dmp_num
        assert op.call_depth == 2
        assert op.call_id == 3
        op = DebugMergePoint([Box(0)], 'repr', 'notmain', 5, 4, ('str',))
        raises(AttributeError, 'op.pycode')
        assert op.call_depth == 5

    def test_get_stats_snapshot(self):
        skip("a bit no idea how to test it")
        from pypyjit import get_stats_snapshot

        stats = get_stats_snapshot() # we can't do much here, unfortunately
        assert stats.w_loop_run_times == []
        assert isinstance(stats.w_counters, dict)
        assert sorted(stats.w_counters.keys()) == self.sorted_keys

