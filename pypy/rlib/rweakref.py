"""
Weakref support in RPython.  Supports ref() without callbacks,
and a limited version of WeakValueDictionary.  LLType only for now!
"""

import weakref
from weakref import ref


class RWeakValueDictionary(object):
    """A limited dictionary containing weak values.
    Only supports string keys.
    """

    def __init__(self, valueclass):
        self._dict = weakref.WeakValueDictionary()
        self._valueclass = valueclass

    def get(self, key):
        return self._dict.get(key, None)

    def set(self, key, value):
        if value is None:
            self._dict.pop(key, None)
        else:
            assert isinstance(value, self._valueclass)
            self._dict[key] = value


# ____________________________________________________________

from pypy.rpython import extregistry
from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.tool.pairtype import pairtype

class SomeWeakValueDict(annmodel.SomeObject):
    knowntype = RWeakValueDictionary

    def __init__(self, valueclassdef):
        self.valueclassdef = valueclassdef

    def rtyper_makerepr(self, rtyper):
        from pypy.rlib import rweakrefimpl
        return rweakrefimpl.WeakValueDictRepr(rtyper)

    def rtyper_makekey_ex(self, rtyper):
        return self.__class__,

    def method_get(self, s_key):
        assert isinstance(s_key, annmodel.SomeString)
        return annmodel.SomeInstance(self.valueclassdef, can_be_None=True)

    def method_set(self, s_key, s_value):
        s_oldvalue = self.method_get(s_key)
        assert s_oldvalue.contains(s_value)

class __extend__(pairtype(SomeWeakValueDict, SomeWeakValueDict)):
    def union((s_wvd1, s_wvd2)):
        if s_wvd1.valueclassdef is not s_wvd2.valueclassdef:
            return SomeObject() # not the same class! complain...
        return SomeWeakValueDict(s_wvd1.valueclassdef)

class Entry(extregistry.ExtRegistryEntry):
    _about_ = RWeakValueDictionary

    def compute_result_annotation(self, s_valueclass):
        assert isinstance(s_valueclass, annmodel.SomePBC)
        assert s_valueclass.is_constant()
        [desc] = s_valueclass.descriptions
        return SomeWeakValueDict(desc.getuniqueclassdef())

    def specialize_call(self, hop):
        from pypy.rlib import rweakrefimpl
        return rweakrefimpl.specialize_make_weakdict(hop)

class Entry(extregistry.ExtRegistryEntry):
    _type_ = RWeakValueDictionary

    def compute_annotation(self):
        bk = self.bookkeeper
        x = self.instance
        return SomeWeakValueDict(bk.getuniqueclassdef(x._valueclass))
