import py
from pypy.objspace.flow.model import Block, Constant, Variable, Link
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
        self.name = "%s.%s" % (self.struct._name, nextnum())
        self.ref = "%%st.%s" % self.name
        
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
        self.constructor_ref = "%%new.st.var.%s" % (self.name)
        self.constructor_decl = "%s * %s(int %%len)" % \
                                (self.ref, self.constructor_ref)

    def __str__(self):
        return "<StructVarsizeTypeNode %r>" %(self.ref,)
        
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

def cast_global(toptr, from_, name):
    s = "cast(%s* getelementptr (%s* %s, int 0) to %s)" % (from_,
                                                           from_,
                                                           name,
                                                           toptr)
    return s

class StructNode(LLVMNode):
    _issetup = False 

    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.ref = "%%stinstance.%s.%s" % (value._TYPE._name, nextnum())

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

    def getall(self):
        res = []
        type_ = self.value._TYPE
        for name in type_._names_without_voids():
            T = type_._flds[name]
            value = getattr(self.value, name)
            if not isinstance(T, lltype.Primitive):
                # Create a dummy constant hack XXX
                c = Constant(value, T)

                # Needs some sanitisation
                x = self.db.obj2node[c]
                value = self.db.repr_arg(c)
                t, v = x.getall()
                value = cast_global(self.db.repr_arg_type(T), t, value)
                
            else:
                value = str(value)
            res.append((self.db.repr_arg_type(T), value))
                
        typestr = self.db.repr_arg_type(type_)
        values = ", ".join(["%s %s" % (t, v) for t, v in res])
        return typestr, values
    
    def writeglobalconstants(self, codewriter):
        type_, values = self.getall()
        codewriter.globalinstance(self.ref, type_, values)
                
class StructVarsizeNode(StructNode):
    def __str__(self):
        return "<StructVarsizeNode %r>" %(self.ref,)

    def getall(self):
        res = []
        type_ = self.value._TYPE
        for name in type_._names_without_voids()[:-1]:
            T = type_._flds[name]
            value = getattr(self.value, name)
            if not isinstance(T, lltype.Primitive):
                # Create a dummy constant hack XXX
                value = self.db.repr_arg(Constant(value, T))
            else:
                value = str(value)
            res.append((self.db.repr_arg_type(T), value))

        # Special case for varsized arrays
        name = type_._names_without_voids()[-1]
        T = type_._flds[name]
        assert not isinstance(T, lltype.Primitive)
        value = getattr(self.value, name)
        c = Constant(value, T)
        x = self.db.obj2node[c]
        t, v = x.getall()

        #value = self.db.repr_arg(c)
        value = cast_global(self.db.repr_arg_type(T), t, "{%s}" % v)
        res.append((self.db.repr_arg_type(T), value))

        typestr = self.db.repr_arg_type(type_)
        values = ", ".join(["%s %s" % (t, v) for t, v in res])
        return typestr, values
    
