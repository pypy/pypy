from pypy.annotation.listdef import ListItem
from pypy.jit import hintmodel
from pypy.rpython.lltypesystem import lltype

class FieldValue(ListItem):

    def __init__(self, bookkeeper, name, hs_value):
        ListItem.__init__(self, bookkeeper, hs_value)
        self.name = name

    def patch(self):
        for vstructdef in self.itemof:
            vstructdef.fields[self.name] = self


class VirtualStructDef:
 
    def __init__(self, bookkeeper, TYPE):
        self.T = TYPE
        self.bookkeeper = bookkeeper
        self.fields = {}
        self.names = TYPE._names
        for name in self.names:
            FIELD_TYPE = self.fieldtype(name)
            if isinstance(FIELD_TYPE, lltype.ContainerType):
                assert isinstance(FIELD_TYPE, lltype.Struct)   # for now
                vstructdef = VirtualStructDef(bookkeeper, FIELD_TYPE)
                hs = hintmodel.SomeLLAbstractContainer(vstructdef)
            else:
                hs = hintmodel.SomeLLAbstractConstant(FIELD_TYPE, {})
            fv = self.fields[name] = FieldValue(bookkeeper, name, hs)
            fv.itemof[self] = True

    def fieldtype(self, name):
        return getattr(self.T, name)

    def read_field(self, name):
        fv = self.fields[name]
        fv.read_locations[self.bookkeeper.position_key] = True
        return fv.s_value

    def same_as(self, other):
        return self.fields == other.fields

    def union(self, other):
        assert self.T == other.T
        for name in self.names:
            self.fields[name].merge(other.fields[name])
        return self

    def generalize_field(self, name, hs_value):
        self.fields[name].generalize(hs_value)

    def __repr__(self):
        return "<VirtualStructDef '%s'>" % (self.T._name,)
