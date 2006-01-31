import weakref

def getstate_with_slots(self):
    result = []
    for cls in self.__class__.__mro__:
        if not hasattr(cls, '__slots__'):
            continue
        for attr in cls.__slots__:
            if attr in ("__weakref__", "__dict__"):
                continue
            if hasattr(self, attr):
                result.append((True, attr, getattr(self, attr)))
            else:
                result.append((False, attr, None))
    if hasattr(self, "__dict__"):
        return result, self.__dict__ 
    else:
        return result, None

def setstate_with_slots(self, (state, __dict__)):
    for i, (is_set, attr, value) in enumerate(state):
        if is_set:
            # circumvent eventual __setattr__
            desc = getattr(self.__class__, attr, None)
            if desc is None:
                setattr(self, attr, value)
            else:
                desc.__set__(self, value)
    if __dict__ is not None:
        self.__dict__ = __dict__


class pickleable_weakref(object):
    __slots__ = "ref"
    
    def __init__(self, obj):
        self.ref = weakref.ref(obj)

    def __call__(self):
        return self.ref()

    def __getstate__(self):
        return self.ref()

    def __setstate__(self, obj):
        self.ref = weakref.ref(obj)

    def __repr__(self):
        return repr(self.ref)

