from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.structnode import StructTypeNode
from pypy.translator.llvm2.arraynode import ArrayTypeNode
from pypy.rpython import lltype

log = log.atomic

def is_atomic(node):
    # XXX is the below really right? 
    if isinstance(node, StructTypeNode):
        fields = [getattr(node.struct, name) 
                    for name in node.struct._names_without_voids()]
        fields = [x for x in fields if isinstance(x, lltype.Ptr)]
        if not fields: 
            return True #non-pointers only
        return False    #contains pointer(s)
    elif isinstance(node, ArrayTypeNode):
        return not isinstance(node.array.OF, lltype.Ptr)
    log("unknown type %s, assuming non-atomic" % str(type(node)))
    return False    
