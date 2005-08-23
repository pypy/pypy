from __future__ import generators
from pypy.rpython.lltype import Struct, Array, FuncType, PyObjectType, typeOf
from pypy.rpython.lltype import GcStruct, GcArray, GC_CONTAINER, ContainerType
from pypy.rpython.lltype import parentlink, Ptr, PyObject, Void, OpaqueType
from pypy.rpython.lltype import RuntimeTypeInfo, getRuntimeTypeInfo
from pypy.translator.c.funcgen import FunctionCodeGenerator
from pypy.translator.c.external import CExternalFunctionCodeGenerator
from pypy.translator.c.support import USESLOTS # set to False if necessary while refactoring
from pypy.translator.c.support import cdecl, somelettersfrom
from pypy.translator.c.primitive import PrimitiveType
from pypy.translator.c import extfunc
from pypy.rpython.rstr import STR


def needs_gcheader(T):
    if not isinstance(T, GC_CONTAINER):
        return False
    if isinstance(T, GcStruct):
        if T._names and isinstance(T._flds[T._names[0]], GC_CONTAINER):
            return False   # gcheader already in the first field
    return True

class StructDefNode:
    gcheader = None
    gcinfo = None

    def __init__(self, db, STRUCT, varlength=1):
        self.db = db
        self.STRUCT = STRUCT
        self.LLTYPE = STRUCT
        self.varlength = varlength
        if varlength == 1:
            basename = STRUCT._name
            with_number = True
        else:
            basename = db.gettypedefnode(STRUCT).barename
            basename = '%s_len%d' % (basename, varlength)
            with_number = False
        (self.barename,
         self.name) = db.namespace.uniquename(basename, with_number=with_number,
                                              bare=True)
        self.dependencies = {}
        self.prefix = somelettersfrom(STRUCT._name) + '_'

        gcpolicy = db.gcpolicy

        # look up the gcheader field
        if needs_gcheader(STRUCT):
            self.gcheader = gcpolicy.gcheader_field_name(self)
        elif isinstance(STRUCT, GcStruct):
            # gcheader in the first field
            T = self.c_struct_field_type(STRUCT._names[0])
            assert isinstance(T, GC_CONTAINER)
            firstdefnode = db.gettypedefnode(T)
            firstfieldname = self.c_struct_field_name(STRUCT._names[0])
            self.gcheader = '%s.%s' % (firstfieldname, firstdefnode.gcheader)

            # give the gcpolicy a chance to do sanity checking or special preparation for
            # this case
            gcpolicy.prepare_nested_gcstruct(self, T)

    def setup(self):
        # this computes self.fields
        self.fields = []
        db = self.db
        STRUCT = self.STRUCT
        varlength = self.varlength
        for name in STRUCT._names:
            T = self.c_struct_field_type(name)
            if name == STRUCT._arrayfld:
                typename = db.gettype(T, varlength=self.varlength,
                                         who_asks=self)
            else:
                typename = db.gettype(T, who_asks=self)
            self.fields.append((self.c_struct_field_name(name), typename))

        rtti = None
        if isinstance(STRUCT, GcStruct):
            try:
                rtti = getRuntimeTypeInfo(STRUCT)
            except ValueError:
                pass

        # let the gcpolicy do its own setup
        if varlength == 1:
            self.db.gcpolicy.struct_setup(self, rtti)

    def c_struct_field_name(self, name):
        return self.prefix + name

    def c_struct_field_type(self, name):
        return self.STRUCT._flds[name]

    def access_expr(self, baseexpr, fldname):
        fldname = self.c_struct_field_name(fldname)
        return '%s.%s' % (baseexpr, fldname)

    def definition(self, phase):
        gcpolicy = self.db.gcpolicy
        if phase == 1:
            yield 'struct %s {' % self.name
            # gcheader
            if needs_gcheader(self.STRUCT):
                for line in gcpolicy.struct_gcheader_definition(self):
                    yield '\t' + line

            for name, typename in self.fields:
                line = '%s;' % cdecl(typename, name)
                if typename == PrimitiveType[Void]:
                    line = '/* %s */' % line
                yield '\t' + line
            yield '};'
 
            for line in gcpolicy.struct_after_definition(self):
                yield line

        elif phase == 2:
            for line in gcpolicy.struct_implementationcode(self):
                yield line

    def visitor_lines(self, prefix, on_field):
        STRUCT = self.STRUCT
        for name in STRUCT._names:
            FIELD_T = self.c_struct_field_type(name)
            cname = self.c_struct_field_name(name)
            for line in on_field('%s.%s' % (prefix, cname),
                                 FIELD_T):
                yield line

    def debug_offsets(self):
        # generate number exprs giving the offset of the elements in the struct
        STRUCT = self.STRUCT
        for name in STRUCT._names:
            FIELD_T = self.c_struct_field_type(name)
            if FIELD_T == Void:
                yield '-1'
            else:
                cname = self.c_struct_field_name(name)
                yield 'offsetof(struct %s, %s)' % (self.name, cname)


