from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp import executor

# a bit of hack because compile.py imports specnode.py directly too
from pypy.jit.metainterp.specnode import SpecNode, NotSpecNode


prebuiltNotSpecNode = NotSpecNode()


class FixedClassSpecNode(SpecNode):
    def __init__(self, known_class):
        self.known_class = known_class

    def mutate_nodes(self, instnode):
        from pypy.jit.metainterp.optimize4 import InstanceNode
        
        if instnode.cls is None:
            instnode.cls = InstanceNode(self.known_class, const=True)
        else:
            assert instnode.cls.source.equals(self.known_class)

    def equals(self, other):
        if type(other) is not FixedClassSpecNode:
            return False
        else:
            assert isinstance(other, FixedClassSpecNode) # make annotator happy
            return self.known_class.equals(other.known_class)

    def matches(self, instnode):
        if instnode.cls is None:
            return False
        return instnode.cls.source.equals(self.known_class)


class SpecNodeWithFields(FixedClassSpecNode):
    def __init__(self, known_class, fields):
        FixedClassSpecNode.__init__(self, known_class)
        self.fields = fields

    def mutate_nodes(self, instnode):
        from pypy.jit.metainterp.optimize4 import av_eq, av_hash
        from pypy.rlib.objectmodel import r_dict
        
        FixedClassSpecNode.mutate_nodes(self, instnode)
        curfields = r_dict(av_eq, av_hash)
        for ofs, subspecnode in self.fields:
            subinstnode = instnode.origfields[ofs]
            # should really be there
            subspecnode.mutate_nodes(subinstnode)
            curfields[ofs] = subinstnode
        instnode.curfields = curfields

    def equals(self, other):
        if not self.known_class.equals(other.known_class):
            return False
        elif len(self.fields) != len(other.fields):
            return False
        else:
            for i in range(len(self.fields)):
                key, value = self.fields[i]
                otherkey, othervalue = other.fields[i]
                if key != otherkey:
                    return False
                if not value.equals(othervalue):
                    return False
            return True

    def matches(self, instnode):
        if not FixedClassSpecNode.matches(self, instnode):
            return False
        for key, value in self.fields:
            if key not in instnode.curfields:
                return False
            if value is not None and not value.matches(instnode.curfields[key]):
                return False
        return True

    def expand_boxlist(self, instnode, newboxlist):
        for ofs, subspecnode in self.fields:
            subinstnode = instnode.curfields[ofs]  # should really be there
            subspecnode.expand_boxlist(subinstnode, newboxlist)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        for ofs, subspecnode in self.fields:
            from pypy.jit.metainterp.history import AbstractDescr
            assert isinstance(ofs, AbstractDescr)
            fieldbox = executor.execute(cpu, rop.GETFIELD_GC,
                                        [valuebox], ofs)
            subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

    def adapt_to(self, instnode, offsets):
        for ofs, subspecnode in self.fields:
            subspecnode.adapt_to(instnode.curfields[ofs], offsets)


class VirtualInstanceSpecNode(SpecNodeWithFields):

    def adapt_to(self, instnode, offsets):
        instnode.virtual = True
        SpecNodeWithFields.adapt_to(self, instnode, offsets)

    def mutate_nodes(self, instnode):
        SpecNodeWithFields.mutate_nodes(self, instnode)
        instnode.virtual = True

    def equals(self, other):
        if not isinstance(other, VirtualInstanceSpecNode):
            return False
        return SpecNodeWithFields.equals(self, other)
