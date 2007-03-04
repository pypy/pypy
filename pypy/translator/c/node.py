from __future__ import generators
from pypy.rpython.lltypesystem.lltype import \
     Struct, Array, FixedSizeArray, FuncType, PyObjectType, typeOf, \
     GcStruct, GcArray, RttiStruct, PyStruct, ContainerType, \
     parentlink, Ptr, PyObject, Void, OpaqueType, Float, \
     RuntimeTypeInfo, getRuntimeTypeInfo, Char, _subarray, _pyobjheader
from pypy.rpython.lltypesystem.llmemory import WeakGcAddress
from pypy.translator.c.funcgen import FunctionCodeGenerator
from pypy.translator.c.external import CExternalFunctionCodeGenerator
from pypy.translator.c.support import USESLOTS # set to False if necessary while refactoring
from pypy.translator.c.support import cdecl, forward_cdecl, somelettersfrom
from pypy.translator.c.support import c_char_array_constant
from pypy.translator.c.primitive import PrimitiveType, isinf, isnan
from pypy.translator.c import extfunc


def needs_gcheader(T):
    if not isinstance(T, ContainerType):
        return False
    if T._gckind != 'gc':
        return False
    if isinstance(T, GcStruct):
        if T._first_struct() != (None, None):
            return False   # gcheader already in the first field
    return True

class defaultproperty(object):
    def __init__(self, fget):
        self.fget = fget
    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        else:
            return self.fget(obj)


class StructDefNode:
    typetag = 'struct'
    is_external = False
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
        if STRUCT._hints.get('union'):
            self.typetag = 'union'
            assert STRUCT._gckind == 'raw'   # not supported: "GcUnion"
        if STRUCT._hints.get('typedef'):
            self.typetag = ''
            assert STRUCT._hints.get('external')
        if self.STRUCT._hints.get('external'):      # XXX hack
            self.is_external = True
        if STRUCT._hints.get('c_name'):
            self.barename = self.name = STRUCT._hints['c_name']
            self.c_struct_field_name = self.verbatim_field_name
        else:
            (self.barename,
             self.name) = db.namespace.uniquename(basename,
                                                  with_number=with_number,
                                                  bare=True)
            self.prefix = somelettersfrom(STRUCT._name) + '_'
        self.dependencies = {}

    def setup(self):
        # this computes self.fields
        if self.STRUCT._hints.get('external'):      # XXX hack
            self.fields = None    # external definition only
            return
        self.fields = []
        db = self.db
        STRUCT = self.STRUCT
        varlength = self.varlength
        if needs_gcheader(self.STRUCT):
            for fname, T in db.gcpolicy.struct_gcheader_definition(self):
                self.fields.append((fname, db.gettype(T, who_asks=self)))
        for name in STRUCT._names:
            T = self.c_struct_field_type(name)
            if name == STRUCT._arrayfld:
                typename = db.gettype(T, varlength=self.varlength,
                                         who_asks=self)
            else:
                typename = db.gettype(T, who_asks=self)
            self.fields.append((self.c_struct_field_name(name), typename))
        self.gcinfo  # force it to be computed

    def computegcinfo(self):
        # let the gcpolicy do its own setup
        self.gcinfo = None   # unless overwritten below
        rtti = None
        STRUCT = self.STRUCT
        if isinstance(STRUCT, RttiStruct):
            try:
                rtti = getRuntimeTypeInfo(STRUCT)
            except ValueError:
                pass
        if self.varlength == 1:
            self.db.gcpolicy.struct_setup(self, rtti)
        return self.gcinfo
    gcinfo = defaultproperty(computegcinfo)

    def gettype(self):
        return '%s %s @' % (self.typetag, self.name)

    def c_struct_field_name(self, name):
        # occasionally overridden in __init__():
        #    self.c_struct_field_name = self.verbatim_field_name
        return self.prefix + name

    def verbatim_field_name(self, name):
        if name.startswith('c_'):   # produced in this way by rctypes
            return name[2:]
        else:
            # field names have to start with 'c_' or be meant for names that
            # vanish from the C source, like 'head' if 'inline_head' is set
            raise ValueError("field %r should not be accessed in this way" % (
                name,))

    def c_struct_field_type(self, name):
        return self.STRUCT._flds[name]

    def access_expr(self, baseexpr, fldname):
        if self.STRUCT._hints.get('inline_head'):
            first, FIRST = self.STRUCT._first_struct()
            if fldname == first:
                # "invalid" cast according to C99 but that's what CPython
                # requires and does all the time :-/
                return '(*(%s) &(%s))' % (cdecl(self.db.gettype(FIRST), '*'),
                                          baseexpr)
        fldname = self.c_struct_field_name(fldname)
        return '%s.%s' % (baseexpr, fldname)

    def ptr_access_expr(self, baseexpr, fldname):
        if self.STRUCT._hints.get('inline_head'):
            first, FIRST = self.STRUCT._first_struct()
            if fldname == first:
                # "invalid" cast according to C99 but that's what CPython
                # requires and does all the time :-/
                return '(*(%s) %s)' % (cdecl(self.db.gettype(FIRST), '*'),
                                       baseexpr)
        fldname = self.c_struct_field_name(fldname)
        return '%s->%s' % (baseexpr, fldname)

    def definition(self):
        if self.fields is None:   # external definition only
            return
        yield '%s %s {' % (self.typetag, self.name)
        is_empty = True
        for name, typename in self.fields:
            line = '%s;' % cdecl(typename, name)
            if typename == PrimitiveType[Void]:
                line = '/* %s */' % line
            else:
                is_empty = False
            yield '\t' + line
        if is_empty:
            yield '\t' + 'char _dummy; /* this struct is empty */'
        yield '};'
        for line in self.db.gcpolicy.struct_after_definition(self):
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
            if FIELD_T is Void:
                yield '-1'
            else:
                try:
                    cname = self.c_struct_field_name(name)
                except ValueError:
                    yield '-1'
                else:
                    yield 'offsetof(%s %s, %s)' % (self.typetag,
                                                   self.name, cname)


