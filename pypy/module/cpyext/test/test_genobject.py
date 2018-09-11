from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.genobject import PyGen_Check, PyGen_CheckExact


class TestGenObject(BaseApiTest):
    def test_genobject(self, space):
        w_geniter = space.appexec([], """():
            def f():
                yield 42
            return f()
        """)
        assert PyGen_Check(space, w_geniter)
        assert PyGen_CheckExact(space, w_geniter)
        assert not PyGen_Check(space, space.wrap(2))
        assert not PyGen_CheckExact(space, space.wrap("b"))
