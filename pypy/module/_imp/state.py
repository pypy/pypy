from pypy.interpreter.gateway import unwrap_spec

class State:
    def __init__(self, space):
        self.space = space
        self.override_frozen_modules = 0

    def set_override_frozen(self, override):
        self.override_frozen_modules = override

def get(space):
    return space.fromcache(State)

@unwrap_spec(override=int)
def set_override_frozen(space, override):
    state = get(space)
    return state.set_override_frozen(override)
