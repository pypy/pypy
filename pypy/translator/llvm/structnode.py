from pypy.translator.llvm.node import ConstantNode
from pypy.translator.llvm.gc import needs_gcheader
from pypy.rpython.lltypesystem import lltype

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
        result = list(self.db.gcpolicy.gcheader_definition(self.structtype))
        for name in self.structtype._names_without_voids():
            result.append((name, self.structtype._flds[name]))
        return result

    def _getvalues(self):
        values = list(self.db.gcpolicy.gcheader_initdata(self.value))
        for name in self.structtype._names_without_voids():
            values.append(getattr(self.value, name))
        return values

    def _getvaluesrepr(self):
        values = self._getvalues()
        return [self.db.repr_constant(value)[1] for value in values]

    def setup(self):
        for value in self._getvalues():
            self.db.prepare_constant(lltype.typeOf(value), value)

        p, c = lltype.parentlink(self.value)
        if p is not None:
            self.db.prepare_constant(lltype.typeOf(p), p)
            
    def get_typerepr(self):
        return self.db.repr_type(self.structtype)
    
    def constantvalue(self):
        """ Returns the constant representation for this node. """
        values = self._getvaluesrepr()
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
        values = self._getvaluesrepr()
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

    def _get_lastnode_helper(self):
        lastname, LASTT = self._get_types[-1]
        assert isinstance(LASTT, lltype.Array) or (
            isinstance(LASTT, lltype.Struct) and LASTT._arrayfld)
        value = getattr(self.value, lastname)
        return self.db.repr_constant(value)

    def _get_lastnode(self):
        return self._get_lastnode_helper()[0]

    def setup(self):
        super(StructVarsizeNode, self).setup()
    
    def get_typerepr(self):
        try:
            return self._get_typerepr_cache
        except AttributeError:
            # last type is a special case and need to be worked out recursively
            types = self._get_types[:-1]
            types_repr = [self.db.repr_type(T) for name, T in types]
            types_repr.append(self._get_lastnode().get_typerepr())
            result = "{%s}" % ", ".join(types_repr)
            self._get_typerepr_cache = result
            return result         
