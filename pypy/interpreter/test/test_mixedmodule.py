from pypy.interpreter.mixedmodule import MixedModule
import py.test


class TestMixedModule(object):
    def test_install(self):
        class Module(MixedModule):
            interpleveldefs = {}
            appleveldefs = {}

        m = Module(self.space, self.space.wrap("test_module"))
        m.install()

        assert self.space.builtin_modules["test_module"] is m

    def test_submodule(self):
        class SubModule(MixedModule):
            interpleveldefs = {}
            appleveldefs = {}

        class Module(MixedModule):
            interpleveldefs = {}
            appleveldefs = {}
            submodules = {
                "sub": SubModule
            }

        m = Module(self.space, self.space.wrap("test_module"))
        m.install()

        assert self.space.builtin_modules["test_module"] is m
        assert isinstance(self.space.builtin_modules["test_module.sub"], SubModule)

class AppTestMixedModule(object):
    pytestmark = py.test.mark.skipif("config.option.runappdirect")

    def setup_class(cls):
        space = cls.space

        class SubModule(MixedModule):
            interpleveldefs = {
                "value": "space.wrap(14)"
            }
            appleveldefs = {}

        class Module(MixedModule):
            interpleveldefs = {}
            appleveldefs = {}
            submodules = {
                "sub": SubModule
            }

        m = Module(space, space.wrap("test_module"))
        m.install()

    def teardown_class(cls):
        from pypy.module.sys.state import get

        space = cls.space
        del space.builtin_modules["test_module"]
        del space.builtin_modules["test_module.sub"]
        w_modules = get(space).w_modules
        space.delitem(w_modules, space.wrap("test_module"))
        space.delitem(w_modules, space.wrap("test_module.sub"))

    def test_attibute(self):
        import test_module

        assert hasattr(test_module, "sub")

    def test_submodule_import(self):
        from test_module import sub

    def test_direct_import(self):
        import test_module.sub

        assert test_module.sub
        assert test_module.sub.value == 14

    def test_import_from(self):
        from test_module.sub import value

        assert value == 14
