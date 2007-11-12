from pypy.translator.llvm.node import ConstantNode
from pypy.rpython.lltypesystem import lltype

def getindexhelper(name, struct):
    assert name in list(struct._names)

    fieldnames = struct._names_without_voids()
    try:
        index = fieldnames.index(name)
    except ValueError:
        index = -1
    return index
        
class StructNode(ConstantNode):
    """ A struct constant.  Can simply contain
    a primitive,
    a struct,
    pointer to struct/array
    """
    __slots__ = "db value structtype _get_ref_cache _get_types".split()

    prefix = '@s_inst_'

    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.structtype = self.value._TYPE
        name = str(value).split()[1]
        self._get_ref_cache = None
        self._get_types = self._compute_types()
        self.make_name(name)

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

        return "getelementptr(%s* %s, i32 0, i32 %s)" %(
            self.get_typerepr(),
            self.get_ref(),
            pos)

    def get_ref(self):
        """ Returns a reference as used for operations in blocks. """        
        # XXX cache here is **dangerous** considering it can return different values :-(
        # XXX should write a test to prove this
        #if self._get_ref_cache:
        #    return self._get_ref_cache
        p, c = lltype.parentlink(self.value)
        if p is None:
            ref = self.name
        else:
            ref = self.db.get_childref(p, c)
        #XXXself._get_ref_cache = ref
        return ref

    def get_pbcref(self, toptr):
        """ Returns a reference as used per pbc. """        
        return self.get_ref()
    
    def constantvalue(self):
        """ Returns the constant representation for this node. """
        values = self._getvalues()
        if len(values) > 3:
            all_values = ",\n\t".join(values)
            return "%s {\n\t%s }" % (self.get_typerepr(), all_values)
        else:
            all_values = ",  ".join(values)
            return "%s { %s }" % (self.get_typerepr(), all_values)
                
class FixedSizeArrayNode(StructNode):
    prefix = '@fa_inst_'

    def __init__(self, db, struct): 
        super(FixedSizeArrayNode, self).__init__(db, struct)
        self.array = struct
        self.arraytype = self.structtype.OF

    def constantvalue(self):
        """ Returns the constant representation for this node. """
        values = self._getvalues()
        all_values = ",\n  ".join(values)
        return "%s [\n  %s\n  ]\n" % (self.get_typerepr(), all_values)

    def get_ref(self):
        p, c = lltype.parentlink(self.value)
        if p is None:
            ref = self.name
        else:
            ref = self.db.get_childref(p, c)
            if isinstance(self.value, lltype._subarray):
                # ptr -> array of len 1
                ref = "bitcast(%s* %s to %s*)" % (self.db.repr_type(self.arraytype),
                                               ref,
                                               self.db.repr_type(lltype.typeOf(self.value)))
        return ref

    def get_childref(self, index):
        return "getelementptr(%s* %s, i32 0, i32 %s)" % (
            self.get_typerepr(),
            self.get_ref(),
            index) 

    def setup(self):
        if isinstance(self.value, lltype._subarray):
            # XXX what is this?
            # self.value._parentstructure()
            p, c = lltype.parentlink(self.value)
            if p is not None:
                self.db.prepare_constant(lltype.typeOf(p), p)
        else:
            super(FixedSizeArrayNode, self).setup()

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

    prefix = '@sv_inst_'

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

    def get_childref(self, index):
        pos = 0
        found = False
        for name in self.structtype._names_without_voids():
            if name == index:
                found = True
                break
            pos += 1
        assert found

        ref = "getelementptr(%s* %s, i32 0, i32 %s)" %(
            self.get_typerepr(),
            super(StructVarsizeNode, self).get_ref(),
            pos)

        return ref

    def get_ref(self):
        ref = super(StructVarsizeNode, self).get_ref()
        typeval = self.db.repr_type(lltype.typeOf(self.value))
        ref = "bitcast(%s* %s to %s*)" % (self.get_typerepr(),
                                          ref,
                                          typeval)
        return ref
    
    def get_pbcref(self, toptr):
        """ Returns a reference as used per pbc. """        
        ref = self.name
        p, c = lltype.parentlink(self.value)
        assert p is None, "child varsize struct are NOT needed by rtyper"
        fromptr = "%s*" % self.get_typerepr()
        refptr = "getelementptr(%s %s, i32 0)" % (fromptr, ref)
        ref = "bitcast(%s %s to %s)" % (fromptr, refptr, toptr)
        return ref
    
