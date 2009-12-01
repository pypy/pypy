from pypy.rpython.lltypesystem.lltype import \
     Struct, Array, FixedSizeArray, FuncType, PyObjectType, typeOf, \
     GcStruct, GcArray, RttiStruct, ContainerType, \
     parentlink, Ptr, PyObject, Void, OpaqueType, Float, \
     RuntimeTypeInfo, getRuntimeTypeInfo, Char, _subarray
from pypy.rpython.lltypesystem import llmemory, llgroup
from pypy.translator.c.funcgen import FunctionCodeGenerator
from pypy.translator.c.external import CExternalFunctionCodeGenerator
from pypy.translator.c.support import USESLOTS # set to False if necessary while refactoring
from pypy.translator.c.support import cdecl, forward_cdecl, somelettersfrom
from pypy.translator.c.support import c_char_array_constant, barebonearray
from pypy.translator.c.primitive import PrimitiveType, name_signed
from pypy.rlib.rarithmetic import isinf, isnan
from pypy.translator.c import extfunc
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from py.builtin import BaseException

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
            self.forward_decl = None
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
        #
        self.fieldnames = STRUCT._names
        if STRUCT._hints.get('typeptr', False):
            if db.gcpolicy.need_no_typeptr():
                assert self.fieldnames == ('typeptr',)
                self.fieldnames = ()

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
        for name in self.fieldnames:
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
        assert name.startswith('c_')   # produced in this way by rffi
        return name[2:]

    def c_struct_field_type(self, name):
        return self.STRUCT._flds[name]

    def access_expr(self, baseexpr, fldname):
        fldname = self.c_struct_field_name(fldname)
        return '%s.%s' % (baseexpr, fldname)

    def ptr_access_expr(self, baseexpr, fldname):
        fldname = self.c_struct_field_name(fldname)
        return 'RPyField(%s, %s)' % (baseexpr, fldname)

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

    def visitor_lines(self, prefix, on_field):
        for name in self.fieldnames:
            FIELD_T = self.c_struct_field_type(name)
            cname = self.c_struct_field_name(name)
            for line in on_field('%s.%s' % (prefix, cname),
                                 FIELD_T):
                yield line

    def debug_offsets(self):
        # generate number exprs giving the offset of the elements in the struct
        for name in self.fieldnames:
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
        if hasattr(self, 'itemtypename'):
            return      # setup() was already called, likely by __init__
        db = self.db
        ARRAY = self.ARRAY
        self.gcinfo    # force it to be computed
        if needs_gcheader(ARRAY):
            for fname, T in db.gcpolicy.array_gcheader_definition(self):
                self.gcfields.append((fname, db.gettype(T, who_asks=self)))
        self.itemtypename = db.gettype(ARRAY.OF, who_asks=self)

    def computegcinfo(self):
        # let the gcpolicy do its own setup
        self.gcinfo = None   # unless overwritten below
        if self.varlength == 1:
            self.db.gcpolicy.array_setup(self)
        return self.gcinfo
    gcinfo = defaultproperty(computegcinfo)

    def gettype(self):
        return '%s %s @' % (self.typetag, self.name)

    def getptrtype(self):
        return '%s %s *@' % (self.typetag, self.name)

    def access_expr(self, baseexpr, index):
        return '%s.items[%s]' % (baseexpr, index)
    access_expr_varindex = access_expr

    def ptr_access_expr(self, baseexpr, index):
        assert 0 <= index <= sys.maxint, "invalid constant index %r" % (index,)
        return self.itemindex_access_expr(baseexpr, index)

    def itemindex_access_expr(self, baseexpr, indexexpr):
        if self.ARRAY._hints.get('nolength', False):
            return 'RPyNLenItem(%s, %s)' % (baseexpr, indexexpr)
        else:
            return 'RPyItem(%s, %s)' % (baseexpr, indexexpr)

    def definition(self):
        gcpolicy = self.db.gcpolicy
        yield 'struct %s {' % self.name
        for fname, typename in self.gcfields:
            yield '\t' + cdecl(typename, fname) + ';'
        if not self.ARRAY._hints.get('nolength', False):
            yield '\tlong length;'
        line = '%s;' % cdecl(self.itemtypename, 'items[%d]'% self.varlength)
        if self.ARRAY.OF is Void:    # strange
            line = '/* array of void */'
            if self.ARRAY._hints.get('nolength', False):
                line = 'char _dummy; ' + line
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


