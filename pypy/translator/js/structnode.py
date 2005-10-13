import py
from pypy.translator.js.node import LLVMNode, ConstantLLVMNode
from pypy.rpython import lltype
from pypy.translator.js.log import log

log = log.structnode 

class StructTypeNode(LLVMNode):
    __slots__ = "db struct ref name".split()

    def __init__(self, db, struct): 
        assert isinstance(struct, lltype.Struct)
        self.db = db
        self.struct = struct
        prefix = 'structtype_'
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
            self.db.prepare_type(field)

    # ______________________________________________________________________
    # main entry points from genllvm 

    def writedatatypedecl(self, codewriter):
        fields_types = [self.db.repr_type(f) for f in self._fields()]
        codewriter.structdef(self.ref, fields_types)

class StructVarsizeTypeNode(StructTypeNode):
    __slots__ = "constructor_ref constructor_decl".split()

    def __init__(self, db, struct): 
        super(StructVarsizeTypeNode, self).__init__(db, struct)
        prefix = 'new_varsizestruct_'
        self.constructor_ref = self.make_ref(prefix, self.name)
        self.constructor_decl = "%s * %s(int %%len)" % \
                                (self.ref,
                                 self.constructor_ref)

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
            indices_to_array.append(("uint", last_pos)) #struct requires uint consts
            name = current._names_without_voids()[-1]
            current = current._flds[name]
        assert isinstance(current, lltype.Array)

class StructNode(ConstantLLVMNode):
    """ A struct constant.  Can simply contain
    a primitive,
    a struct,
    pointer to struct/array
    """
    __slots__ = "db value structtype ref _get_ref_cache _get_types".split()

    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.structtype = self.value._TYPE
        prefix = 'structinstance_'
        name = str(value).split()[1]
        self.ref = self.make_ref(prefix, name)
        self._get_ref_cache = None
        self._get_types = self._compute_types()

    def __str__(self):
        return "<StructNode %r>" % (self.ref,)

    def _compute_types(self):
        return [(name, self.structtype._flds[name])
                for name in self.structtype._names_without_voids()]

    def _getvalues(self):
        values = []
        for name, T in self._get_types:
            value = getattr(self.value, name)
            values.append(self.db.repr_constant(value)[1])
        return values
    
    def setup(self):
        for name, T in self._get_types:
            assert T is not lltype.Void
            value = getattr(self.value, name)
            self.db.prepare_constant(T, value)

        p, c = lltype.parentlink(self.value)
        if p is not None:
            self.db.prepare_constant(lltype.typeOf(p), p)
            
    def get_typerepr(self):
        return self.db.repr_type(self.structtype)

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
        if self._get_ref_cache:
            return self._get_ref_cache
        p, c = lltype.parentlink(self.value)
        if p is None:
            ref = self.ref
        else:
            ref = self.db.get_childref(p, c)
        self._get_ref_cache = ref
        return ref

    def get_pbcref(self, toptr):
        """ Returns a reference as used per pbc. """        
        return self.get_ref()
    
    def constantvalue(self):
        """ Returns the constant representation for this node. """
        vars = []
        for i, value in enumerate(self._getvalues()):
            name = self._get_types[i][0]
            var  = (name, str(value))
            vars.append(var)
        return "({%s})" % ", ".join(["%s:%s" % var for var in vars])

        #values = self._getvalues()
        #all_values = ",\n  ".join(values)
        #return "%s {\n  %s\n  }\n" % (self.get_typerepr(), all_values)
                
                
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
        for name, T in self._get_types[:-1]:
            value = getattr(self.value, name)
            values.append(self.db.repr_constant(value)[1])
        values.append(self._get_lastnoderepr())
        return values

    def _get_lastnode_helper(self):
        lastname, LASTT = self._get_types[-1]
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
            try:
                return self._get_typerepr_cache
            except:
                # last type is a special case and need to be worked out recursively
                types = self._get_types[:-1]
                types_repr = [self.db.repr_type(T) for name, T in types]
                types_repr.append(self._get_lastnode().get_typerepr())
                result = "{%s}" % ", ".join(types_repr)
                self._get_typerepr_cache = result
                return result
         
    def get_ref(self):
        return self.ref
        #if self._get_ref_cache:
        #    return self._get_ref_cache
        #ref = super(StructVarsizeNode, self).get_ref()
        #typeval = self.db.repr_type(lltype.typeOf(self.value))
        #ref = "cast (%s* %s to %s*)" % (self.get_typerepr(),
        #                                ref,
        #                                typeval)
        #self._get_ref_cache = ref
        #return ref
    
    def get_pbcref(self, toptr):
        """ Returns a reference as used per pbc. """        
        return self.ref
        #ref = self.ref
        #p, c = lltype.parentlink(self.value)
        #assert p is None, "child arrays are NOT needed by rtyper"
        #fromptr = "%s*" % self.get_typerepr()
        #refptr = "getelementptr (%s %s, int 0)" % (fromptr, ref)
        #ref = "cast(%s %s to %s)" % (fromptr, refptr, toptr)
        #return ref