class ArrayDefNode:
    typetag = 'struct'

    def __init__(self, db, ARRAY, varlength=1):
        self.db = db
        self.ARRAY = ARRAY
        self.LLTYPE = ARRAY
        original_varlength = varlength
        self.gcfields = []
        
        if ARRAY._hints.get('isrpystring'):
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
 
    def setup(self):
        db = self.db
        ARRAY = self.ARRAY
        self.itemtypename = db.gettype(ARRAY.OF, who_asks=self)
        self.gcinfo    # force it to be computed
        if needs_gcheader(ARRAY):
            for fname, T in db.gcpolicy.array_gcheader_definition(self):
                self.gcfields.append((fname, db.gettype(T, who_asks=self)))

    def computegcinfo(self):
        # let the gcpolicy do its own setup
        self.gcinfo = None   # unless overwritten below
        if self.varlength == 1:
            self.db.gcpolicy.array_setup(self)
        return self.gcinfo
    gcinfo = defaultproperty(computegcinfo)

    def gettype(self):
        return 'struct %s @' % self.name

    def access_expr(self, baseexpr, index):
        return '%s.items[%d]' % (baseexpr, index)

    def ptr_access_expr(self, baseexpr, index):
        return '%s->items[%d]' % (baseexpr, index)

    def definition(self):
        gcpolicy = self.db.gcpolicy
        yield 'struct %s {' % self.name
        for fname, typename in self.gcfields:
            yield '\t' + cdecl(typename, fname) + ';'
        if not self.ARRAY._hints.get('nolength', False):
            yield '\tlong length;'
        line = '%s;' % cdecl(self.itemtypename, 'items[%d]'% self.varlength)
        if self.ARRAY.OF is Void:    # strange
            line = '/* %s */' % line
        yield '\t' + line
        yield '};'

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
        if not self.ARRAY._hints.get('nolength', False):
            yield 'offsetof(struct %s, length)' % (self.name,)
        else:
            yield '-1'
        if self.ARRAY.OF is not Void:
            yield 'offsetof(struct %s, items[0])' % (self.name,)
            yield 'offsetof(struct %s, items[1])' % (self.name,)
        else:
            yield '-1'
            yield '-1'