class ArrayDefNode:
    gcheader = None
    gcinfo = None

    def __init__(self, db, ARRAY, varlength=1):
        self.db = db
        self.ARRAY = ARRAY
        self.LLTYPE = ARRAY
        original_varlength = varlength
        if ARRAY is STR.chars:
            varlength += 1   # for the NUL char terminator at the end of the string
        self.varlength = varlength
        if original_varlength == 1:
            basename = 'array'
            with_number = True
        else:
            basename = db.gettypedefnode(ARRAY).barename
            basename = '%s_len%d' % (basename, varlength)
            with_number = False
        (self.barename,
         self.name) = db.namespace.uniquename(basename, with_number=with_number,
                                              bare=True)
        self.dependencies = {}

        # look up the gcheader field name
        if needs_gcheader(ARRAY):
            self.gcheader = self.db.gcpolicy.gcheader_field_name(self)
 
    def setup(self):
        db = self.db
        ARRAY = self.ARRAY
        varlength = self.varlength
        self.itemtypename = db.gettype(ARRAY.OF, who_asks=self)

        # let the gcpolicy do its own setup
        if varlength == 1:
            self.db.gcpolicy.array_setup(self)

    def access_expr(self, baseexpr, index):
        return '%s.items[%d]' % (baseexpr, index)

    def definition(self, phase):
        gcpolicy = self.db.gcpolicy
        if phase == 1:
            yield 'struct %s {' % self.name
            # gcheader
            if needs_gcheader(self.ARRAY):
                for line in gcpolicy.array_gcheader_definition(self):
                    yield '\t' + line
            yield '\tlong length;'
            line = '%s;' % cdecl(self.itemtypename, 'items[%d]'% self.varlength)
            if self.ARRAY.OF == Void:    # strange
                line = '/* %s */' % line
            yield '\t' + line
            yield '};'

            for line in gcpolicy.array_after_definition(self):
                yield line

        elif phase == 2:
            for line in gcpolicy.array_implementationcode(self):
                yield line

    def visitor_lines(self, prefix, on_item):
        ARRAY = self.ARRAY
        # we need a unique name for this C variable, or at least one that does
        # not collide with the expression in 'prefix'
        i = 0
        varname = 'p0'
        while prefix.find(varname) >= 0:
            i += 1
            varname = 'p%d' % i
        body = list(on_item('(*%s)' % varname, ARRAY.OF))
        if body:
            yield '{'
            yield '\t%s = %s.items;' % (cdecl(self.itemtypename, '*' + varname),
                                        prefix)
            yield '\t%s = %s + %s.length;' % (cdecl(self.itemtypename,
                                                    '*%s_end' % varname),
                                              varname,
                                              prefix)
            yield '\twhile (%s != %s_end) {' % (varname, varname)
            for line in body:
                yield '\t\t' + line
            yield '\t\t%s++;' % varname
            yield '\t}'
            yield '}'

    def debug_offsets(self):
        # generate three offsets for debugging inspection
        yield 'offsetof(struct %s, length)' % (self.name,)
        if self.ARRAY.OF != Void:
            yield 'offsetof(struct %s, items[0])' % (self.name,)
            yield 'offsetof(struct %s, items[1])' % (self.name,)
        else:
            yield '-1'
            yield '-1'


class ExtTypeOpaqueDefNode:
    "For OpaqueTypes created by pypy.rpython.extfunctable.ExtTypeInfo."

    def __init__(self, db, T):
        self.db = db
        self.T = T
        self.dependencies = {}
        self.name = 'RPyOpaque_%s' % (T.tag,)

    def setup(self):
        pass

    def definition(self, phase):
        return []

# ____________________________________________________________


class ContainerNode(object):
    if USESLOTS:
        __slots__ = """db T obj 
                       typename implementationtypename
                        name ptrname
                        globalcontainer
                        includes""".split()

    def __init__(self, db, T, obj):
        self.includes = ()
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
        self.ptrname = '(&%s)' % self.name
        if self.typename != self.implementationtypename:
            self.ptrname = '((%s)(void*)%s)' % (self.typename.replace('@', '*'),
                                                self.ptrname)

    def forward_declaration(self):
        yield '%s;' % (
            cdecl(self.implementationtypename, self.name))

    def implementation(self):
        lines = list(self.initializationexpr())
        lines[0] = '%s = %s' % (
            cdecl(self.implementationtypename, self.name),
            lines[0])
        lines[-1] += ';'
        return lines

    def startupcode(self):
        return []

    def getlength(self):
        return 1

