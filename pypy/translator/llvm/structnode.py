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
    __slots__ = "db value structtype _get_types".split()

    prefix = '@s_inst_'

    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.structtype = self.value._TYPE
        parts = str(value).split()[1]
        name = parts.split('.')[-1]
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

    def setup(self):
        if isinstance(self.value, lltype._subarray):
            p, c = lltype.parentlink(self.value)
            if p is not None:
                self.db.prepare_constant(lltype.typeOf(p), p)
        else:
            super(FixedSizeArrayNode, self).setup()

class StructVarsizeNode(StructNode):
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