class FixedSizeArrayDefNode:
    gcinfo = None
    name = None
    typetag = 'struct'

    def __init__(self, db, FIXEDARRAY):
        self.db = db
        self.FIXEDARRAY = FIXEDARRAY
        self.LLTYPE = FIXEDARRAY
        self.dependencies = {}
        self.itemtypename = db.gettype(FIXEDARRAY.OF, who_asks=self)

    def setup(self):
        """Loops are forbidden by ForwardReference.become() because
        there is no way to declare them in C."""

    def gettype(self):
        FIXEDARRAY = self.FIXEDARRAY
        return self.itemtypename.replace('@', '(@)[%d]' % FIXEDARRAY.length)

    def getptrtype(self):
        return self.itemtypename.replace('@', '*@')

    def access_expr(self, baseexpr, index):
        if not isinstance(index, int):
            assert index.startswith('item')
            index = int(index[4:])
        return '%s[%d]' % (baseexpr, index)

    ptr_access_expr = access_expr

    def definition(self):
        return []    # no declaration is needed

    def visitor_lines(self, prefix, on_item):
        FIXEDARRAY = self.FIXEDARRAY
        # we need a unique name for this C variable, or at least one that does
        # not collide with the expression in 'prefix'
        i = 0
        varname = 'p0'
        while prefix.find(varname) >= 0:
            i += 1
            varname = 'p%d' % i
        body = list(on_item('(*%s)' % varname, FIXEDARRAY.OF))
        if body:
            yield '{'
            yield '\t%s = %s;' % (cdecl(self.itemtypename, '*' + varname),
                                  prefix)
            yield '\t%s = %s + %d;' % (cdecl(self.itemtypename,
                                             '*%s_end' % varname),
                                       varname,
                                       FIXEDARRAY.length)
            yield '\twhile (%s != %s_end) {' % (varname, varname)
            for line in body:
                yield '\t\t' + line
            yield '\t\t%s++;' % varname
            yield '\t}'
            yield '}'

    def debug_offsets(self):
        # XXX not implemented
        return []


class ExtTypeOpaqueDefNode:
    "For OpaqueTypes created by pypy.rpython.extfunctable.ExtTypeInfo."
    typetag = 'struct'

    def __init__(self, db, T):
        self.db = db
        self.T = T
        self.dependencies = {}
        self.name = 'RPyOpaque_%s' % (T.tag,)

    def setup(self):
        pass

    def definition(self):
        return []

# ____________________________________________________________


class ContainerNode(object):
    if USESLOTS:
        __slots__ = """db T obj 
                       typename implementationtypename
                        name ptrname
                        globalcontainer""".split()

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
        self.ptrname = '(&%s)' % self.name
        if self.typename != self.implementationtypename:
            ptrtypename = db.gettype(Ptr(T))
            self.ptrname = '((%s)(void*)%s)' % (cdecl(ptrtypename, ''),
                                                self.ptrname)

    def is_thread_local(self):
        return hasattr(self.T, "_hints") and self.T._hints.get('thread_local')

    def forward_declaration(self):
        yield '%s;' % (
            forward_cdecl(self.implementationtypename,
                self.name, self.db.standalone, self.is_thread_local()))

    def implementation(self):
        lines = list(self.initializationexpr())
        lines[0] = '%s = %s' % (
            cdecl(self.implementationtypename, self.name, self.is_thread_local()),
            lines[0])
        lines[-1] += ';'
        return lines

    def startupcode(self):
        return []

    def getlength(self):
        return 1

assert not USESLOTS or '__dict__' not in dir(ContainerNode)

class StructNode(ContainerNode):
    nodekind = 'struct'
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
        is_empty = True
        yield '{'
        defnode = self.db.gettypedefnode(self.T)

        data = []

        if needs_gcheader(self.T):
            for i, thing in enumerate(self.db.gcpolicy.struct_gcheader_initdata(self)):
                data.append(('gcheader%d'%i, thing))
        
        for name in self.T._names:
            data.append((name, getattr(self.obj, name)))
        
        # You can only initialise the first field of a union in c
        # XXX what if later fields have some initialisation?
        if hasattr(self.T, "_hints") and self.T._hints.get('union'):
            data = data[0:1]

        for name, value in data:
            if isinstance(value, _pyobjheader):   # hack
                node = self.db.getcontainernode(value)
                lines = [node.pyobj_initexpr()]
            else:
                c_expr = defnode.access_expr(self.name, name)
                lines = generic_initializationexpr(self.db, value, c_expr,
                                                   decoration + name)
            for line in lines:
                yield '\t' + line
            if not lines[0].startswith('/*'):
                is_empty = False
        if is_empty:
            yield '\t%s' % '0,'
        yield '}'

assert not USESLOTS or '__dict__' not in dir(StructNode)

class ArrayNode(ContainerNode):
    nodekind = 'array'
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
            for i, thing in enumerate(self.db.gcpolicy.array_gcheader_initdata(self)):
                lines = generic_initializationexpr(self.db, thing,
                                                   'gcheader%d'%i,
                                                   '%sgcheader%d' % (decoration, i))
                for line in lines:
                    yield line
        if self.T.OF is Void or len(self.obj.items) == 0:
            yield '\t%d' % len(self.obj.items)
            yield '}'
        elif self.T.OF == Char:
            yield '\t%d, %s' % (len(self.obj.items),
                                c_char_array_constant(''.join(self.obj.items)))
            yield '}'
        else:
            yield '\t%d, {' % len(self.obj.items)
            for j in range(len(self.obj.items)):
                value = self.obj.items[j]
                lines = generic_initializationexpr(self.db, value,
                                                '%s.items[%d]' % (self.name, j),
                                                '%s%d' % (decoration, j))
                for line in lines:
                    yield '\t' + line
            yield '} }'

