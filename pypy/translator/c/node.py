from __future__ import generators
from pypy.translator.gensupp import C_IDENTIFIER
from pypy.rpython.lltypes import Struct, Array, FuncType, PyObject, typeOf
from pypy.rpython.lltypes import GcStruct, GcArray, GC_CONTAINER, ContainerType
from pypy.rpython.lltypes import parentlink


def needs_refcount(T):
    if not isinstance(T, GC_CONTAINER):
        return False
    if isinstance(T, GcStruct):
        if T._names and isinstance(T._flds[T._names[0]], GC_CONTAINER):
            return False   # refcount already in the first first
    return True

def somelettersfrom(s):
    upcase = [c for c in s if c.isupper()]
    if not upcase:
        upcase = [c for c in s.title() if c.isupper()]
    locase = [c for c in s if c.islower()]
    if locase and upcase:
        return ''.join(upcase).lower()
    else:
        return s[:2].lower()


class StructDefNode:

    def __init__(self, db, STRUCT, varlength=1):
        self.STRUCT = STRUCT
        if varlength == 1:
            basename = STRUCT._name
        else:
            basename = db.gettypedefnode(STRUCT).name
            basename = '%s_len%d' % (basename, varlength)
        self.name = db.namespace.uniquename(basename)
        self.dependencies = {}
        self.fields = []
        self.prefix = somelettersfrom(STRUCT._name) + '_'
        for name in STRUCT._names:
            T = STRUCT._flds[name]
            if name == STRUCT._arrayfld:
                typename = db.gettype(T, varlength=varlength, who_asks=self)
            else:
                typename = db.gettype(T, who_asks=self)
            self.fields.append((self.c_struct_field_name(name), typename))

    def c_struct_field_name(self, name):
        return self.prefix + name

    def access_expr(self, baseexpr, fldname):
        fldname = self.c_struct_field_name(fldname)
        return '%s.%s' % (baseexpr, fldname)

    def definition(self):
        yield 'struct %s {' % self.name
        if needs_refcount(self.STRUCT):
            yield '\tlong refcount;'
        for name, typename in self.fields:
            yield '\t%s;' % typename.replace('@', name)
        yield '};'


class ArrayDefNode:

    def __init__(self, db, ARRAY, varlength=1):
        self.ARRAY = ARRAY
        if varlength == 1:
            basename = 'array'
        else:
            basename = db.gettypedefnode(ARRAY).name
            basename = '%s_len%d' % (basename, varlength)
        self.name = db.namespace.uniquename(basename)
        self.dependencies = {}
        self.structname = db.gettype(ARRAY.OF, who_asks=self)
        self.varlength = varlength

    def access_expr(self, baseexpr, index):
        return '%s.items[%d]' % (baseexpr, index)

    def definition(self):
        yield 'struct %s {' % self.name
        if needs_refcount(self.ARRAY):
            yield '\tlong refcount;'
        yield '\tlong length;'
        yield '\t%s;' % self.structname.replace('@', 'items[%d]' %
                                                self.varlength)
        yield '};'


class ContainerNode:

    def __init__(self, db, T, obj):
        self.db = db
        self.T = T
        self.obj = obj
        #self.dependencies = {}
        self.typename = db.gettype(T)  #, who_asks=self)
        self.implementationtypename = db.gettype(T, varlength=self.getlength())
        parent, parentindex = parentlink(obj)
        if parent is None:
            self.name = db.namespace.uniquename('g_' + self.basename())
            self.globalcontainer = True
        else:
            self.globalcontainer = False
            parentnode = db.getcontainernode(parent)
            defnode = db.gettypedefnode(parentnode.T)
            self.name = defnode.access_expr(parentnode.name, parentindex)
        self.ptrname = '&%s' % self.name
        if self.typename != self.implementationtypename:
            self.ptrname = '((%s)(void*)%s)' % (self.typename.replace('@', '*'),
                                                self.ptrname)

    def forward_declaration(self):
        yield '%s; /* forward */' % (
            self.implementationtypename.replace('@', self.name))

    def implementation(self):
        lines = list(self.initializationexpr())
        lines[0] = '%s = %s' % (
            self.implementationtypename.replace('@', self.name),
            lines[0])
        lines[-1] += ';'
        return lines

    def getlength(self):
        return 1


class StructNode(ContainerNode):

    def basename(self):
        return self.T._name

    def enum_dependencies(self):
        for name in self.T._names:
            yield getattr(self.obj, name)

    def getlength(self):
        if self.T._arrayfld is None:
            return 1
        else:
            array = getattr(self.obj, self.T._arrayfld)
            return len(array.items)

    def initializationexpr(self, prefix=''):
        yield '{'
        if needs_refcount(self.T):
            yield '\t1,'
        for name in self.T._names:
            value = getattr(self.obj, name)
            if isinstance(typeOf(value), ContainerType):
                node = self.db.getcontainernode(value)
                expr = '\n'.join(node.initializationexpr(prefix+name+'.'))
                expr += ','
            else:
                expr = self.db.get(value)
                i = expr.find('\n')
                if i<0: i = len(expr)
                expr = '%s,\t/* %s%s */%s' % (expr[:i], prefix, name, expr[i:])
            expr = expr.replace('\n', '\n\t')      # indentation
            yield '\t%s' % expr
        yield '}'


class ArrayNode(ContainerNode):

    def basename(self):
        return 'array'

    def enum_dependencies(self):
        return self.obj.items

    def getlength(self):
        return len(self.obj.items)

    def initializationexpr(self, prefix=''):
        yield '{'
        if needs_refcount(self.T):
            yield '\t1,'
        yield '\t%d,' % len(self.obj.items)
        for j in range(len(self.obj.items)):
            node = self.db.getcontainernode(self.obj.items[j])
            expr = '\n'.join(node.initializationexpr('%s%d.' % (prefix, j)))
            expr += ','
            expr = expr.replace('\n', '\n\t')      # indentation
            yield '\t%s' % expr
        yield '}'


class FuncNode(ContainerNode):
    def basename(self):
        return self.obj._name
    def enum_dependencies(self):
        Booom

class PyObjectNode(ContainerNode):
    basename = 'BOOOM'


ContainerNodeClass = {
    Struct:   StructNode,
    GcStruct: StructNode,
    Array:    ArrayNode,
    GcArray:  ArrayNode,
    FuncType: FuncNode,
    PyObject: PyObjectNode,
    }
