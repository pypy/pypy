## ----------------------------------------------------------------------------
## dict strategy (see dict_multiobject.py)

from pypy.rlib import rerased
from pypy.objspace.std.dictmultiobject import (AbstractTypedStrategy,
                                               DictStrategy,
                                               IteratorImplementation,
                                               _UnwrappedIteratorMixin)


# this strategy is selected by EmptyDictStrategy.switch_to_correct_strategy
class IdentityDictStrategy(AbstractTypedStrategy, DictStrategy):
    """
    Strategy for custom instances which compares by identity (i.e., the
    default unless you override __hash__, __eq__ or __cmp__).  The storage is
    just a normal RPython dict, which has already the correct by-identity
    semantics.

    Note that at a first sight, you might have problems if you mutate the
    class of an object which is already inside an identitydict.  Consider this
    example::

    class X(object):
        pass
    d = {x(): 1}
    X.__eq__ = ...
    d[y] # might trigger a call to __eq__?

    We want to be sure that x.__eq__ is called in the same cases as in
    CPython.  However, as long as the strategy is IdentityDictStrategy, the
    __eq__ will never be called.

    It turns out that it's not a problem.  In CPython (and in PyPy without
    this strategy), the __eq__ is called if ``hash(y) == hash(x)`` and ``x is
    not y``.  Note that hash(x) is computed at the time when we insert x in
    the dict, not at the time we lookup y.

    Now, how can hash(y) == hash(x)?  There are two possibilities:

      1. we write a custom __hash__ for the class of y, thus making it a not
        "compares by reference" type

      2. the class of y is "compares by reference" type, and by chance the
         hash is the same as x

    In the first case, the getitem immediately notice that y is not of the
    right type, and switches the strategy to ObjectDictStrategy, then the
    lookup works as usual.

    The second case is completely non-deterministic, even in CPython.
    Depending on the phase of the moon, you might call the __eq__ or not, so
    it is perfectly fine to *never* call it.  Morever, in practice with the
    minimar GC we never have two live objects with the same hash, so it would
    never happen anyway.
    """

    erase, unerase = rerased.new_erasing_pair("identitydict")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def wrap(self, unwrapped):
        return unwrapped

    def unwrap(self, wrapped):
        return wrapped

    def get_empty_storage(self):
        return self.erase({})

    def is_correct_type(self, w_obj):
        w_type = self.space.type(w_obj)
        return w_type.compares_by_identity()

    def _never_equal_to(self, w_lookup_type):
        return False

    def iter(self, w_dict):
        return IdentityDictIteratorImplementation(self.space, self, w_dict)

    def keys(self, w_dict):
        return self.unerase(w_dict.dstorage).keys()


class IdentityDictIteratorImplementation(_UnwrappedIteratorMixin, IteratorImplementation):
    pass
