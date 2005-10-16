import py
from pypy.translator.js.node import LLVMNode, ConstantLLVMNode
from pypy.rpython import lltype
from pypy.translator.js.log import log
log = log.structnode 


def _rename_reserved_keyword(name):
    if name in 'if then else function for while witch continue break super int bool Array String Struct Number'.split():
        name += '_'
    return name


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

    def writedecl(self, codewriter):
        codewriter.declare(self.ref + ' = new Object()')
        
    def get_childref(self, index):
        return self.get_ref() #XXX what to do with index?
        #pos = 0
        #found = False
        #for name in self.structtype._names_without_voids():
        #    if name == index:
        #        found = True
        #        break
        #    pos += 1
        #return "getelementptr(%s* %s, int 0, uint %s)" %(
        #    self.get_typerepr(),
        #    self.get_ref(),
        #    pos)

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

    def constantvalue(self):
        """ Returns the constant representation for this node. """
        vars = []
        for i, value in enumerate(self._getvalues()):
            name = self._get_types[i][0]
            name = _rename_reserved_keyword(name)
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
    
    #def get_typerepr(self):
    #        try:
    #            return self._get_typerepr_cache
    #        except:
    #            # last type is a special case and need to be worked out recursively
    #            types = self._get_types[:-1]
    #            types_repr = [self.db.repr_type(T) for name, T in types]
    #            types_repr.append(self._get_lastnode().get_typerepr())
    #            result = "{%s}" % ", ".join(types_repr)
    #            self._get_typerepr_cache = result
    #            return result
         
    def get_ref(self):
        return self.ref
