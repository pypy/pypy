from pypy.tool.pairtype import extendabletype
from pypy.jit.metainterp.history import Const


class SpecNode(object):
    __metaclass__ = extendabletype     # extended in optimizefindnode.py
    __slots__ = ()

    def equals(self, other, ge):     # 'ge' stands for greater-or-equal;
        raise NotImplementedError    # if false, the default is 'equal'.
 
    def extract_runtime_data(self, cpu, valuebox, resultlist):
        raise NotImplementedError


class NotSpecNode(SpecNode):
    __slots__ = ()

    def equals(self, other, ge):
        return isinstance(other, NotSpecNode) or ge

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)


prebuiltNotSpecNode = NotSpecNode()


class ConstantSpecNode(SpecNode):
    def __init__(self, constbox):
        assert isinstance(constbox, Const)
        self.constbox = constbox

    def equals(self, other, ge):
        return isinstance(other, ConstantSpecNode) and \
               self.constbox.same_constant(other.constbox)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        pass


class AbstractVirtualStructSpecNode(SpecNode):
    def __init__(self, fields):
        self.fields = fields    # list: [(fieldofs, subspecnode)]

    def equal_fields(self, other, ge):
        if len(self.fields) != len(other.fields):
            return False
        for i in range(len(self.fields)):
            o1, s1 = self.fields[i]
            o2, s2 = other.fields[i]
            if not (o1 is o2 and s1.equals(s2, ge)):
                return False
        return True

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        from pypy.jit.metainterp import executor, history, resoperation
        for ofs, subspecnode in self.fields:
            assert isinstance(ofs, history.AbstractDescr)
            fieldbox = executor.execute(cpu, resoperation.rop.GETFIELD_GC,
                                        ofs, valuebox)
            subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)


class VirtualInstanceSpecNode(AbstractVirtualStructSpecNode):
    def __init__(self, known_class, fields):
        AbstractVirtualStructSpecNode.__init__(self, fields)
        assert isinstance(known_class, Const)
        self.known_class = known_class

    def equals(self, other, ge):
        if not (isinstance(other, VirtualInstanceSpecNode) and
                self.known_class.same_constant(other.known_class)):
            return False
        return self.equal_fields(other, ge)


class VirtualArraySpecNode(SpecNode):
    def __init__(self, arraydescr, items):
        self.arraydescr = arraydescr
        self.items = items      # list of subspecnodes

    def equals(self, other, ge):
        if not (isinstance(other, VirtualArraySpecNode) and
                len(self.items) == len(other.items)):
            return False
        assert self.arraydescr == other.arraydescr
        for i in range(len(self.items)):
            s1 = self.items[i]
            s2 = other.items[i]
            if not s1.equals(s2, ge):
                return False
        return True

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        from pypy.jit.metainterp import executor, history, resoperation
        for i in range(len(self.items)):
            itembox = executor.execute(cpu, resoperation.rop.GETARRAYITEM_GC,
                                       self.arraydescr,
                                       valuebox, history.ConstInt(i))
            subspecnode = self.items[i]
            subspecnode.extract_runtime_data(cpu, itembox, resultlist)


class VirtualStructSpecNode(AbstractVirtualStructSpecNode):
    def __init__(self, typedescr, fields):
        AbstractVirtualStructSpecNode.__init__(self, fields)
        self.typedescr = typedescr

    def equals(self, other, ge):
        if not isinstance(other, VirtualStructSpecNode):
            return False
        assert self.typedescr == other.typedescr
        return self.equal_fields(other, ge)


def equals_specnodes(specnodes1, specnodes2, ge=False):
    assert len(specnodes1) == len(specnodes2)
    for i in range(len(specnodes1)):
        if not specnodes1[i].equals(specnodes2[i], ge):
            return False
    return True

def more_general_specnodes(specnodes1, specnodes2):
    return equals_specnodes(specnodes1, specnodes2, ge=True)