assert not USESLOTS or '__dict__' not in dir(ContainerNode)

class StructNode(ContainerNode):
    if USESLOTS:
        __slots__ = ()

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

    def initializationexpr(self, decoration=''):
        yield '{'
        if needs_gcheader(self.T):
            for line in self.db.gcpolicy.struct_gcheader_initialitionexpr(self):
                yield '\t' + line
        defnode = self.db.gettypedefnode(self.T)
        for name in self.T._names:
            value = getattr(self.obj, name)
            c_name = defnode.c_struct_field_name(name)
            expr = generic_initializationexpr(self.db, value,
                                              '%s.%s' % (self.name, c_name),
                                              decoration + name)
            yield '\t%s' % expr
        yield '}'

assert not USESLOTS or '__dict__' not in dir(StructNode)

class ArrayNode(ContainerNode):
    if USESLOTS:
        __slots__ = ()

    def basename(self):
        return 'array'

    def enum_dependencies(self):
        return self.obj.items

    def getlength(self):
        return len(self.obj.items)

    def initializationexpr(self, decoration=''):
        yield '{'
        if needs_gcheader(self.T):
            for line in self.db.gcpolicy.array_gcheader_initialitionexpr(self):
                yield '\t' + line
        if self.T.OF == Void or len(self.obj.items) == 0:
            yield '\t%d' % len(self.obj.items)
            yield '}'
        else:
            yield '\t%d, {' % len(self.obj.items)
            for j in range(len(self.obj.items)):
                value = self.obj.items[j]
                expr = generic_initializationexpr(self.db, value,
                                                '%s.items[%d]' % (self.name, j),
                                                '%s%d' % (decoration, j))
                yield '\t%s' % expr
            yield '} }'

assert not USESLOTS or '__dict__' not in dir(ArrayNode)

def generic_initializationexpr(db, value, access_expr, decoration):
    if isinstance(typeOf(value), ContainerType):
        node = db.getcontainernode(value)
        expr = '\n'.join(node.initializationexpr(decoration+'.'))
        expr += ','
    else:
        comma = ','
        if typeOf(value) == Ptr(PyObject) and value:
            # cannot just write 'gxxx' as a constant in a structure :-(
            node = db.getcontainernode(value._obj)
            expr = 'NULL /*%s*/' % node.name
            node.where_to_copy_me.append('&%s' % access_expr)
        else:
            expr = db.get(value)
            if typeOf(value) == Void:
                comma = ''
        expr += comma
        i = expr.find('\n')
        if i<0: i = len(expr)
        expr = '%s\t/* %s */%s' % (expr[:i], decoration, expr[i:])
    return expr.replace('\n', '\n\t')      # indentation

# ____________________________________________________________


class FuncNode(ContainerNode):
    if USESLOTS:
        __slots__ = """funcgen""".split()

    def __init__(self, db, T, obj):
        self.globalcontainer = True
        self.funcgen = select_function_code_generator(obj, db)
        self.db = db
        self.T = T
        self.obj = obj
        #self.dependencies = {}
        self.typename = db.gettype(T)  #, who_asks=self)
        if self.funcgen:
            argnames = self.funcgen.argnames()
            self.implementationtypename = db.gettype(T, argnames=argnames)
        if hasattr(obj, 'includes'):
            self.includes = obj.includes
            self.name = self.basename()
        else:
            self.includes = ()
            self.name = db.namespace.uniquename('g_' + self.basename())
        self.ptrname = self.name

    def basename(self):
        return self.obj._name

    def enum_dependencies(self):
        if self.funcgen is None:
            return []
        return self.funcgen.allconstantvalues()

    def forward_declaration(self):
        if self.funcgen:
            return ContainerNode.forward_declaration(self)
        else:
            return []

    def implementation(self):
        funcgen = self.funcgen
        if funcgen is None:
            return
        funcgen.implementation_begin()
        yield '%s {' % cdecl(self.implementationtypename, self.name)
        #
        # declare the local variables
        #
        localnames = list(funcgen.cfunction_declarations())
        lengths = [len(a) for a in localnames]
        lengths.append(9999)
        start = 0
        while start < len(localnames):
            # pack the local declarations over as few lines as possible
            total = lengths[start] + 8
            end = start+1
            while total + lengths[end] < 77:
                total += lengths[end] + 1
                end += 1
            yield '\t' + ' '.join(localnames[start:end])
            start = end
        #
        # generate the body itself
        #
        lineprefix = ''
        for line in funcgen.cfunction_body():
            # performs some formatting on the generated body:
            # indent normal lines with tabs; indent labels less than the rest
            if line.endswith(':'):
                if line.startswith('err'):
                    lineprefix += '\t' + line
                    continue  # merge this 'err:' label with the following line
                else:
                    fmt = '%s    %s'
            elif line:
                fmt = '%s\t%s'
            else:
                fmt = '%s%s'
            yield fmt % (lineprefix, line)
            lineprefix = ''

        if lineprefix:         # unlikely
            yield lineprefix
        yield '}'
        funcgen.implementation_end()

