from pypy.objspace.fake.objspace import FakeObjSpace, W_Root
from pypy.config.pypyoption import get_pypy_config


def checkmodule(*modnames):
    config = get_pypy_config(translating=True)
    space = FakeObjSpace(config)
    for modname in modnames:
        mod = __import__('pypy.module.%s' % modname, None, None, ['__doc__'])
        # force computation and record what we wrap
        module = mod.Module(space, W_Root())
        for name in module.loaders:
            module._load_lazily(space, name)
    #
    space.translates(**{'translation.list_comprehension_operations': True})
