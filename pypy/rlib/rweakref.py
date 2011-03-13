"""
Weakref support in RPython.  Supports ref() without callbacks,
a form of WeakKeyDictionary, and a limited version of WeakValueDictionary.
LLType only for now!
"""

import weakref


class RWeakValueDictionary(object):
    """A dictionary containing weak values."""

    def __init__(self, keyclass, valueclass):
        self._dict = weakref.WeakValueDictionary()
        self._keyclass = keyclass
        self._valueclass = valueclass

    def get(self, key):
        assert isinstance(key, self._keyclass)
        return self._dict.get(key, None)

    def set(self, key, value):
        assert isinstance(key, self._keyclass)
        if value is None:
            self._dict.pop(key, None)
        else:
            assert isinstance(value, self._valueclass)
            self._dict[key] = value


class RWeakKeyDictionary(object):
    """A dictionary containing weak keys.
    Keys and values must be instances.
    Prebuilt RWeakKeyDictionaries must be empty.
    """

    def __init__(self, keyclass, valueclass):
        self._dict = weakref.WeakKeyDictionary()
        self._keyclass = keyclass
        self._valueclass = valueclass

    def get(self, key):
        """Get the value associated to 'key', or None by default."""
        assert isinstance(key, self._keyclass)
        return self._dict.get(key, None)

    def set(self, key, value):
        """Set the key/value pair (or delete it if value is None)."""
        assert isinstance(key, self._keyclass)
        if value is None:
            self._dict.pop(key, None)
        else:
            assert isinstance(value, self._valueclass)
            self._dict[key] = value

    def length(self):
        """Mostly for debugging.  Slow, don't use in real code."""
        return len(self._dict)


# ____________________________________________________________

from pypy.rpython import extregistry
from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.tool.pairtype import pairtype

class SomeWeakValueDict(annmodel.SomeObject):
    knowntype = RWeakValueDictionary

    def __init__(self, s_key, valueclassdef):
        self.s_key = s_key
        self.valueclassdef = valueclassdef

    def rtyper_makerepr(self, rtyper):
        from pypy.rlib import _rweakvaldict
        return _rweakvaldict.WeakValueDictRepr(rtyper,
                                               rtyper.makerepr(self.s_key))

    def rtyper_makekey_ex(self, rtyper):
        return self.__class__,

    def method_get(self, s_key):
        return annmodel.SomeInstance(self.valueclassdef, can_be_None=True)

    def method_set(self, s_key, s_value):
        s_oldvalue = self.method_get(s_key)
        assert s_oldvalue.contains(s_value)

class __extend__(pairtype(SomeWeakValueDict, SomeWeakValueDict)):
    def union((s_wvd1, s_wvd2)):
        if s_wvd1.valueclassdef is not s_wvd2.valueclassdef:
            return annmodel.SomeObject() # not the same class! complain...
        s_key = annmodel.unionof(s_wvd1.s_key, s_wvd2.s_key)
        return SomeWeakValueDict(s_key, s_wvd1.valueclassdef)

class Entry(extregistry.ExtRegistryEntry):
    _about_ = RWeakValueDictionary

    def compute_result_annotation(self, s_keyclass, s_valueclass):
        assert s_keyclass.is_constant()
        s_key = self.bookkeeper.immutablevalue(s_keyclass.const())
        return SomeWeakValueDict(
            s_key,
            _getclassdef(s_valueclass))

    def specialize_call(self, hop):
        from pypy.rlib import _rweakvaldict
        return _rweakvaldict.specialize_make_weakdict(hop)

class Entry(extregistry.ExtRegistryEntry):
    _type_ = RWeakValueDictionary

    def compute_annotation(self):
        bk = self.bookkeeper
        x = self.instance
        return SomeWeakValueDict(
            bk.immutablevalue(x._keyclass()),
            bk.getuniqueclassdef(x._valueclass))

def _getclassdef(s_instance):
    assert isinstance(s_instance, annmodel.SomePBC)
    assert s_instance.is_constant()
    [desc] = s_instance.descriptions
    return desc.getuniqueclassdef()

# ____________________________________________________________

class SomeWeakKeyDict(annmodel.SomeObject):
    knowntype = RWeakKeyDictionary

    def __init__(self, keyclassdef, valueclassdef):
        self.keyclassdef = keyclassdef
        self.valueclassdef = valueclassdef

    def rtyper_makerepr(self, rtyper):
        from pypy.rlib import _rweakkeydict
        return _rweakkeydict.WeakKeyDictRepr(rtyper)

    def rtyper_makekey_ex(self, rtyper):
        return self.__class__,

    def method_get(self, s_key):
        assert isinstance(s_key, annmodel.SomeInstance)
        assert s_key.classdef.issubclass(self.keyclassdef)
        return annmodel.SomeInstance(self.valueclassdef, can_be_None=True)

    def method_set(self, s_key, s_value):
        s_oldvalue = self.method_get(s_key)
        assert s_oldvalue.contains(s_value)

    def method_length(self):
        return annmodel.SomeInteger(nonneg=True)

class __extend__(pairtype(SomeWeakKeyDict, SomeWeakKeyDict)):
    def union((s_wkd1, s_wkd2)):
        if s_wkd1.keyclassdef is not s_wkd2.keyclassdef:
            return SomeObject() # not the same key class! complain...
        if s_wkd1.valueclassdef is not s_wkd2.valueclassdef:
            return SomeObject() # not the same value class! complain...
        return SomeWeakKeyDict(s_wkd1.keyclassdef, s_wkd1.valueclassdef)

class Entry(extregistry.ExtRegistryEntry):
    _about_ = RWeakKeyDictionary

    def compute_result_annotation(self, s_keyclass, s_valueclass):
        return SomeWeakKeyDict(_getclassdef(s_keyclass),
                               _getclassdef(s_valueclass))

    def specialize_call(self, hop):
        from pypy.rlib import _rweakkeydict
        return _rweakkeydict.specialize_make_weakdict(hop)

class Entry(extregistry.ExtRegistryEntry):
    _type_ = RWeakKeyDictionary

    def compute_annotation(self):
        bk = self.bookkeeper
        x = self.instance
        return SomeWeakKeyDict(bk.getuniqueclassdef(x._keyclass),
                               bk.getuniqueclassdef(x._valueclass))
