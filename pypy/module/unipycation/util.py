def get_from_module(space, module, name):
    w_module = space.getbuiltinmodule(module)
    return space.getattr(w_module, space.wrap(name))
