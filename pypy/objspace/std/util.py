from pypy.interpreter import gateway

def negate(f):
    """Create a function which calls `f` and negates its result.  When the
    result is ``space.w_NotImplemented``, ``space.w_NotImplemented`` is
    returned. This is useful for complementing e.g. the __ne__ descriptor if
    your type already defines a __eq__ descriptor.
    """
    def _negator(self, space, w_other):
        # no need to use space.is_ / space.not_
        tmp = f(self, space, w_other)
        if tmp is space.w_NotImplemented:
            return space.w_NotImplemented
        return space.newbool(tmp is space.w_False)
    _negator.func_name = 'negate-%s' % f.func_name
    return _negator

def get_positive_index(where, length):
    if where < 0:
        where += length
        if where < 0:
            where = 0
    elif where > length:
        where = length
    assert where >= 0
    return where

app = gateway.applevel(r'''
    def _classdir(klass):
        """__dir__ for type objects

        This includes all attributes of klass and all of the base
        classes recursively.
        """
        names = set()
        ns = getattr(klass, '__dict__', None)
        if ns is not None:
            names.update(ns)
        bases = getattr(klass, '__bases__', None)
        if bases is not None:
            # Note that since we are only interested in the keys, the order
            # we merge classes is unimportant
            for base in bases:
                names.update(_classdir(base))
        return names

    def _objectdir(obj):
        """__dir__ for generic objects

         Returns __dict__, __class__ and recursively up the
         __class__.__bases__ chain.
        """
        names = set()
        ns = getattr(obj, '__dict__', None)
        if isinstance(ns, dict):
            names.update(ns)
        klass = getattr(obj, '__class__', None)
        if klass is not None:
            names.update(_classdir(klass))
        return names
''', filename=__file__)

_classdir = app.interphook('_classdir')
_objectdir = app.interphook('_objectdir')
