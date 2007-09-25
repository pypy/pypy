from pypy.rlib import rcoroutine
from pypy.rlib import rstack
from pypy.rlib.rstack import resume_state_create
from pypy.translator.stackless.test.test_transform import llinterp_stackless_function
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.lltypesystem import lltype

class TestCoroutineReconstruction:

    def setup_meth(self):
        rcoroutine.syncstate.reset()

    def test_simple_ish(self):

        output = []
        def f(coro, n, x):
            if n == 0:
                coro.switch()
                rstack.resume_point("f_0")
                return
            f(coro, n-1, 2*x)
            rstack.resume_point("f_1", coro, n, x)
            output.append(x)

        class T(rcoroutine.AbstractThunk):
            def __init__(self, arg_coro, arg_n, arg_x):
                self.arg_coro = arg_coro
                self.arg_n = arg_n
                self.arg_x = arg_x
            def call(self):
                f(self.arg_coro, self.arg_n, self.arg_x)

        def example():
            main_coro = rcoroutine.Coroutine.getcurrent()
            sub_coro = rcoroutine.Coroutine()
            thunk_f = T(main_coro, 5, 1)
            sub_coro.bind(thunk_f)
            sub_coro.switch()

            new_coro = rcoroutine.Coroutine()
            new_thunk_f = T(main_coro, 5, 1)
            new_coro.bind(new_thunk_f)

            costate = rcoroutine.Coroutine._get_default_costate()
            bottom = resume_state_create(None, "yield_current_frame_to_caller_1")
            _bind_frame = resume_state_create(bottom, "coroutine__bind", costate)
            f_frame_1 = resume_state_create(_bind_frame, "f_1", main_coro, 5, 1)
            f_frame_2 = resume_state_create(f_frame_1, "f_1", main_coro, 4, 2)
            f_frame_3 = resume_state_create(f_frame_2, "f_1", main_coro, 3, 4)
            f_frame_4 = resume_state_create(f_frame_3, "f_1", main_coro, 2, 8)
            f_frame_5 = resume_state_create(f_frame_4, "f_1", main_coro, 1, 16)
            f_frame_0 = resume_state_create(f_frame_5, "f_0")
            switch_frame = resume_state_create(f_frame_0, "coroutine_switch", costate)

            new_coro.frame = switch_frame

            new_coro.switch()
            return output == [16, 8, 4, 2, 1]

        res = llinterp_stackless_function(example)
        assert res == 1

