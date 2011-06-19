
import py
from pypy.conftest import gettestobjspace, option
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.gateway import interp2app
from pypy.jit.metainterp.history import LoopToken
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.logger import Logger
from pypy.rpython.annlowlevel import (cast_instance_to_base_ptr,
                                      cast_base_ptr_to_instance)
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.module.pypyjit.interp_jit import pypyjitdriver
from pypy.jit.tool.oparser import parse
from pypy.jit.metainterp.typesystem import llhelper

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

        def interp_on_compile():
            pypyjitdriver.on_compile(logger, LoopToken(), oplist, 'loop',
                                     0, False, ll_code)

        def interp_on_compile_bridge():
            pypyjitdriver.on_compile_bridge(logger, LoopToken(), oplist, 0)
        
        cls.w_on_compile = space.wrap(interp2app(interp_on_compile))
        cls.w_on_compile_bridge = space.wrap(interp2app(interp_on_compile_bridge))

    def test_on_compile(self):
        import pypyjit
        all = []

        def hook(*args):
            assert args[0] == 'main'
            assert args[1] in ['loop', 'bridge']
            all.append(args[2:])
        
        self.on_compile()
        pypyjit.set_compile_hook(hook)
        assert not all
        self.on_compile()
        assert len(all) == 1
        assert all[0][0][0].co_name == 'f'
        assert all[0][0][1] == 0
        assert all[0][0][2] == False
        assert len(all[0][1]) == 3
        assert 'int_add' in all[0][1][0]
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
