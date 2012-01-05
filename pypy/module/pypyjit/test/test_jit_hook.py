
import py
from pypy.conftest import gettestobjspace, option
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.gateway import interp2app
from pypy.jit.metainterp.history import JitCellToken, ConstInt, ConstPtr
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.logger import Logger
from pypy.rpython.annlowlevel import (cast_instance_to_base_ptr,
                                      cast_base_ptr_to_instance)
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.module.pypyjit.interp_jit import pypyjitdriver
from pypy.module.pypyjit.policy import pypy_portal
from pypy.jit.tool.oparser import parse
from pypy.jit.metainterp.typesystem import llhelper
from pypy.jit.metainterp.jitprof import ABORT_TOO_LONG

class MockSD(object):
    class cpu(object):
        ts = llhelper

class AppTestJitHook(object):
    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("Can't run this test with -A")
        space = gettestobjspace(usemodules=('pypyjit',))
        cls.space = space
        w_f = space.appexec([], """():
        def f():
            pass
        return f
        """)
        cls.w_f = w_f
        ll_code = cast_instance_to_base_ptr(w_f.code)
        code_gcref = lltype.cast_opaque_ptr(llmemory.GCREF, ll_code)
        logger = Logger(MockSD())

        oplist = parse("""
        [i1, i2]
        i3 = int_add(i1, i2)
        debug_merge_point(0, 0, 0, 0, ConstPtr(ptr0))
        guard_true(i3) []
        """, namespace={'ptr0': code_gcref}).operations
        greenkey = [ConstInt(0), ConstInt(0), ConstPtr(code_gcref)]

        def interp_on_compile():
            pypy_portal.on_compile(pypyjitdriver, logger, JitCellToken(),
                                   oplist, 'loop', greenkey, {}, 0, 0)

        def interp_on_compile_bridge():
            pypy_portal.on_compile_bridge(pypyjitdriver, logger,
                                            JitCellToken(), oplist, 0,
                                            {}, 0, 0)

        def interp_on_abort():
            pypy_portal.on_abort(ABORT_TOO_LONG, pypyjitdriver, greenkey)
        
        cls.w_on_compile = space.wrap(interp2app(interp_on_compile))
        cls.w_on_compile_bridge = space.wrap(interp2app(interp_on_compile_bridge))
        cls.w_on_abort = space.wrap(interp2app(interp_on_abort))

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
        assert elem[2][0].co_name == 'f'
        assert elem[2][1] == 0
        assert elem[2][2] == False
        assert len(elem[3]) == 3
        assert 'int_add' in elem[3][0]
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
        dmp = l[0][3][1]
        assert isinstance(dmp, pypyjit.DebugMergePoint)
        assert dmp.code is self.f.func_code

    def test_creation(self):
        import pypyjit
        dmp = pypyjit.DebugMergePoint(0, 0, self.f.func_code)
        assert dmp.code is self.f.func_code 

    def test_on_abort(self):
        import pypyjit
        l = []

        def hook(jitdriver_name, greenkey, reason):
            l.append((jitdriver_name, reason))
        
        pypyjit.set_abort_hook(hook)
        self.on_abort()
        assert l == [('pypyjit', 'ABORT_TOO_LONG')]
