from pypy.annotation.listdef import ListItem
from pypy.annotation import model as annmodel
from pypy.jit import hintmodel
from pypy.rpython.lltypesystem import lltype

def virtualcontainerdef(bookkeeper, T):
    """Build and return a VirtualXxxDef() corresponding to a
    freshly allocated virtual container.
    """
    if isinstance(T, lltype.Struct):
        cls = VirtualStructDef
    elif isinstance(T, lltype.Array):
        cls = VirtualArrayDef
    else:
        raise TypeError("unsupported container type %r" % (T,))
    return cls(bookkeeper, T)

def make_item_annotation(bookkeeper, TYPE):
    if isinstance(TYPE, lltype.ContainerType):
        vdef = virtualcontainerdef(bookkeeper, TYPE)
        return hintmodel.SomeLLAbstractContainer(vdef)
    elif isinstance(TYPE, lltype.Ptr):
        return annmodel.s_ImpossibleValue
    else:
        return hintmodel.SomeLLAbstractConstant(TYPE, {})

# ____________________________________________________________

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
            hs = make_item_annotation(bookkeeper, FIELD_TYPE)
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

# ____________________________________________________________


class ArrayItem(ListItem):

    def patch(self):
        for varraydef in self.itemof:
            varraydef.arrayitem = self


class VirtualArrayDef:

    def __init__(self, bookkeeper, TYPE):
        self.T = TYPE
        self.bookkeeper = bookkeeper
        hs = make_item_annotation(bookkeeper, TYPE.OF)
        self.arrayitem = ArrayItem(bookkeeper, hs)
        self.arrayitem.itemof[self] = True

    def read_item(self):
        self.arrayitem.read_locations[self.bookkeeper.position_key] = True
        return self.arrayitem.s_value

    def same_as(self, other):
        return self.arrayitem is other.arrayitem

    def union(self, other):
        assert self.T == other.T
        self.arrayitem.merge(other.arrayitem)
        return self

    def generalize_item(self, hs_value):
        self.arrayitem.generalize(hs_value)

    def __repr__(self):
        return "<VirtualArrayDef of %r>" % (self.T.OF,)
