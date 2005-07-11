import py
from pypy.translator.llvm2.log import log
from pypy.translator.llvm2.node import LLVMNode
from pypy.translator.llvm2 import varsize
from pypy.rpython import lltype

import itertools  
nextnum = itertools.count().next 

log = log.structnode 

class StructTypeNode(LLVMNode):
    _issetup = False 

    def __init__(self, db, struct): 
        assert isinstance(struct, lltype.Struct)
        self.db = db
        self.struct = struct
        self.name = "%s.%s" % (self.struct._name , nextnum())
        self.ref = "%%st.%s" % (self.name)
        
    def __str__(self):
        return "<StructTypeNode %r>" %(self.ref,)
    
    def setup(self):
        # Recurse
        for field in self.struct._flds.values():
            self.db.prepare_repr_arg_type(field)
        self._issetup = True

    # ______________________________________________________________________
    # main entry points from genllvm 

    def writedatatypedecl(self, codewriter):
        assert self._issetup 
        fields = [getattr(self.struct, name)
                  for name in self.struct._names_without_voids()] 
        codewriter.structdef(self.ref,
                             self.db.repr_arg_type_multi(fields))

class StructVarsizeTypeNode(StructTypeNode):

    def __init__(self, db, struct): 
        super(StructVarsizeTypeNode, self).__init__(db, struct)
        self.constructor_ref = "%%new.st.var.%s" % (self.name)
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
        from pypy.translator.llvm2.atomic import is_atomic

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
            indices_to_array)

class StructNode(LLVMNode):
    """ A struct constant.  Can simply contain
    a primitive,
    a struct,
    pointer to struct/array
    """
    _issetup = False 

    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.structtype = self.value._TYPE
        self.ref = "%%stinstance.%s" % (nextnum(),)

    def __str__(self):
        return "<StructNode %r>" % (self.ref,)

    def _gettypes(self):
        return [(name, self.structtype._flds[name])
                for name in self.structtype._names_without_voids()]

    def setup(self):
        for name, T in self._gettypes():
            assert T is not lltype.Void
            if isinstance(T, lltype.Ptr):
                self.db.addptrvalue(getattr(self.value, name))
        self._issetup = True

    def castfrom(self):
        return None

    def get_typestr(self):
        return self.db.repr_arg_type(self.structtype)
    
    def constantvalue(self):
        """ Returns the constant representation for this node. """
        values = []
        for name, T in self._gettypes():
            value = getattr(self.value, name)
            values.append(self.db.reprs_constant(value))
                
        return "%s {%s}" % (self.get_typestr(), ", ".join(values))
    
    # ______________________________________________________________________
    # main entry points from genllvm 

    def writeglobalconstants(self, codewriter):
        codewriter.globalinstance(self.ref, self.constantvalue())
                
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

    def setup(self):
        # set castref (note we must ensure that types are "setup" before we can
        # get typeval)
        typeval = self.db.repr_arg_type(lltype.typeOf(self.value))
        self.castref = "cast (%s* %s to %s*)" % (self.get_typestr(),
                                                 self.ref,
                                                 typeval)
        super(StructVarsizeNode, self).setup()
        
    def get_typestr(self):
        lastname, LASTT = self._gettypes()[-1]
        assert isinstance(LASTT, lltype.Array) or (
            isinstance(LASTT, lltype.Struct) and LASTT._arrayfld)

        #XXX very messy
        node = self.db.create_constant_node(getattr(self.value, lastname), True)
        lasttype = node.get_typestr()

        types = []
        for name, T in self._gettypes()[:-1]:
            types.append(self.db.repr_arg_type(T))
        types.append(lasttype)

        return "{%s}" % ", ".join(types)
        
    def castfrom(self):
        return "%s*" % self.get_typestr()
 
