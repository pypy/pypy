from pypy.config.config import OptionDescription, Config

def combine_config(c1, c2, name, desc='', overrides=None, translating=False):
    if overrides is None:
        overrides = {}
    children = c1._cfgimpl_descr._children + c2._cfgimpl_descr._children
    children = [c for c in children if c._name != 'help']
    odescr = OptionDescription(name, desc, children)
    config = Config(odescr, **overrides)
    if translating:
        config.translating = True
    for c in c1, c2:
        for child in c._cfgimpl_descr._children:
            if child._name == 'help':
                continue
            value = getattr(c, child._name)
            config._cfgimpl_values[child._name] = value
    return config

