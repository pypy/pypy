import py
from pypy.objspace.flow.model import Block, Constant, Variable, Link
from pypy.translator.llvm2.log import log 
log = log.structnode 

class StructNode(object):
    _issetup = False 
    struct_counter = 0

    def __init__(self, db, struct): 
        self.db = db
        self.struct = struct 
        self.ref = "%%st.%s.%s" % (struct._name, StructNode.struct_counter)
        StructNode.struct_counter += 1
        
    def __str__(self):
        return "<StructNode %r>" %(self.ref,)
    
    def setup(self):
        log.XXX("setup", self)
        self._issetup = True

    # ______________________________________________________________________
    # entry points from genllvm 
    #
    def writedecl(self, codewriter): 
        assert self._issetup 
        struct = self.struct
        l = []
        for fieldname in struct._names:
            type_ = getattr(struct, fieldname)
            l.append(self.db.repr_arg_type(type_))
        codewriter.structdef(self.ref, l) 

    def writeimpl(self, codewriter):
        assert self._issetup 
