from pypy.objspace.fake.objspace import FakeObjSpace, W_Root
from pypy.config.pypyoption import get_pypy_config


def checkmodule(*modnames):
    config = get_pypy_config(translating=True)
    space = FakeObjSpace(config)
    seeobj_w = []
    for modname in modnames:
        mod = __import__('pypy.module.%s' % modname, None, None, ['__doc__'])
        # force computation and record what we wrap
        module = mod.Module(space, W_Root())
        module.startup(space)
        for name in module.loaders:
            seeobj_w.append(module._load_lazily(space, name))
        if hasattr(module, 'submodules'):
            for cls in module.submodules.itervalues():
                submod = cls(space, W_Root())
                for name in submod.loaders:
                    seeobj_w.append(submod._load_lazily(space, name))
    #
    space.translates(seeobj_w=seeobj_w,
                     **{'translation.list_comprehension_operations': True})
