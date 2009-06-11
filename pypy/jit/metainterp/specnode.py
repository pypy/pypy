from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.history import ExpandArgsFrom
from pypy.jit.metainterp import executor

class SpecNode(object):

    def expand_boxlist(self, instnode, newboxlist):
        newboxlist.append(instnode.source)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)

    def adapt_to(self, instnode, modif_list):
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

#class SpecNodeWithBox(NotSpecNode):
#    # XXX what is this class used for?
#    def __init__(self, box):
#        self.box = box
    
#    def equals(self, other):
#        if type(other) is SpecNodeWithBox:
#            return True
#        return False

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
        from pypy.jit.metainterp.optimize import av_eq, av_hash
        from pypy.rlib.objectmodel import r_dict
        
        FixedClassSpecNode.mutate_nodes(self, instnode)
        curfields = r_dict(av_eq, av_hash)
        for ofs, subspecnode in self.fields:
            if subspecnode is not None:
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

    def expand_boxlist(self, instnode, newboxlist):
        for ofs, subspecnode in self.fields:
            if subspecnode is not None:
                if ofs in instnode.curfields:
                    subinstnode = instnode.curfields[ofs]
                else:
                    subinstnode = subspecnode.sourcenode
                subspecnode.expand_boxlist(subinstnode, newboxlist)
            else:
                newboxlist.append(ExpandArgsFrom(self, ofs))

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        for ofs, subspecnode in self.fields:
            from pypy.jit.metainterp.history import AbstractDescr
            assert isinstance(ofs, AbstractDescr)
            fieldbox = executor.execute(cpu, rop.GETFIELD_GC,
                                        [valuebox], ofs)
            subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

    def adapt_to(self, instnode, modif_list):
        for ofs, subspecnode in self.fields:
            subspecnode.adapt_to(instnode.curfields[ofs], modif_list)

    def compute_number_of_nodes(self):
        counter = 0
        for ofs, subspecnode in self.fields:
            counter += subspecnode.compute_number_of_nodes()
        return counter

class VirtualizedSpecNode(SpecNodeWithFields):

    def equals(self, other):
        if not self.known_class.equals(other.known_class):
            return False
        assert len(self.fields) == len(other.fields)
        for i in range(len(self.fields)):
            if (self.fields[i][1] is None or
                other.fields[i][1] is None):
                continue
            assert self.fields[i][0].equals(other.fields[i][0])
            if not self.fields[i][1].equals(other.fields[i][1]):
                return False
        return True

    def matches(self, instnode):
        for key, value in self.fields:
            if key not in instnode.curfields:
                continue
            if value is not None and not value.matches(instnode.curfields[key]):
                return False
        return True
    
    def expand_boxlist(self, instnode, newboxlist):
        newboxlist.append(instnode.source)
        SpecNodeWithFields.expand_boxlist(self, instnode, newboxlist)

    def extract_runtime_data(self, cpu, valuebox, resultlist):
        resultlist.append(valuebox)
        SpecNodeWithFields.extract_runtime_data(self, cpu, valuebox, resultlist)

    def adapt_to(self, instnode, modif_list):
        from pypy.jit.metainterp.optimize import InstanceNode
        
        instnode.escaped = True
        fields = []
        instnode.cls = InstanceNode(self.known_class, const=True)
        for ofs, subspecnode in self.fields:
            if subspecnode is None:
                if ofs in instnode.curfields and ofs in instnode.origfields:
                    node = instnode.curfields[ofs]
                    orignode = instnode.origfields[ofs]
                    subspecnode = orignode.intersect(node, {})
                    subspecnode.sourcenode = orignode
                    modif_list.append((self, ofs, subspecnode))
                    subspecnode.adapt_to(node, modif_list)
                    subspecnode.mutate_nodes(orignode)
                elif ofs in instnode.origfields:
                    node = instnode.origfields[ofs]
                    subspecnode = node.intersect(node, {})
                    subspecnode.sourcenode = node
                    modif_list.append((self, ofs, subspecnode))
                    subspecnode.adapt_to(node, modif_list)
            elif ofs in instnode.curfields:                
                subspecnode.adapt_to(instnode.curfields[ofs], modif_list)
            elif ofs in instnode.origfields:
                subspecnode.adapt_to(instnode.origfields[ofs], modif_list)
            fields.append((ofs, subspecnode))
        self.fields = fields

# class DelayedSpecNode(VirtualizedSpecNode):

