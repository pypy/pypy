import weakref, itertools
from pypy.annotation.listdef import ListItem
from pypy.annotation import model as annmodel
from pypy.jit.hintannotator import model as hintmodel
from pypy.rpython.lltypesystem import lltype


class AbstractContainerDef(object):
    __counter = itertools.count()
    __cache   = {}

    def __init__(self, bookkeeper, TYPE):
        self.T = TYPE
        self.bookkeeper = bookkeeper
        # if a virtual container "escapes" control in some way, e.g. by
        # being unified with a SomeLLAbstractVariable, the ContainerDef
        # becomes 'degenerated'.  For the hintrtyper, degenerated
        # SomeLLAbstractContainers should roughly be equivalent to
        # SomeLLAbstractVariables.
        self.degenerated = False
        # hack to try to produce a repr that shows identifications
        key = (self.__class__, TYPE)
        weakdict = AbstractContainerDef.__cache.setdefault(key,
            weakref.WeakValueDictionary())
        weakdict[AbstractContainerDef.__counter.next()] = self

    def __repr__(self):
        items = AbstractContainerDef.__cache[self.__class__, self.T].items()
        keys = [key for key, containerdef in items if containerdef.same_as(self)]
        tag = min(keys)
        if self.degenerated:
            degen = 'degen '
        else:
            degen = ''
        return "<%s%s #%d>" % (degen, self.__class__.__name__, tag)

# ____________________________________________________________

def virtualcontainerdef(bookkeeper, T, vparent=None, vparentindex=0):
    """Build and return a VirtualXxxDef() corresponding to a
    freshly allocated virtual container.
    """
    if isinstance(T, lltype.Struct):
        return VirtualStructDef(bookkeeper, T, vparent, vparentindex)
    elif isinstance(T, lltype.Array):
        return VirtualArrayDef(bookkeeper, T, vparent)
    raise TypeError("unsupported container type %r" % (T,))

def make_item_annotation(bookkeeper, TYPE, vparent=None, vparentindex=0):
    if isinstance(TYPE, lltype.ContainerType):
        vdef = virtualcontainerdef(bookkeeper, TYPE, vparent, vparentindex)
        return hintmodel.SomeLLAbstractContainer(vdef)
    elif isinstance(TYPE, lltype.Ptr):
        return annmodel.s_ImpossibleValue
    else:
        hs_c = hintmodel.SomeLLAbstractConstant(TYPE, {})
        hs_c.const = TYPE._defl()
        return hs_c

def degenerate_item(item, ITEM_TYPE):
    if isinstance(ITEM_TYPE, lltype.ContainerType):
        hs = item.s_value
        assert isinstance(hs, hintmodel.SomeLLAbstractContainer)
        hs.contentdef.mark_degenerated()
    else:
        item.generalize(hintmodel.SomeLLAbstractVariable(ITEM_TYPE))

# ____________________________________________________________

class FieldValue(ListItem):

    def __init__(self, bookkeeper, name, hs_value):
        ListItem.__init__(self, bookkeeper, hs_value)
        self.name = name

    def patch(self):
        for vstructdef in self.itemof:
            vstructdef.fields[self.name] = self


class VirtualStructDef(AbstractContainerDef):
 
    def __init__(self, bookkeeper, TYPE, vparent=None, vparentindex=0):
        AbstractContainerDef.__init__(self, bookkeeper, TYPE)
        self.fields = {}
        self.names = TYPE._names
        for index, name in enumerate(self.names):
            FIELD_TYPE = self.fieldtype(name)
            hs = make_item_annotation(bookkeeper, FIELD_TYPE, vparent=self, vparentindex=index)
            fv = self.fields[name] = FieldValue(bookkeeper, name, hs)
            fv.itemof[self] = True
        self.vparent = vparent
        self.vparentindex = vparentindex

    def cast(self, TO):
        down_or_up = lltype.castable(TO,
                                     lltype.Ptr(self.T))
        # the following works because if a structure is virtual, then
        # all its parent and inlined substructures are also virtual
        vstruct = self
        if down_or_up >= 0:
            for n in range(down_or_up):
                vstruct = vstruct.read_field(vstruct.T._names[0]).contentdef
        else:
            for n in range(-down_or_up):
                vstruct = vstruct.vparent
        assert vstruct
        return vstruct

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
        incompatible = False
        if self.vparent is not None:
            if other.vparent is not None:
                if self.vparent.T != other.vparent.T or self.vparentindex != other.vparentindex:
                    incompatible = True
                else:
                    self.vparent.union(other.vparent)
            else:
                incompatible = True
        elif other.vparent is not None:
            incompatible = True
        if incompatible or self.degenerated or other.degenerated:
            self.mark_degenerated()
            other.mark_degenerated()
        return self

    def generalize_field(self, name, hs_value):
        self.fields[name].generalize(hs_value)

    def mark_degenerated(self):
        if self.degenerated:
            return
        self.degenerated = True
        for name in self.names:
            degenerate_item(self.fields[name], self.fieldtype(name))
        if self.vparent is not None:
            self.vparent.mark_degenerated()

# ____________________________________________________________


class ArrayItem(ListItem):

    def patch(self):
        for varraydef in self.itemof:
            varraydef.arrayitem = self

# this may need to really be used only for fixed size cases
class VirtualArrayDef(AbstractContainerDef):

    def __init__(self, bookkeeper, TYPE, vparent=None):
        AbstractContainerDef.__init__(self, bookkeeper, TYPE)
        hs = make_item_annotation(bookkeeper, TYPE.OF, vparent=self) # xxx vparentindex?
        self.arrayitem = ArrayItem(bookkeeper, hs)
        self.arrayitem.itemof[self] = True
        self.vparent = vparent

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

    def mark_degenerated(self):
        self.degenerated = True
        degenerate_item(self.arrayitem, self.T.OF)
