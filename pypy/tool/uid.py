import struct

# This is temporary hack to run PyPy on PyPy
# until PyPy's struct module handle P format character.
try:
    HUGEVAL = 256 ** struct.calcsize('P')
except struct.error:
    HUGEVAL = 0

def fixid(result):
    if result < 0:
        result += HUGEVAL
    return result

def uid(obj):
    """
    Return the id of an object as an unsigned number so that its hex
    representation makes sense
    """
    return fixid(id(obj))


class Hashable(object):
    """
    A Hashable instance encapsulates any object, but is always usable as a
    key in dictionaries.  This is based on id() for mutable objects and on
    real hash/compare for immutable ones.
    """
    __slots__ = ["key", "value"]
    
    def __init__(self, value):
        self.value = value     # a concrete value
        # try to be smart about constant mutable or immutable values
        key = type(self.value), self.value  # to avoid confusing e.g. 0 and 0.0
        try:
            hash(key)
        except TypeError:
            key = id(self.value)
        self.key = key

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self.key == other.key

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.key)

    def __repr__(self):
        return '(%s)' % (self,)

    def __str__(self):
        # try to limit the size of the repr to make it more readable
        r = repr(self.value)
        if (r.startswith('<') and r.endswith('>') and
            hasattr(self.value, '__name__')):
            r = '%s %s' % (type(self.value).__name__, self.value.__name__)
        elif len(r) > 60 or (len(r) > 30 and type(self.value) is not str):
            r = r[:20] + '...' + r[-8:]
        return r