class BareBoneArrayDefNode:
    """For 'simple' array types which don't need a length nor GC headers.
    Implemented directly as a C array instead of a struct with an items field.
    rffi kind of expects such arrays to be 'bare' C arrays.
    """
    gcinfo = None
    name = None
    forward_decl = None

    def __init__(self, db, ARRAY, varlength=1):
        self.db = db
        self.ARRAY = ARRAY
        self.LLTYPE = ARRAY
        self.varlength = varlength
        self.dependencies = {}
        self.itemtypename = db.gettype(ARRAY.OF, who_asks=self)

    def setup(self):
        """Array loops are forbidden by ForwardReference.become() because
        there is no way to declare them in C."""

    def gettype(self):
        return self.itemtypename.replace('@', '(@)[%d]' % (self.varlength,))

    def getptrtype(self):
        return self.itemtypename.replace('@', '*@')

    def access_expr(self, baseexpr, index):
        return '%s[%d]' % (baseexpr, index)
    access_expr_varindex = access_expr

    def ptr_access_expr(self, baseexpr, index):
        assert 0 <= index <= sys.maxint, "invalid constant index %r" % (index,)
        return self.itemindex_access_expr(baseexpr, index)

    def itemindex_access_expr(self, baseexpr, indexexpr):
        return 'RPyBareItem(%s, %s)' % (baseexpr, indexexpr)

    def definition(self):
        return []    # no declaration is needed

    def visitor_lines(self, prefix, on_item):
        raise Exception("cannot visit C arrays - don't know the length")

    def debug_offsets(self):
        # generate three offsets for debugging inspection,
        yield '-1'     # no length
        yield '0'      # first element is immediately at the start of the array
        yield 'sizeof(%s)' % (cdecl(self.itemtypename, ''),)


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
        if not (0 <= index < self.FIXEDARRAY.length):
            raise IndexError("refusing to generate a statically out-of-bounds"
                             " array indexing")
        return '%s[%d]' % (baseexpr, index)

    ptr_access_expr = access_expr

    def access_expr_varindex(self, baseexpr, index):
        return '%s[%s]' % (baseexpr, index)

    def itemindex_access_expr(self, baseexpr, indexexpr):
        return 'RPyFxItem(%s, %s, %d)' % (baseexpr, indexexpr,
                                          self.FIXEDARRAY.length)

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
    """For OpaqueTypes created with the hint render_structure."""
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
        if llgroup.member_of_group(self.obj):
            return
        yield '%s;' % (
            forward_cdecl(self.implementationtypename,
                self.name, self.db.standalone, self.is_thread_local()))

    def implementation(self):
        if llgroup.member_of_group(self.obj):
            return []
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
        
        for name in defnode.fieldnames:
            data.append((name, getattr(self.obj, name)))
        
        # Reasonably, you should only initialise one of the fields of a union
        # in C.  This is possible with the syntax '.fieldname value' or
        # '.fieldname = value'.  But here we don't know which of the
        # fields need initialization, so XXX we pick the first one
        # arbitrarily.
        if hasattr(self.T, "_hints") and self.T._hints.get('union'):
            data = data[0:1]

        for name, value in data:
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

class GcStructNodeWithHash(StructNode):
    # for the outermost level of nested structures, if it has a _hash_cache_.
    nodekind = 'struct'
    if USESLOTS:
        __slots__ = ()

    def get_hash_typename(self):
        return 'struct _hashT_%s @' % self.name

    def forward_declaration(self):
        hash_typename = self.get_hash_typename()
        hash_offset = self.db.gctransformer.get_hash_offset(self.T)
        yield '%s {' % cdecl(hash_typename, '')
        yield '\tunion {'
        yield '\t\t%s;' % cdecl(self.implementationtypename, 'head')
        yield '\t\tchar pad[%s];' % name_signed(hash_offset, self.db)
        yield '\t} u;'
        yield '\tlong hash;'
        yield '};'
        yield '%s;' % (
            forward_cdecl(hash_typename, '_hash_' + self.name,
                          self.db.standalone, self.is_thread_local()),)
        yield '#define %s _hash_%s.u.head' % (self.name, self.name)

    def implementation(self):
        hash_typename = self.get_hash_typename()
        hash = self.db.gcpolicy.get_prebuilt_hash(self.obj)
        assert hash is not None
        lines = list(self.initializationexpr())
        lines.insert(0, '%s = { {' % (
            cdecl(hash_typename, '_hash_' + self.name,
                  self.is_thread_local()),))
        lines.append('}, %s /* hash */ };' % name_signed(hash, self.db))
        return lines