#     def expand_boxlist(self, instnode, newboxlist, oplist):
#         from pypy.jit.metainterp.history import AbstractDescr
#         newboxlist.append(instnode.source)
#         for ofs, subspecnode in self.fields:
#             assert isinstance(subspecnode, SpecNodeWithBox)
#             if oplist is None:
#                 instnode.cleanfields[ofs] = instnode.origfields[ofs]
#                 newboxlist.append(instnode.curfields[ofs].source)
#             else:
#                 if ofs in instnode.cleanfields:
#                     newboxlist.append(instnode.cleanfields[ofs].source)
#                 else:
#                     box = subspecnode.box.clonebox()
#                     assert isinstance(ofs, AbstractDescr)
#                     oplist.append(ResOperation(rop.GETFIELD_GC,
#                        [instnode.source], box, ofs))
#                     newboxlist.append(box)

# class DelayedFixedListSpecNode(DelayedSpecNode):

#    def expand_boxlist(self, instnode, newboxlist, oplist):
#        from pypy.jit.metainterp.history import ResOperation
#        from pypy.jit.metainterp.resoperation import rop
#        from pypy.jit.metainterp.optimize import FixedList
        
#        newboxlist.append(instnode.source)
#        cls = self.known_class
#        assert isinstance(cls, FixedList)
#        arraydescr = cls.arraydescr
#        for ofs, subspecnode in self.fields:
#            assert isinstance(subspecnode, SpecNodeWithBox)
#            if oplist is None:
#                instnode.cleanfields[ofs] = instnode.origfields[ofs]
#                newboxlist.append(instnode.curfields[ofs].source)
#            else:
#                if ofs in instnode.cleanfields:
#                    newboxlist.append(instnode.cleanfields[ofs].source)
#                else:
#                    box = subspecnode.box.clonebox()
#                    oplist.append(ResOperation(rop.GETARRAYITEM_GC,
#                       [instnode.source, ofs], box, arraydescr))
#                    newboxlist.append(box)

#    def extract_runtime_data(self, cpu, valuebox, resultlist):
#        from pypy.jit.metainterp.resoperation import rop
#        from pypy.jit.metainterp.optimize import FixedList
#        from pypy.jit.metainterp.history import check_descr
       
#        resultlist.append(valuebox)
#        cls = self.known_class
#        assert isinstance(cls, FixedList)
#        arraydescr = cls.arraydescr
#        check_descr(arraydescr)
#        for ofs, subspecnode in self.fields:
#            fieldbox = executor.execute(cpu, rop.GETARRAYITEM_GC,
#                                        [valuebox, ofs], arraydescr)
#            subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

class VirtualizableSpecNode(VirtualizedSpecNode):

    def equals(self, other):
        if not isinstance(other, VirtualizableSpecNode):
            return False
        return VirtualizedSpecNode.equals(self, other)        

    def adapt_to(self, instnode, modif_list):
        instnode.virtualized = True
        VirtualizedSpecNode.adapt_to(self, instnode, modif_list)

class VirtualizableListSpecNode(VirtualizedSpecNode):

    def equals(self, other):
        if not isinstance(other, VirtualizableListSpecNode):
            return False
        return VirtualizedSpecNode.equals(self, other)
    
    def extract_runtime_data(self, cpu, valuebox, resultlist):
        from pypy.jit.metainterp.resoperation import rop
        from pypy.jit.metainterp.optimize import FixedList
        from pypy.jit.metainterp.history import check_descr

        resultlist.append(valuebox)
        cls = self.known_class
        assert isinstance(cls, FixedList)
        arraydescr = cls.arraydescr
        check_descr(arraydescr)
        for ofs, subspecnode in self.fields:
            if subspecnode is not None:
                fieldbox = executor.execute(cpu, rop.GETARRAYITEM_GC,
                                            [valuebox, ofs], arraydescr)
                subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)

    def adapt_to(self, instnode, modif_list):
        instnode.virtualized = True
        VirtualizedSpecNode.adapt_to(self, instnode, modif_list)

class VirtualSpecNode(SpecNodeWithFields):

    def adapt_to(self, instnode, modif_list):
        instnode.virtual = True
        SpecNodeWithFields.adapt_to(self, instnode, modif_list)

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
       instnode.cursize = self.known_length

   def equals(self, other):
       if not isinstance(other, VirtualFixedListSpecNode):
           return False
       return SpecNodeWithFields.equals(self, other)
    
   def extract_runtime_data(self, cpu, valuebox, resultlist):
       from pypy.jit.metainterp.resoperation import rop
       from pypy.jit.metainterp.optimize import FixedList
       from pypy.jit.metainterp.history import check_descr
       cls = self.known_class
       assert isinstance(cls, FixedList)
       arraydescr = cls.arraydescr
       check_descr(arraydescr)
       for ofs, subspecnode in self.fields:
           fieldbox = executor.execute(cpu, rop.GETARRAYITEM_GC,
                                       [valuebox, ofs], arraydescr)
           subspecnode.extract_runtime_data(cpu, fieldbox, resultlist)
