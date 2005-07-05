from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.structnode import StructTypeNode
from pypy.translator.llvm2.arraynode import ArrayTypeNode

log = log.atomic

def is_atomic(node):
    if isinstance(node, StructTypeNode):
        fields = str([getattr(node.struct, name) for name in node.struct._names_without_voids()])
        if '*' not in fields:
            return True #non-pointers only
        return False    #contains pointer(s)
    elif isinstance(node, ArrayTypeNode):
        return False    #because they actually are arrays of pointers
    log("unknown type %s, assuming non-atomic" % str(type(node)))
    return False    