assert not USESLOTS or '__dict__' not in dir(FuncNode)

def select_function_code_generator(fnobj, db):
    if fnobj._callable in extfunc.EXTERNALS:
        # 'fnobj' is one of the ll_xyz() functions with the suggested_primitive
        # flag in pypy.rpython.module.*.  The corresponding C wrappers are
        # written by hand in src/ll_*.h, and declared in extfunc.EXTERNALS.
        db.externalfuncs[fnobj._callable] = fnobj
        return None
    elif getattr(fnobj._callable, 'suggested_primitive', False):
        raise ValueError, "trying to compile suggested primitive %r" % (
            fnobj._callable,)
    elif hasattr(fnobj, 'graph'):
        cpython_exc = getattr(fnobj, 'exception_policy', None) == "CPython"
        return FunctionCodeGenerator(fnobj.graph, db, cpython_exc)
    elif getattr(fnobj, 'external', None) == 'C':
        # deprecated case
        if getattr(fnobj, 'includes', None):
            return None   # assume no wrapper needed
        else:
            return CExternalFunctionCodeGenerator(fnobj, db)
    else:
        raise ValueError, "don't know how to generate code for %r" % (fnobj,)

# xxx move it completly to the gcpolicy
class RuntimeTypeInfo_OpaqueNode(ContainerNode):
    globalcontainer = True
    includes = ()

    def __init__(self, db, T, obj):
        assert T == RuntimeTypeInfo
        assert isinstance(obj.about, GcStruct)
        self.db = db
        self.T = T
        self.obj = obj
        defnode = db.gettypedefnode(obj.about)

        self.db.gcpolicy.rtti_node(defnode, self)

    def enum_dependencies(self):
        return []

    def implementation(self):
        return []


class ExtType_OpaqueNode(ContainerNode):

    def enum_dependencies(self):
        return []

    def initializationexpr(self, decoration=''):
        yield 'RPyOpaque_INITEXPR_%s' % (self.T.tag,)

    def startupcode(self):
        args = [self.ptrname]
        # XXX how to make this code more generic?
        if self.T.tag == 'ThreadLock':
            lock = self.obj.externalobj
            if lock.locked():
                args.append('1')
            else:
                args.append('0')
        yield 'RPyOpaque_SETUP_%s(%s);' % (self.T.tag, ', '.join(args))


def opaquenode_factory(db, T, obj):
    if T == RuntimeTypeInfo:
        return RuntimeTypeInfo_OpaqueNode(db, T, obj)
    if hasattr(T, '_exttypeinfo'):
        return ExtType_OpaqueNode(db, T, obj)
    raise Exception("don't know about %r" % (T,))


class PyObjectNode(ContainerNode):
    globalcontainer = True
    typename = 'PyObject @'
    implementationtypename = 'PyObject *@'
    includes = ()

    def __init__(self, db, T, obj):
        # obj is a _pyobject here; obj.value is the underlying CPython object
        self.db = db
        self.T = T
        self.obj = obj
        self.name = db.pyobjmaker.computenameof(obj.value)
        self.ptrname = self.name
        # a list of expressions giving places where this constant PyObject
        # must be copied.  Normally just in the global variable of the same
        # name, but see also StructNode.initializationexpr()  :-(
        self.where_to_copy_me = []
        if self.name not in db.pyobjmaker.wrappers:
            self.where_to_copy_me.append('&%s' % self.name)

    def enum_dependencies(self):
        return []

    def implementation(self):
        return []


ContainerNodeFactory = {
    Struct:       StructNode,
    GcStruct:     StructNode,
    Array:        ArrayNode,
    GcArray:      ArrayNode,
    FuncType:     FuncNode,
    OpaqueType:   opaquenode_factory,
    PyObjectType: PyObjectNode,
    }
