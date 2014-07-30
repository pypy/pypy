class FatalErrorState(object):
    def __init__(self, space):
        self.enabled = False

def enable(space):
    space.fromcache(FatalErrorState).enabled = True

def disable(space):
    space.fromcache(FatalErrorState).enabled = False

def is_enabled(space):
    return space.wrap(space.fromcache(FatalErrorState).enabled)

def register(space, __args__):
    pass
