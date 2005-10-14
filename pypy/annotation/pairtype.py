"""
XXX A docstring should go here.
"""

class extendabletype(type):
    """A type with a syntax trick: 'class __extend__(t)' actually extends
    the definition of 't' instead of creating a new subclass."""
    def __new__(cls, name, bases, dict):
        if name == '__extend__':
            cls = bases[0]   # override data into the existing base
            for key, value in dict.items():
                if key == '__module__':
                    continue
                    # XXX do we need to provide something more for pickling?
                setattr(cls, key, value)
            return None
        else:
            return super(extendabletype, cls).__new__(cls, name, bases, dict)


def pair(a, b):
    """Return a pair object."""
    tp = pairtype(a.__class__, b.__class__)
    return tp((a, b))   # tp is a subclass of tuple

pairtypecache = {}

def pairtype(cls1, cls2):
    """type(pair(a,b)) is pairtype(a.__class__, b.__class__)."""
    try:
        pair = pairtypecache[cls1, cls2]
    except KeyError:
        name = 'pairtype(%s, %s)' % (cls1.__name__, cls2.__name__)
        bases1 = [pairtype(base1, cls2) for base1 in cls1.__bases__]
        bases2 = [pairtype(cls1, base2) for base2 in cls2.__bases__]
        bases = tuple(bases1 + bases2) or (tuple,)  # 'tuple': ultimate base
        pair = pairtypecache[cls1, cls2] = extendabletype(name, bases, {})
    return pair
