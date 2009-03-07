from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.history import ConstInt
from pypy.jit.metainterp import executor

class SpecNode(object):

    def expand_boxlist(self, instnode, newboxlist, start):
        newboxlist.append(instnode.source)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)

    def adapt_to(self, instnode):
        instnode.escaped = True

    def mutate_nodes(self, instnode):
        raise NotImplementedError

    def equals(self, other):
        raise NotImplementedError

    def matches(self, other):
        raise NotImplementedError

class NotSpecNode(SpecNode):
    def mutate_nodes(self, instnode):
        instnode.cursize = -1

    def equals(self, other):
        if type(other) is NotSpecNode:
            return True
        return False

    def matches(self, other):
        # NotSpecNode matches everything
        return True

class SpecNodeWithBox(NotSpecNode):
    # XXX what is this class used for?
    def __init__(self, box):
        self.box = box
    
    def equals(self, other):
        if type(other) is SpecNodeWithBox:
            return True
        return False

class FixedClassSpecNode(SpecNode):
    def __init__(self, known_class):
        self.known_class = known_class

    def mutate_nodes(self, instnode):
        from pypy.jit.metainterp.optimize import InstanceNode
        
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

##class FixedListSpecNode(FixedClassSpecNode):

##    def equals(self, other):
##        if type(other) is not FixedListSpecNode:
##            return False
##        else:
##            assert isinstance(other, FixedListSpecNode) # make annotator happy
##            return self.known_class.equals(other.known_class)

class SpecNodeWithFields(FixedClassSpecNode):
    def __init__(self, known_class, fields):
        FixedClassSpecNode.__init__(self, known_class)
        self.fields = fields

    def mutate_nodes(self, instnode):
        FixedClassSpecNode.mutate_nodes(self, instnode)
        curfields = {}
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
        # XXX think about details of virtual vs virtualizable
        if not FixedClassSpecNode.matches(self, instnode):
            return False
        for key, value in self.fields:
            if key not in instnode.curfields:
                return False
            if value is not None and not value.matches(instnode.curfields[key]):
                return False
        return True

    def expand_boxlist(self, instnode, newboxlist, start):
        for ofs, subspecnode in self.fields:
            subinstnode = instnode.curfields[ofs]  # should really be there
            subspecnode.expand_boxlist(subinstnode, newboxlist, start)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        for ofs, subspecnode in self.fields:
            fieldbox = executor.execute(cpu, rop.GETFIELD_GC,
                                        [valuebox], ofs)
            subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

    def adapt_to(self, instnode):
        for ofs, subspecnode in self.fields:
            subspecnode.adapt_to(instnode.curfields[ofs])

class VirtualizedSpecNode(SpecNodeWithFields):

    def expand_boxlist(self, instnode, newboxlist, start):
        newboxlist.append(instnode.source)
        SpecNodeWithFields.expand_boxlist(self, instnode, newboxlist, start)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)
        SpecNodeWithFields.extract_runtime_data(self, cpu, valuebox, resultlist)

    def adapt_to(self, instnode):
        instnode.escaped = True
        SpecNodeWithFields.adapt_to(self, instnode)

class DelayedSpecNode(VirtualizedSpecNode):

    def expand_boxlist(self, instnode, newboxlist, oplist):
        newboxlist.append(instnode.source)
        for ofs, subspecnode in self.fields:
            assert isinstance(subspecnode, SpecNodeWithBox)
            if oplist is None:
                instnode.cleanfields[ofs] = instnode.origfields[ofs]
                newboxlist.append(instnode.curfields[ofs].source)
            else:
                if ofs in instnode.cleanfields:
                    newboxlist.append(instnode.cleanfields[ofs].source)
                else:
                    box = subspecnode.box.clonebox()
                    oplist.append(ResOperation(rop.GETFIELD_GC,
                       [instnode.source], box, ofs))
                    newboxlist.append(box)

class DelayedFixedListSpecNode(DelayedSpecNode):

   def expand_boxlist(self, instnode, newboxlist, oplist):
       from pypy.jit.metainterp.history import ResOperation, ConstInt
       from pypy.jit.metainterp.resoperation import rop
       from pypy.jit.metainterp.optimize import FixedList
        
       newboxlist.append(instnode.source)
       cls = self.known_class
       assert isinstance(cls, FixedList)
       arraydescr = cls.arraydescr
       for ofs, subspecnode in self.fields:
           assert isinstance(subspecnode, SpecNodeWithBox)
           if oplist is None:
               instnode.cleanfields[ofs] = instnode.origfields[ofs]
               newboxlist.append(instnode.curfields[ofs].source)
           else:
               if ofs in instnode.cleanfields:
                   newboxlist.append(instnode.cleanfields[ofs].source)
               else:
                   box = subspecnode.box.clonebox()
                   oplist.append(ResOperation(rop.GETARRAYITEM_GC,
                      [instnode.source, ConstInt(ofs)], box, arraydescr))
                   newboxlist.append(box)

   def extract_runtime_data(self, cpu, valuebox, resultlist):
       from pypy.jit.metainterp.resoperation import rop
       from pypy.jit.metainterp.optimize import FixedList
       
       resultlist.append(valuebox)
       cls = self.known_class
       assert isinstance(cls, FixedList)
       arraydescr = cls.arraydescr
       for ofs, subspecnode in self.fields:
           fieldbox = executor.execute(cpu, rop.GETARRAYITEM_GC,
                                       [valuebox, ConstInt(ofs)], arraydescr)
           subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

class VirtualizableSpecNode(VirtualizedSpecNode):

    def equals(self, other):
        if not isinstance(other, VirtualizableSpecNode):
            return False
        return SpecNodeWithFields.equals(self, other)

class VirtualSpecNode(SpecNodeWithFields):

    def mutate_nodes(self, instnode):
        SpecNodeWithFields.mutate_nodes(self, instnode)
        instnode.virtual = True

class VirtualInstanceSpecNode(VirtualSpecNode):

    def equals(self, other):
        if not isinstance(other, VirtualInstanceSpecNode):
            return False
        return SpecNodeWithFields.equals(self, other)

class VirtualFixedListSpecNode(VirtualSpecNode):

   def __init__(self, known_class, fields, known_length):
       VirtualSpecNode.__init__(self, known_class, fields)
       self.known_length = known_length

   def mutate_nodes(self, instnode):
       VirtualSpecNode.mutate_nodes(self, instnode)
       instnode.known_length = self.known_length

   def equals(self, other):
       if not isinstance(other, VirtualFixedListSpecNode):
           return False
       return SpecNodeWithFields.equals(self, other)
    
   def extract_runtime_data(self, cpu, valuebox, resultlist):
       from pypy.jit.metainterp.resoperation import rop
       from pypy.jit.metainterp.history import ConstInt
       from pypy.jit.metainterp.optimize import FixedList

       for ofs, subspecnode in self.fields:
           cls = self.known_class
           assert isinstance(cls, FixedList)
           arraydescr = cls.arraydescr
           fieldbox = executor.execute(cpu, rop.GETARRAYITEM_GC,
                                       [valuebox, ConstInt(ofs)], arraydescr)
           subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)
