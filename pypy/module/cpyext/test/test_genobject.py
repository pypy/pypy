from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.genobject import PyGen_Check, PyGen_CheckExact
from pypy.module.cpyext.genobject import PyCoro_CheckExact


class TestGenObject(BaseApiTest):
    def test_genobject(self, space):
        w_geniter = space.appexec([], """():
            def f():
                yield 42
            return f()
        """)
        assert PyGen_Check(space, w_geniter)
        assert PyGen_CheckExact(space, w_geniter)
        assert not PyCoro_CheckExact(space, w_geniter)
        assert not PyGen_Check(space, space.wrap(2))
        assert not PyGen_CheckExact(space, space.wrap("b"))
        assert not PyCoro_CheckExact(space, space.wrap([]))

        w_coroutine = space.appexec([], """():
            async def f():
                pass
            return f()
        """)
        assert not PyGen_Check(space, w_coroutine)
        assert not PyGen_CheckExact(space, w_coroutine)
        assert PyCoro_CheckExact(space, w_coroutine)
