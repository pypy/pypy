
from pypy.conftest import gettestobjspace    
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.gateway import interp2app
from pypy.jit.metainterp.history import LoopToken
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.rpython.annlowlevel import (cast_instance_to_base_ptr,
                                      cast_base_ptr_to_instance)
from pypy.module.pypyjit.interp_jit import pypyjitdriver

class AppTestJitHook(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('pypyjit',))
        cls.space = space
        w_f = space.appexec([], """():
        def f():
            pass
        return f
        """)
        ll_code = cast_instance_to_base_ptr(w_f.code)

        oplist = []

        def interp_on_compile():
            pypyjitdriver.on_compile(LoopToken(), oplist, 'loop',
                                     0, False, ll_code)

        def interp_on_compile_bridge():
            pypyjitdriver.on_compile_bridge(LoopToken(), oplist, 0)
        
        cls.w_on_compile = space.wrap(interp2app(interp_on_compile))
        cls.w_on_compile_bridge = space.wrap(interp2app(interp_on_compile_bridge))

    def test_on_compile(self):
        import pypyjit
        all = []

        def hook(*args):
            all.append(args)
        
        self.on_compile()
        pypyjit.set_compile_hook(hook)
        assert not all
        self.on_compile()
        assert len(all) == 1
        assert all[0][0].co_name == 'f'
        print all
