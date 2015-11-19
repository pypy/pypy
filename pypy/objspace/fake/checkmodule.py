from pypy.objspace.fake.objspace import FakeObjSpace, W_Root
from pypy.config.pypyoption import get_pypy_config


def checkmodule(*modnames, **kwds):
    translate_startup = kwds.pop('translate_startup', True)
    assert not kwds
    config = get_pypy_config(translating=True)
    space = FakeObjSpace(config)
    seeobj_w = []
    modules = []
    for modname in modnames:
        mod = __import__('pypy.module.%s' % modname, None, None, ['__doc__'])
        # force computation and record what we wrap
        module = mod.Module(space, W_Root())
        module.setup_after_space_initialization()
        module.init(space)
        modules.append(module)
        for name in module.loaders:
            seeobj_w.append(module._load_lazily(space, name))
        if hasattr(module, 'submodules'):
            for cls in module.submodules.itervalues():
                submod = cls(space, W_Root())
                for name in submod.loaders:
                    seeobj_w.append(submod._load_lazily(space, name))
    #
    def func():
        for mod in modules:
            mod.startup(space)
    if not translate_startup:
        func()   # call it now
        func = None
    space.translates(func, seeobj_w=seeobj_w,
                     **{'translation.list_comprehension_operations': True})
