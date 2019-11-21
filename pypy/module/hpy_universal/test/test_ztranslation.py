from rpython.translator.c.test.test_standalone import StandaloneTests
from rpython.config.translationoption import get_combined_translation_config
from pypy.config.pypyoption import get_pypy_config
from pypy.objspace.fake.checkmodule import checkmodule
from pypy.objspace.fake.objspace import FakeObjSpace
from pypy.module.hpy_universal.state import State

def test_checkmodule():
    def extra_func(space):
        state = space.fromcache(State)
        state.setup()

    config_opts = {'translation.gc': 'boehm'}
    checkmodule('hpy_universal',
                extra_func=extra_func,
                c_compile=True,
                config_opts=config_opts)
