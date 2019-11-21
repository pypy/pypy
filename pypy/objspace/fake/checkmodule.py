from pypy.objspace.fake.objspace import FakeObjSpace, W_Root
from pypy.config.pypyoption import get_pypy_config


def checkmodule(modname, translate_startup=True, ignore=(),
                c_compile=False, extra_func=None, config_opts=None):
    """
    Check that the module 'modname' translates.

    Options:
      translate_startup: TODO, document me

      ignore: list of module interpleveldefs/appleveldefs to ignore

      c_compile: determine whether to inokve the C compiler after rtyping

      extra_func: extra function which will be annotated and called. It takes
                  a single "space" argment

      config_opts: dictionary containing extra configuration options which
                   will be passed to TranslationContext
    """
    config = get_pypy_config(translating=True)
    space = FakeObjSpace(config)
    seeobj_w = []
    modules = []
    modnames = [modname]
    for modname in modnames:
        mod = __import__(
            'pypy.module.%s.moduledef' % modname, None, None, ['__doc__'])
        # force computation and record what we wrap
        module = mod.Module(space, W_Root())
        module.setup_after_space_initialization()
        module.init(space)
        modules.append(module)
        for name in module.loaders:
            if name in ignore:
                continue
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

    opts = {'translation.list_comprehension_operations': True}
    opts.update(config_opts)
    space.translates(func, seeobj_w=seeobj_w,
                     c_compile=c_compile, extra_func=extra_func, **opts)