def gcstructnode_factory(db, T, obj):
    if db.gcpolicy.get_prebuilt_hash(obj) is not None:
        cls = GcStructNodeWithHash
    else:
        cls = StructNode
    return cls(db, T, obj)


class ArrayNode(ContainerNode):
    nodekind = 'array'
    if USESLOTS:
        __slots__ = ()

    def __init__(self, db, T, obj):
        ContainerNode.__init__(self, db, T, obj)
        if barebonearray(T):
            self.ptrname = self.name

    def basename(self):
        return 'array'

    def enum_dependencies(self):
        return self.obj.items

    def getlength(self):
        return len(self.obj.items)

    def initializationexpr(self, decoration=''):
        defnode = self.db.gettypedefnode(self.T)
        yield '{'
        if needs_gcheader(self.T):
            for i, thing in enumerate(self.db.gcpolicy.array_gcheader_initdata(self)):
                lines = generic_initializationexpr(self.db, thing,
                                                   'gcheader%d'%i,
                                                   '%sgcheader%d' % (decoration, i))
                for line in lines:
                    yield line
        if self.T._hints.get('nolength', False):
            length = ''
        else:
            length = '%d, ' % len(self.obj.items)
        if self.T.OF is Void or len(self.obj.items) == 0:
            yield '\t%s' % length.rstrip(', ')
            yield '}'
        elif self.T.OF == Char:
            if len(self.obj.items) and self.obj.items[0] is None:
                s = ''.join([self.obj.getitem(i) for i in range(len(self.obj.items))])
            else:
                s = ''.join(self.obj.items)
            yield '\t%s%s' % (length, c_char_array_constant(s))
            yield '}'
        else:
            barebone = barebonearray(self.T)
            if not barebone:
                yield '\t%s{' % length
            for j in range(len(self.obj.items)):
                value = self.obj.items[j]
                lines = generic_initializationexpr(self.db, value,
                                                '%s.items[%d]' % (self.name, j),
                                                '%s%d' % (decoration, j))
                for line in lines:
                    yield '\t' + line
            if not barebone:
                yield '} }'
            else:
                yield '}'

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
        callable = getattr(obj, '_callable', None)
        if (callable is not None and
            getattr(callable, 'c_name', None) is not None):
            self.name = forcename or obj._callable.c_name
        elif getattr(obj, 'external', None) == 'C' and not db.need_sandboxing(obj):
            self.name = forcename or self.basename()
        else:
            self.name = (forcename or
                         db.namespace.uniquename('g_' + self.basename()))
        self.compilation_info = getattr(obj, 'compilation_info', None)
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

    def graphs_to_patch(self):
        for funcgen in self.funcgens:
            for i in funcgen.graphs_to_patch():
                yield i

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

def sandbox_stub(fnobj, db):
    # unexpected external function for --sandbox translation: replace it
    # with a "Not Implemented" stub.  To support these functions, port them
    # to the new style registry (e.g. rpython.module.ll_os.RegisterOs).
    from pypy.translator.sandbox import rsandbox
    graph = rsandbox.get_external_function_sandbox_graph(fnobj, db,
                                                      force_stub=True)
    return [FunctionCodeGenerator(graph, db)]

def sandbox_transform(fnobj, db):
    # for --sandbox: replace a function like os_open_llimpl() with
    # code that communicates with the external process to ask it to
    # perform the operation.
    from pypy.translator.sandbox import rsandbox
    graph = rsandbox.get_external_function_sandbox_graph(fnobj, db)
    return [FunctionCodeGenerator(graph, db)]

