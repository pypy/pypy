from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import unwrap_spec


@unwrap_spec(index=int)
def injected_getitem(space, w_self, index):
    return space.wrap(index * 42)


injected_methods = {
    '__getitem__': interp2app(injected_getitem),
}

def inject(space, name, dict_w, pto):
    assert name == 'test_module.test_mytype'
    for key, value in injected_methods.items():
        dict_w[key] = space.wrap(value)
