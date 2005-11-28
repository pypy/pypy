import py
from pypy.translator.js.node import Node
from pypy.rpython.lltypesystem import lltype
from pypy.translator.js.log import log
log = log.structnode 


class StructNode(Node):
    """ A struct constant.  Can simply contain
    a primitive,
    a struct,
    pointer to struct/array
    """
    def __init__(self, db, value):
        self.db = db
        self.value = value
        self.structtype = self.value._TYPE
        name = str(value).split()[1]
        self.ref = db.namespace.uniquename(name)
        self._name_types = self._compute_name_types()

    def __str__(self):
        return "<StructNode %r>" % (self.ref,)

    def _compute_name_types(self):
        return [(name, self.structtype._flds[name])
                for name in self.structtype._names_without_voids()]

    def _getvalues(self):
        values = []
        for name, T in self._name_types:
            value = getattr(self.value, name)
            values.append(self.db.repr_constant(value)[1])
        return values
    
    def setup(self):
        for name, T in self._name_types:
            assert T is not lltype.Void
            value = getattr(self.value, name)
            self.db.prepare_constant(T, value)

        p, c = lltype.parentlink(self.value)
        if p is not None:
            self.db.prepare_constant(lltype.typeOf(p), p)

    def write_forward_struct_declaration(self, codewriter):
        codewriter.declare('var ' + self.ref + ' = new Object()')
        
    #def get_childref(self, index):
    #    return self.ref #self.get _ref() #XXX what to do with index?
    #    #pos = 0
    #    #found = False
    #    #for name in self.structtype._names_without_voids():
    #    #    if name == index:
    #    #        found = True
    #    #        break
    #    #    pos += 1
    #    #return "getelementptr(%s* %s, int 0, uint %s)" %(
    #    #    self.get_typerepr(),
    #    #    self.get _ref(),
    #    #    pos)
    #
    #def get _ref(self):
    #    """ Returns a reference as used for operations in blocks. """        
    #    p, c = lltype.parentlink(self.value)
    #    if p is None:
    #        ref = self.ref
    #    else:
    #        ref = self.db.get_childref(p, c)
    #    return ref

    def write_global_struct(self, codewriter):
        """ Returns the constant representation for this node. """
        #lines = []
        for i, value in enumerate(self._getvalues()):
            name, T = self._name_types[i]
            line = "%s.%s = %s" % (self.ref, self.db.namespace.ensure_non_reserved(name), str(value))
            log.writeglobaldata(line)
            codewriter.append(line)
            #lines.append(line)
        #log.writeglobaldata(str(lines))
        #return lines


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
        for name, T in self._name_types[:-1]:
            value = getattr(self.value, name)
            values.append(self.db.repr_constant(value)[1])
        values.append(self._get_lastnoderepr())
        return values

    def _get_lastnode_helper(self):
        lastname, LASTT = self._name_types[-1]
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
    #    # last type is a special case and need to be worked out recursively
    #    types = self._name_types[:-1]
    #    types_repr = [self.db.repr_type(T) for name, T in types]
    #    types_repr.append(self._get_lastnode().get_typerepr())
    #    result = "{%s}" % ", ".join(types_repr)
    #    return result
    #
    #def get _ref(self):
    #    return self.ref