assert not USESLOTS or '__dict__' not in dir(ArrayNode)

class FixedSizeArrayNode(ContainerNode):
    nodekind = 'array'
    if USESLOTS:
        __slots__ = ()

    def __init__(self, db, T, obj):
        ContainerNode.__init__(self, db, T, obj)
        if not isinstance(obj, _subarray):   # XXX hackish
            self.ptrname = self.name

    def basename(self):
        return self.T._name

    def enum_dependencies(self):
        for i in range(self.obj.getlength()):
            yield self.obj.getitem(i)

    def getlength(self):
        return 1    # not variable-sized!

    def initializationexpr(self, decoration=''):
        is_empty = True
        yield '{'
        # _names == ['item0', 'item1', ...]
        for j, name in enumerate(self.T._names):
            value = getattr(self.obj, name)
            lines = generic_initializationexpr(self.db, value,
                                               '%s[%d]' % (self.name, j),
                                               '%s%d' % (decoration, j))
            for line in lines:
                yield '\t' + line
        yield '}'

def generic_initializationexpr(db, value, access_expr, decoration):
    if isinstance(typeOf(value), ContainerType):
        node = db.getcontainernode(value)
        lines = list(node.initializationexpr(decoration+'.'))
        lines[-1] += ','
        return lines
    else:
        comma = ','
        if typeOf(value) == Ptr(PyObject) and value:
            # cannot just write 'gxxx' as a constant in a structure :-(
            node = db.getcontainernode(value._obj)
            expr = 'NULL /*%s*/' % node.name
            node.where_to_copy_me.append('&%s' % access_expr)
        elif typeOf(value) == Float and (isinf(value) or isnan(value)):
            db.late_initializations.append(('%s' % access_expr, db.get(value)))
            expr = '0.0 /* patched later by %sinfinity */' % (
                '-+'[value > 0])
        elif typeOf(value) == WeakGcAddress and value.ref is not None:
            db.late_initializations.append(('%s' % access_expr, db.get(value)))
            expr = 'HIDE_POINTER(NULL) /* patched later */'
        else:
            expr = db.get(value)
            if typeOf(value) is Void:
                comma = ''
        expr += comma
        i = expr.find('\n')
        if i<0: i = len(expr)
        expr = '%s\t/* %s */%s' % (expr[:i], decoration, expr[i:])
        return expr.split('\n')

# ____________________________________________________________


class FuncNode(ContainerNode):
    nodekind = 'func'
    # there not so many node of this kind, slots should not
    # be necessary

    def __init__(self, db, T, obj, forcename=None):
        self.globalcontainer = True
        self.db = db
        self.T = T
        self.obj = obj
        if hasattr(obj, 'includes'):
            self.includes = obj.includes
            self.name = forcename or self.basename()
        else:
            self.name = (forcename or
                         db.namespace.uniquename('g_' + self.basename()))
        if hasattr(obj, 'libraries'):
            self.libraries = obj.libraries
        self.make_funcgens()
        #self.dependencies = {}
        self.typename = db.gettype(T)  #, who_asks=self)
        self.ptrname = self.name

    def make_funcgens(self):
        self.funcgens = select_function_code_generators(self.obj, self.db, self.name)
        if self.funcgens:
            argnames = self.funcgens[0].argnames()  #Assume identical for all funcgens
            self.implementationtypename = self.db.gettype(self.T, argnames=argnames)

    def basename(self):
        return self.obj._name

    def enum_dependencies(self):
        if not self.funcgens:
            return []
        return self.funcgens[0].allconstantvalues() #Assume identical for all funcgens

    def forward_declaration(self):
        for funcgen in self.funcgens:
            yield '%s;' % (
                forward_cdecl(self.implementationtypename,
                    funcgen.name(self.name), self.db.standalone))

    def implementation(self):
        for funcgen in self.funcgens:
            for s in self.funcgen_implementation(funcgen):
                yield s

    def funcgen_implementation(self, funcgen):
        funcgen.implementation_begin()
        # recompute implementationtypename as the argnames may have changed
        argnames = funcgen.argnames()
        implementationtypename = self.db.gettype(self.T, argnames=argnames)
        yield '%s {' % cdecl(implementationtypename, funcgen.name(self.name))
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
        bodyiter = funcgen.cfunction_body()
        for line in bodyiter:
            # performs some formatting on the generated body:
            # indent normal lines with tabs; indent labels less than the rest
            if line.endswith(':'):
                if line.startswith('err'):
                    try:
                        nextline = bodyiter.next()
                    except StopIteration:
                        nextline = ''
                    # merge this 'err:' label with the following line
                    line = '\t%s\t%s' % (line, nextline)
                else:
                    line = '    ' + line
            elif line:
                line = '\t' + line
            yield line

        yield '}'
        del bodyiter
        funcgen.implementation_end()

