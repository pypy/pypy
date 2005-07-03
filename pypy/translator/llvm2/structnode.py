import py
from pypy.objspace.flow.model import Block, Constant, Variable, Link
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode
from pypy.rpython import lltype

log = log.structnode 

class StructTypeNode(LLVMNode):
    _issetup = False 
    struct_counter = 0

    def __init__(self, db, struct): 
        assert isinstance(struct, lltype.Struct)
        self.db = db
        self.struct = struct
        self.name = "%s.%s" % (self.struct._name, StructTypeNode.struct_counter)
        self.ref = "%%st.%s" % self.name
        StructTypeNode.struct_counter += 1
        
    def __str__(self):
        return "<StructTypeNode %r>" %(self.ref,)
    
    def setup(self):
        # Recurse
        for field in self.struct._flds:
            self.db.prepare_repr_arg_type(field)
        self._issetup = True

    # ______________________________________________________________________
    # main entry points from genllvm 

    def writedatatypedecl(self, codewriter):
        assert self._issetup 
        fields = [getattr(self.struct, name) for name in self.struct._names_without_voids()] 
        l = [self.db.repr_arg_type(field) for field in fields]
        codewriter.structdef(self.ref, l)

class StructVarsizeTypeNode(StructTypeNode):

    def __init__(self, db, struct): 
        super(StructVarsizeTypeNode, self).__init__(db, struct)
        new_var_name = "%%new.st.var.%s" % self.name
        self.constructor_name = "%s * %s(int %%len)" % (self.ref, new_var_name)
        
    def writedecl(self, codewriter): 
        # declaration for constructor
        codewriter.declare(self.constructor_name)

    def writeimpl(self, codewriter):
        log.writeimpl(self.ref)
        codewriter.openfunc(self.constructor_name)
        codewriter.label("block0")
        indices_to_array = [("int", 0)]
        s = self.struct
        while isintance(s, lltypes.Struct):
            last_pos = len(self.struct._names_without_voids()) - 1
            indices_to_array.append(("uint", last_pos))
            s = s._flds.values()[-1]

        # Into array and length            
        indices = indices_to_array + [("uint", 1), ("int", "%len")]
        codewriter.getelementptr("%size", self.ref + "*",
                                 "null", *indices)

        #XXX is this ok for 64bit?
        codewriter.cast("%sizeu", arraytype + "*", "%size", "uint")
        codewriter.malloc("%resulttmp", "sbyte", "uint", "%sizeu")
        codewriter.cast("%result", "sbyte*", "%resulttmp", self.ref + "*")

        # remember the allocated length for later use.
        indices = indices_to_array + [("uint", 0)]
        codewriter.getelementptr("%size_ptr", self.ref + "*",
                                 "%result", *indices)

        codewriter.cast("%signedsize", "uint", "%sizeu", "int")
        codewriter.store("int", "%signedsize", "%size_ptr")

        codewriter.ret(self.ref + "*", "%result")
        codewriter.closefunc()

class StructNode(LLVMNode):
    _issetup = False 
    struct_counter = 0

    def __init__(self, db, value):
        self.db = db
        self.name = "%s.%s" % (value._TYPE._name, StructNode.struct_counter)
        self.ref = "%%stinstance.%s" % self.name
        self.value = value
        StructNode.struct_counter += 1

    def __str__(self):
        return "<StructNode %r>" %(self.ref,)

    def setup(self):
        for name in self.value._TYPE._names_without_voids():
            T = self.value._TYPE._flds[name]
            assert T is not lltype.Void
            if not isinstance(T, lltype.Primitive):
                value = getattr(self.value, name)
                # Create a dummy constant hack XXX
                c = Constant(value, T)
                self.db.prepare_arg(c)
                
        self._issetup = True

    def get_values(self):
        res = []
        for name in self.value._TYPE._names_without_voids():
            T = self.value._TYPE._flds[name]
            value = getattr(self.value, name)
            if not isinstance(T, lltype.Primitive):
                # Create a dummy constant hack XXX
                value = self.db.repr_arg(Constant(value, T))
            else:
                value = str(value)
            res.append((self.db.repr_arg_type(T), value))
        return ", ".join(["%s %s" % (t, v) for t, v in res])

    def writeglobalconstants(self, codewriter):
        codewriter.globalinstance(self.ref,
                                  self.db.repr_arg_type(self.value._TYPE),
                                  self.get_values())

