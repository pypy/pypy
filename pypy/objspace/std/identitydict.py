from pypy.rlib import rerased
from pypy.objspace.std.dictmultiobject import (AbstractTypedStrategy,
                                               DictStrategy,
                                               IteratorImplementation,
                                               _UnwrappedIteratorMixin)


# a global (per-space) version counter to track live instances which "compare
# by identity" (i.e., whose __eq__, __cmp__ and __hash__ are the default
# ones).  The idea is to track only classes for which we checked the
# compares_by_identity() status at least once: we increment the version if its
# status might change, e.g. because we set one of those attributes.  The
# actual work is done by W_TypeObject.mutated() and objecttype:descr_setclass

def bump_global_version(space):
    if space.config.objspace.std.withidentitydict:
        space.fromcache(ComparesByIdentityVersion).bump()

def get_global_version(space):
    if space.config.objspace.std.withidentitydict:
        return space.fromcache(ComparesByIdentityVersion).get()
    return None

class ComparesByIdentityVersion(object):

    def __init__(self, space):
        self.bump()

    def bump(self):
        from pypy.objspace.std.typeobject import VersionTag
        self._version = VersionTag()

    def get(self):
        return self._version



## ----------------------------------------------------------------------------
## dict strategy (see dict_multiobject.py)

# this strategy is selected by EmptyDictStrategy.switch_to_correct_strategy
class IdentityDictStrategy(AbstractTypedStrategy, DictStrategy):
    """
    Strategy for custom instances which compares by identity (i.e., the
    default unless you override __hash__, __eq__ or __cmp__).  The storage is
    just a normal RPython dict, which has already the correct by-identity
    semantics.
    """

    _erase_tuple, _unerase_tuple = rerased.new_erasing_pair("identitydict")
    _erase_tuple = staticmethod(_erase_tuple)
    _unerase_tuple = staticmethod(_unerase_tuple)

    def wrap(self, unwrapped):
        return unwrapped

    def unwrap(self, wrapped):
        return wrapped

    def erase(self, d):
        current_version = get_global_version(self.space)
        return self._erase_tuple((current_version, d))

    def unerase(self, dstorage):
        version, d = self._unerase_tuple(dstorage)
        return d

    def get_current_version(self, dstorage):
        version, d = self._unerase_tuple(dstorage)
        return version

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