def select_function_code_generators(fnobj, db, functionname):
    if hasattr(fnobj, '_external_name'):
        db.externalfuncs[fnobj._external_name] = fnobj
        return []
    elif fnobj._callable in extfunc.EXTERNALS:
        # 'fnobj' is one of the ll_xyz() functions with the suggested_primitive
        # flag in pypy.rpython.module.*.  The corresponding C wrappers are
        # written by hand in src/ll_*.h, and declared in extfunc.EXTERNALS.
        db.externalfuncs[fnobj._callable] = fnobj
        return []
    elif getattr(fnobj._callable, 'suggested_primitive', False):
        raise ValueError, "trying to compile suggested primitive %r" % (
            fnobj._callable,)
    elif hasattr(fnobj, 'graph'):
        exception_policy = getattr(fnobj, 'exception_policy', None)
        return [FunctionCodeGenerator(fnobj.graph, db, exception_policy,
                                      functionname)]
    elif getattr(fnobj, 'external', None) == 'C':
        # deprecated case
        if hasattr(fnobj, 'includes'):
            return []   # assume no wrapper needed
        else:
            return [CExternalFunctionCodeGenerator(fnobj, db)]
    else:
        raise ValueError, "don't know how to generate code for %r" % (fnobj,)

class ExtType_OpaqueNode(ContainerNode):
    nodekind = 'rpyopaque'

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
        return db.gcpolicy.rtti_node_factory()(db, T, obj)
    if hasattr(T, '_exttypeinfo'):
        return ExtType_OpaqueNode(db, T, obj)
    raise Exception("don't know about %r" % (T,))


class PyObjectNode(ContainerNode):
    nodekind = 'pyobj'
    globalcontainer = True
    typename = 'PyObject @'
    implementationtypename = 'PyObject *@'

    def __init__(self, db, T, obj):
        # obj is a _pyobject here; obj.value is the underlying CPython object
        self.db = db
        self.T = T
        self.obj = obj
        self.name = db.pyobjmaker.computenameof(obj.value)
        self.ptrname = self.name
        self.exported_name = self.name
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


class PyObjHeadNode(ContainerNode):
    nodekind = 'pyobj'

    def __init__(self, db, T, obj):
        ContainerNode.__init__(self, db, T, obj)
        self.where_to_copy_me = []
        self.exported_name = db.namespace.uniquename('cpyobj')

    def basename(self):
        raise Exception("PyObjHead should always have a parent")

    def enum_dependencies(self):
        yield self.obj.ob_type
        if self.obj.setup_fnptr:
            yield self.obj.setup_fnptr

    def get_setupfn_name(self):
        if self.obj.setup_fnptr:
            return self.db.get(self.obj.setup_fnptr)
        else:
            return 'NULL'

    def pyobj_initexpr(self):
        parent, parentindex = parentlink(self.obj)
        typenode = self.db.getcontainernode(self.obj.ob_type._obj)
        typenode.where_to_copy_me.append('(PyObject **) & %s.ob_type' % (
            self.name,))
        if typeOf(parent)._hints.get('inline_head'):
            return 'PyObject_HEAD_INIT(NULL)'
        else:
            return '{ PyObject_HEAD_INIT(NULL) },'


def objectnode_factory(db, T, obj):
    if isinstance(obj, _pyobjheader):
        return PyObjHeadNode(db, T, obj)
    else:
        return PyObjectNode(db, T, obj)


ContainerNodeFactory = {
    Struct:       StructNode,
    GcStruct:     StructNode,
    PyStruct:     StructNode,
    Array:        ArrayNode,
    GcArray:      ArrayNode,
    FixedSizeArray: FixedSizeArrayNode,
    FuncType:     FuncNode,
    OpaqueType:   opaquenode_factory,
    PyObjectType: objectnode_factory,
    }
