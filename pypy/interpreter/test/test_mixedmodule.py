from pypy.interpreter.mixedmodule import MixedModule


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
    def setup_class(cls):
        space = cls.space

        class SubModule(MixedModule):
            interpleveldefs = {}
            appleveldefs = {}

        class Module(MixedModule):
            interpleveldefs = {}
            appleveldefs = {}
            submodules = {
                "sub": SubModule
            }

        m = Module(space, space.wrap("test_module"))
        m.install()

    def test_attibute(self):
        import test_module

        assert hasattr(test_module, "sub")

    def test_submodule_import(self):
        from test_module import sub
