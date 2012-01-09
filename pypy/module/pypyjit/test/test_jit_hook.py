
import py
from pypy.conftest import gettestobjspace, option
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.pycode import PyCode
from pypy.jit.metainterp.history import JitCellToken, ConstInt, ConstPtr
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.logger import Logger
from pypy.rpython.annlowlevel import (cast_instance_to_base_ptr,
                                      cast_base_ptr_to_instance)
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rclass import OBJECT
from pypy.module.pypyjit.interp_jit import pypyjitdriver
from pypy.module.pypyjit.policy import pypy_hooks
from pypy.jit.tool.oparser import parse
from pypy.jit.metainterp.typesystem import llhelper
from pypy.jit.metainterp.jitprof import ABORT_TOO_LONG

class MockJitDriverSD(object):
    class warmstate(object):
        @staticmethod
        def get_location_str(boxes):
            ll_code = lltype.cast_opaque_ptr(lltype.Ptr(OBJECT),
                                             boxes[2].getref_base())
            pycode = cast_base_ptr_to_instance(PyCode, ll_code)
            return pycode.co_name

class MockSD(object):
    class cpu(object):
        ts = llhelper

    jitdrivers_sd = [MockJitDriverSD]

class AppTestJitHook(object):
    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("Can't run this test with -A")
        space = gettestobjspace(usemodules=('pypyjit',))
        cls.space = space
        w_f = space.appexec([], """():
        def function():
            pass
        return function
        """)
        cls.w_f = w_f
        ll_code = cast_instance_to_base_ptr(w_f.code)
        code_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, ll_code)
        logger = Logger(MockSD())

        cls.origoplist = parse("""
        [i1, i2, p2]
        i3 = int_add(i1, i2)
        debug_merge_point(0, 0, 0, 0, ConstPtr(ptr0))
        guard_nonnull(p2) []
        guard_true(i3) []
        """, namespace={'ptr0': code_gcref}).operations
        greenkey = [ConstInt(0), ConstInt(0), ConstPtr(code_gcref)]
        offset = {}
        for i, op in enumerate(cls.origoplist):
            if i != 1:
               offset[op] = i

        def interp_on_compile():
            pypy_hooks.after_compile(pypyjitdriver, logger, JitCellToken(),
                                      cls.oplist, 'loop', greenkey, offset,
                                      0, 0)

        def interp_on_compile_bridge():
            pypy_hooks.after_compile_bridge(pypyjitdriver, logger,
                                             JitCellToken(), cls.oplist, 0,
                                             offset, 0, 0)

        def interp_on_optimize():
            pypy_hooks.before_compile(pypyjitdriver, logger, JitCellToken(),
                                       cls.oplist, 'loop', greenkey)

        def interp_on_abort():
            pypy_hooks.on_abort(ABORT_TOO_LONG, pypyjitdriver, greenkey)
        
        cls.w_on_compile = space.wrap(interp2app(interp_on_compile))
        cls.w_on_compile_bridge = space.wrap(interp2app(interp_on_compile_bridge))
        cls.w_on_abort = space.wrap(interp2app(interp_on_abort))
        cls.w_int_add_num = space.wrap(rop.INT_ADD)
        cls.w_on_optimize = space.wrap(interp2app(interp_on_optimize))

    def setup_method(self, meth):
        self.__class__.oplist = self.origoplist

    def test_on_compile(self):
        import pypyjit
        all = []

        def hook(name, looptype, tuple_or_guard_no, ops, asmstart, asmlen):
            all.append((name, looptype, tuple_or_guard_no, ops))
        
        self.on_compile()
        pypyjit.set_compile_hook(hook)
        assert not all
        self.on_compile()
        assert len(all) == 1
        elem = all[0]
        assert elem[0] == 'pypyjit'
        assert elem[2][0].co_name == 'function'
        assert elem[2][1] == 0
        assert elem[2][2] == False
        assert len(elem[3]) == 4
        int_add = elem[3][0]
        #assert int_add.name == 'int_add'
        assert int_add.num == self.int_add_num
        self.on_compile_bridge()
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

        def hook(*args):
            l.append(args)

        pypyjit.set_compile_hook(hook)
        self.on_compile()
        op = l[0][3][1]
        assert isinstance(op, pypyjit.ResOperation)
        assert 'function' in repr(op)

    def test_on_abort(self):
        import pypyjit
        l = []

        def hook(jitdriver_name, greenkey, reason):
            l.append((jitdriver_name, reason))
        
        pypyjit.set_abort_hook(hook)
        self.on_abort()
        assert l == [('pypyjit', 'ABORT_TOO_LONG')]

    def test_on_optimize(self):
        import pypyjit
        l = []

        def hook(name, looptype, tuple_or_guard_no, ops, *args):
            l.append(ops)

        def optimize_hook(name, looptype, tuple_or_guard_no, ops):
            return []

        pypyjit.set_compile_hook(hook)
        pypyjit.set_optimize_hook(optimize_hook)
        self.on_optimize()
        self.on_compile()
        assert l == [[]]

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