def select_function_code_generators(fnobj, db, functionname):
    # XXX this logic is completely broken nowadays
    #     _external_name does not mean that this is done oldstyle
    sandbox = db.need_sandboxing(fnobj)
    if hasattr(fnobj, '_external_name'):
        if sandbox:
            return sandbox_stub(fnobj, db)
        db.externalfuncs[fnobj._external_name] = fnobj
        return []
    elif fnobj._callable in extfunc.EXTERNALS:
        # -- deprecated case --
        # 'fnobj' is one of the ll_xyz() functions with the suggested_primitive
        # flag in pypy.rpython.module.*.  The corresponding C wrappers are
        # written by hand in src/ll_*.h, and declared in extfunc.EXTERNALS.
        if sandbox and not fnobj._name.startswith('ll_stack_'): # XXX!!! Temporary
            return sandbox_stub(fnobj, db)
        db.externalfuncs[fnobj._callable] = fnobj
        return []
    elif hasattr(fnobj, 'graph'):
        if sandbox and sandbox != "if_external":
            # apply the sandbox transformation
            return sandbox_transform(fnobj, db)
        exception_policy = getattr(fnobj, 'exception_policy', None)
        return [FunctionCodeGenerator(fnobj.graph, db, exception_policy,
                                      functionname)]
    elif getattr(fnobj, 'external', None) is not None:
        if sandbox:
            return sandbox_stub(fnobj, db)
        elif fnobj.external == 'C':
            return []
        else:
            assert fnobj.external == 'CPython'
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
    if T.hints.get("render_structure", False):
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
        value = obj.value
        self.name = self._python_c_name(value)
        self.ptrname = self.name
        self.exported_name = self.name
        # a list of expressions giving places where this constant PyObject
        # must be copied.  Normally just in the global variable of the same
        # name, but see also StructNode.initializationexpr()  :-(
        self.where_to_copy_me = []

    def _python_c_name(self, value):
        # just some minimal cases: None and builtin exceptions
        if value is None:
            return 'Py_None'
        import types, py
        if isinstance(value, (type, types.ClassType)):
            if (issubclass(value, BaseException) and
                (value.__module__ == 'exceptions'
                 or value is py.code._AssertionError)):
                return 'PyExc_' + value.__name__
        raise Exception("don't know how to simply render py object: %r" %
                        (value, ))
    
    def forward_declaration(self):
        return []

    def enum_dependencies(self):
        return []

    def implementation(self):
        return []

def weakrefnode_factory(db, T, obj):
    assert isinstance(obj, llmemory._wref)
    ptarget = obj._dereference()
    wrapper = db.gcpolicy.convert_weakref_to(ptarget)
    container = wrapper._obj
    #obj._converted_weakref = container     # hack for genllvm :-/
    return db.getcontainernode(container, _dont_write_c_code=False)

class GroupNode(ContainerNode):
    nodekind = 'group'
    count_members = None

    def __init__(self, *args):
        ContainerNode.__init__(self, *args)
        self.implementationtypename = 'struct group_%s_s @' % self.name

    def basename(self):
        return self.obj.name

    def enum_dependencies(self):
        # note: for the group used by the GC, it can grow during this phase,
        # which means that we might not return all members yet.  This is fixed
        # by get_finish_tables() in rpython.memory.gctransform.framework.
        for member in self.obj.members:
            yield member._as_ptr()

    def _fix_members(self):
        if self.obj.outdated:
            raise Exception(self.obj.outdated)
        if self.count_members is None:
            self.count_members = len(self.obj.members)
        else:
            # make sure no new member showed up, because it's too late
            assert len(self.obj.members) == self.count_members

    def forward_declaration(self):
        self._fix_members()
        yield ''
        ctype = ['%s {' % cdecl(self.implementationtypename, '')]
        for i, member in enumerate(self.obj.members):
            structtypename = self.db.gettype(typeOf(member))
            ctype.append('\t%s;' % cdecl(structtypename, 'member%d' % i))
        ctype.append('} @')
        ctype = '\n'.join(ctype)
        yield '%s;' % (
            forward_cdecl(ctype, self.name, self.db.standalone,
                          self.is_thread_local()))
        yield '#include "src/llgroup.h"'
        yield 'PYPY_GROUP_CHECK_SIZE(%s);' % self.name
        for i, member in enumerate(self.obj.members):
            structnode = self.db.getcontainernode(member)
            yield '#define %s %s.member%d' % (structnode.name,
                                              self.name, i)
        yield ''

    def initializationexpr(self):
        self._fix_members()
        lines = ['{']
        lasti = len(self.obj.members) - 1
        for i, member in enumerate(self.obj.members):
            structnode = self.db.getcontainernode(member)
            lines1 = list(structnode.initializationexpr())
            lines1[0] += '\t/* member%d: %s */' % (i, structnode.name)
            if i != lasti:
                lines1[-1] += ','
            lines.extend(lines1)
        lines.append('}')
        return lines


ContainerNodeFactory = {
    Struct:       StructNode,
    GcStruct:     gcstructnode_factory,
    Array:        ArrayNode,
    GcArray:      ArrayNode,
    FixedSizeArray: FixedSizeArrayNode,
    FuncType:     FuncNode,
    OpaqueType:   opaquenode_factory,
    PyObjectType: PyObjectNode,
    llmemory._WeakRefType: weakrefnode_factory,
    llgroup.GroupType: GroupNode,
    }
