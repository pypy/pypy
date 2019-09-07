from pypy.module._demo.moduledef import Module
from pypy.tool.option import make_config, make_objspace

class TestImport:

    def setup_method(self, func):
        Module.demo_events = []

    def test_startup(self):
        config = make_config(None, usemodules=('_demo',))
        space = make_objspace(config)
        w_modules = space.sys.get('modules')

        assert Module.demo_events == ['setup']
        assert not space.contains_w(w_modules, space.wrap('_demo'))

        # first import
        w_import = space.builtin.get('__import__')
        w_demo = space.call(w_import,
                            space.newlist([space.wrap('_demo')]))
        assert Module.demo_events == ['setup', 'startup']

        # reload the module, this should not call startup again
        space.delitem(w_modules,
                      space.wrap('_demo'))
        w_demo = space.call(w_import,
                            space.newlist([space.wrap('_demo')]))
        assert Module.demo_events == ['setup', 'startup']

        assert space.getattr(w_demo, space.wrap('measuretime'))
