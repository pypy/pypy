from pypy.tool.pairtype import extendabletype


class SpecNode(object):
    __metaclass__ = extendabletype     # extended in optimizefindnode.py
    __slots__ = ()


class NotSpecNode(SpecNode):
    __slots__ = ()

    def equals(self, other):
        return isinstance(other, NotSpecNode)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)


prebuiltNotSpecNode = NotSpecNode()


class VirtualInstanceSpecNode(SpecNode):
    def __init__(self, known_class, fields):
        self.known_class = known_class
        self.fields = fields    # list: [(fieldofs, subspecnode)]

    def equals(self, other):
        if not (isinstance(other, VirtualInstanceSpecNode) and
                self.known_class.equals(other.known_class) and
                len(self.fields) == len(other.fields)):
            return False
        for i in range(len(self.fields)):
            o1, s1 = self.fields[i]
            o2, s2 = other.fields[i]
            if not (o1.sort_key() == o2.sort_key() and s1.equals(s2)):
                return False
        return True

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        from pypy.jit.metainterp import executor, history, resoperation
        for ofs, subspecnode in self.fields:
            assert isinstance(ofs, history.AbstractDescr)
            fieldbox = executor.execute(cpu, resoperation.rop.GETFIELD_GC,
                                        [valuebox], ofs)
            subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)


class VirtualArraySpecNode(SpecNode):
    def __init__(self, arraydescr, items):
        self.arraydescr = arraydescr
        self.items = items      # list of subspecnodes

    def equals(self, other):
        if not (isinstance(other, VirtualArraySpecNode) and
                len(self.items) == len(other.items)):
            return False
        assert self.arraydescr == other.arraydescr
        for i in range(len(self.items)):
            s1 = self.items[i]
            s2 = other.items[i]
            if not s1.equals(s2):
                return False
        return True

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        from pypy.jit.metainterp import executor, history, resoperation
        for i in range(len(self.items)):
            itembox = executor.execute(cpu, resoperation.rop.GETARRAYITEM_GC,
                                       [valuebox, history.ConstInt(i)],
                                       self.arraydescr)
            subspecnode = self.items[i]
            subspecnode.extract_runtime_data(cpu, itembox, resultlist)


def equals_specnodes(specnodes1, specnodes2):
    assert len(specnodes1) == len(specnodes2)
    for i in range(len(specnodes1)):
        if not specnodes1[i].equals(specnodes2[i]):
            return False
    return True
