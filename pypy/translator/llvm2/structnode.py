import py
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode, ConstantLLVMNode
from pypy.translator.llvm2 import varsize
from pypy.rpython import lltype

log = log.structnode 

class StructTypeNode(LLVMNode):
    def __init__(self, db, struct): 
        assert isinstance(struct, lltype.Struct)
        self.db = db
        self.struct = struct
        prefix = '%structtype.'
        name = self.struct._name
        self.ref = self.make_ref(prefix, name)
        self.name = self.ref[len(prefix):]
        
    def __str__(self):
        return "<StructTypeNode %r>" %(self.ref,)

    def _fields(self):
        return [getattr(self.struct, name) 
                for name in self.struct._names_without_voids()]
    
    def setup(self):
        # Recurse
        for field in self._fields():
            self.db.prepare_repr_arg_type(field)

    def is_atomic(self):
        for f in self._fields():
            if isinstance(f, lltype.Ptr):
                return False

            if not isinstance(f, lltype.Primitive):
                # XXX Recurse
                return False

        return True
    # ______________________________________________________________________
    # main entry points from genllvm 

    def writedatatypedecl(self, codewriter):
        fields = self._fields()
        codewriter.structdef(self.ref,
                             self.db.repr_arg_type_multi(fields))

class StructVarsizeTypeNode(StructTypeNode):

    def __init__(self, db, struct): 
        super(StructVarsizeTypeNode, self).__init__(db, struct)
        self.constructor_ref = "%%new.varsizestruct.%s" % (self.name)
        self.constructor_decl = "%s * %s(int %%len)" % \
                                (self.ref, self.constructor_ref)

    def __str__(self):
        return "<StructVarsizeTypeNode %r>" %(self.ref,)
        
    # ______________________________________________________________________
    # main entry points from genllvm 

    def writedecl(self, codewriter): 
        # declaration for constructor
        codewriter.declare(self.constructor_decl)

    def writeimpl(self, codewriter):
        log.writeimpl(self.ref)

        # build up a list of indices to get to the last 
        # var-sized struct (or rather the according array) 
        indices_to_array = [] 
        current = self.struct
        while isinstance(current, lltype.Struct):
            last_pos = len(current._names_without_voids()) - 1
            indices_to_array.append(("uint", last_pos))
            name = current._names_without_voids()[-1]
            current = current._flds[name]
        assert isinstance(current, lltype.Array)
        arraytype = self.db.repr_arg_type(current.OF)
        # XXX write type info as a comment 
        varsize.write_constructor(codewriter, 
            self.ref, self.constructor_decl, arraytype, 
            indices_to_array,
            atomicmalloc=self.is_atomic())

class StructNode(ConstantLLVMNode):
    """ A struct constant.  Can simply contain
    a primitive,
    a struct,
    pointer to struct/array
    """
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.structtype = self.value._TYPE
        self.ref = self.make_ref('%structinstance', '')
        
    def __str__(self):
        return "<StructNode %r>" % (self.ref,)

    def _gettypes(self):
        return [(name, self.structtype._flds[name])
                for name in self.structtype._names_without_voids()]

    def _getvalues(self):
        values = []
        for name, T in self._gettypes():
            value = getattr(self.value, name)
            values.append(self.db.repr_constant(value)[1])
        return values
    
    def setup(self):
        for name, T in self._gettypes():
            assert T is not lltype.Void
            value = getattr(self.value, name)
            self.db.prepare_constant(T, value)

        p, c = lltype.parentlink(self.value)
        if p is not None:
            self.db.prepare_constant(lltype.typeOf(p), p)
            
    def get_typerepr(self):
        return self.db.repr_arg_type(self.structtype)

    def get_childref(self, index):
        pos = 0
        found = False
        for name in self.structtype._names_without_voids():
            if name == index:
                found = True
                break
            pos += 1
            
        return "getelementptr(%s* %s, int 0, uint %s)" %(
            self.get_typerepr(),
            self.get_ref(),
            pos)

    def get_ref(self):
        """ Returns a reference as used for operations in blocks. """        
        p, c = lltype.parentlink(self.value)
        if p is None:
            ref = self.ref
        else:
            parent = self.db.obj2node[p]
            ref = parent.get_childref(c)
        return ref

    def get_pbcref(self, toptr):
        """ Returns a reference as used per pbc. """        
        return self.get_ref()
    
    def constantvalue(self):
        """ Returns the constant representation for this node. """
        values = self._getvalues()
        all_values = ",\n  ".join(values)
        return "%s {\n  %s\n  }\n" % (self.get_typerepr(), all_values)
                
                
class StructVarsizeNode(StructNode):
    """ A varsize struct constant.  Can simply contain
    a primitive,
    a struct,
    pointer to struct/array

    and the last element *must* be
    an array
    OR
    a series of embedded structs, which has as its last element an array.
    """

    def __str__(self):
        return "<StructVarsizeNode %r>" % (self.ref,)

    def _getvalues(self):
        values = []
        for name, T in self._gettypes()[:-1]:
            value = getattr(self.value, name)
            values.append(self.db.repr_constant(value)[1])
        values.append(self._get_lastnoderepr())
        return values

    def _get_lastnode_helper(self):
        lastname, LASTT = self._gettypes()[-1]
        assert isinstance(LASTT, lltype.Array) or (
            isinstance(LASTT, lltype.Struct) and LASTT._arrayfld)
        value = getattr(self.value, lastname)
        return self.db.repr_constant(value)

    def _get_lastnode(self):
        return self._get_lastnode_helper()[0]

    def _get_lastnoderepr(self):
        return self._get_lastnode_helper()[1]

    def setup(self):
        super(StructVarsizeNode, self).setup()
    
    def get_typerepr(self):
        # last type is a special case and need to be worked out recursively
        types = self._gettypes()[:-1]
        types_repr = [self.db.repr_arg_type(T) for name, T in types]
        types_repr.append(self._get_lastnode().get_typerepr())
        
        return "{%s}" % ", ".join(types_repr)
         
    def get_ref(self):
        ref = super(StructVarsizeNode, self).get_ref()
        typeval = self.db.repr_arg_type(lltype.typeOf(self.value))
        ref = "cast (%s* %s to %s*)" % (self.get_typerepr(),
                                        ref,
                                        typeval)
        return ref
    
    def get_pbcref(self, toptr):
        """ Returns a reference as used per pbc. """        
        ref = self.ref
        p, c = lltype.parentlink(self.value)
        if p is not None:
            assert False, "XXX TODO"

        fromptr = "%s*" % self.get_typerepr()
        refptr = "getelementptr (%s %s, int 0)" % (fromptr, ref)
        ref = "cast(%s %s to %s)" % (fromptr, refptr, toptr)
        return ref
