from pypy.annotation.model import SomeObject, SomeImpossibleValue
from pypy.annotation.listdef import ListItem


class DictKey(ListItem):
    def patch(self):
        for dictdef in self.itemof:
            dictdef.dictkey = self

class DictValue(ListItem):
    def patch(self):
        for dictdef in self.itemof:
            dictdef.dictvalue = self


class DictDef:
    """A dict definition remembers how general the keys and values in that
    particular dict have to be.  Every dict creation makes a new DictDef,
    and the union of two dicts merges the DictKeys and DictValues that each
    DictDef stores."""

    def __init__(self, bookkeeper, s_key = SomeImpossibleValue(),
                                 s_value = SomeImpossibleValue()):
        self.dictkey = DictKey(bookkeeper, s_key)
        self.dictkey.itemof[self] = True
        self.dictvalue = DictValue(bookkeeper, s_value)
        self.dictvalue.itemof[self] = True
        self.bookkeeper = bookkeeper

    def read_key(self, position_key=None):
        if position_key is None:
            if self.bookkeeper is None:   # for tests
                from pypy.annotation.bookkeeper import getbookkeeper
                position_key = getbookkeeper().position_key
            else:
                position_key = self.bookkeeper.position_key
        self.dictkey.read_locations[position_key] = True
        return self.dictkey.s_value

    def read_value(self, position_key=None):
        if position_key is None:
            if self.bookkeeper is None:   # for tests
                from pypy.annotation.bookkeeper import getbookkeeper
                position_key = getbookkeeper().position_key
            else:
                position_key = self.bookkeeper.position_key
        self.dictvalue.read_locations[position_key] = True
        return self.dictvalue.s_value

    def same_as(self, other):
        return (self.dictkey is other.dictkey and
                self.dictvalue is other.dictvalue)

    def union(self, other):
        if (self.same_as(MOST_GENERAL_DICTDEF) or
            other.same_as(MOST_GENERAL_DICTDEF)):
            return MOST_GENERAL_DICTDEF   # without merging
        else:
            self.dictkey.merge(other.dictkey)
            self.dictvalue.merge(other.dictvalue)
            return self

    def generalize_key(self, s_key):
        self.dictkey.generalize(s_key)

    def generalize_value(self, s_value):
        self.dictvalue.generalize(s_value)

    def __repr__(self):
        return '<%r: %r>' % (self.dictkey.s_value, self.dictvalue.s_value)


MOST_GENERAL_DICTDEF = DictDef(None, SomeObject(), SomeObject())
