import sys
import pytest

from pypy.config.pypyoption import get_pypy_config
from pypy.objspace.std import StdObjSpace
from pypy.tool.udir import udir

mod_init = """
from pypy.interpreter.mixedmodule import MixedModule

import time

class Module(MixedModule):

    appleveldefs = {}

    interpleveldefs = {
    'clock'    : 'interp_time.clock',
    'time'     : 'interp_time.time_',
    'sleep'    : 'interp_time.sleep',
    }
"""

mod_interp = """
import time

from pypy.interpreter.gateway import unwrap_spec

def clock(space):
    return space.wrap(time.clock())

def time_(space):
    return space.wrap(time.time())

@unwrap_spec(seconds=float)
def sleep(space, seconds):
    time.sleep(seconds)
"""

old_sys_path = []

def init_extmodule_code():
    pkg = udir.join("testext")
    pkg.ensure(dir=True)
    pkg.join("__init__.py").write("# package")
    mod = pkg.join("extmod")
    mod.ensure(dir=True)
    mod.join("__init__.py").write(mod_init)
    mod.join("interp_time.py").write(mod_interp)

class AppTestExtModules(object):
    def setup_class(cls):
        init_extmodule_code()
        conf = get_pypy_config()
        conf.objspace.extmodules = 'testext.extmod'
        old_sys_path[:] = sys.path[:]
        sys.path.insert(0, str(udir))
        space = StdObjSpace(conf)
        cls.space = space

    def teardown_class(cls):
        sys.path[:] = old_sys_path

    @pytest.mark.skipif("config.option.runappdirect")
    def test_import(self):
        import extmod
        assert extmod.__file__.endswith('extmod')
        assert type(extmod.time()) is float
