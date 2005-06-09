from __future__ import generators
from pypy.translator.genc.basetype import CType
from pypy.translator.gensupp import C_IDENTIFIER
from pypy.objspace.flow.model import SpaceOperation, Constant, Variable
from pypy.rpython import lltype


class CLiteral(CType):   # HACK! TEMPORARY
    def nameof(self, obj, debug=None):
        assert isinstance(obj, str)
        return obj

class CLiteralTypeName(CType):   # HACK! TEMPORARY
    def nameof(self, obj, debug=None):
        assert isinstance(obj, lltype.LowLevelType)
        ct = ll2concretetype(self.translator, obj)
        return ct.typename


class CLLType(CType):

    def __init__(self, translator, lltype):
        super(CLLType, self).__init__(translator)
        self.lltype = lltype
        self.globaldecl = []

    def debugname(self):
        # a nice textual name for debugging...
        return str(self.lltype)

    def collect_globals(self, genc):
        result = self.globaldecl
        self.globaldecl = []
        return result


def needs_refcount(ct):
    return isinstance(ct, CPtrType) and ct.lltype._needsgc()


class CPtrType(CLLType):
    error_return = 'NULL'
    Counter = 0

    def __init__(self, translator, lltype):
        super(CPtrType, self).__init__(translator, lltype)
        ct = ll2concretetype(translator, lltype.TO)
        self.typename = 'ptr%d_%s' % (CPtrType.Counter,
                                      ct.typename.translate(C_IDENTIFIER))
        CPtrType.Counter += 1

    def init_globals(self, genc):
        ct = ll2concretetype(genc.translator, self.lltype.TO)
        yield 'typedef %s* %s;' % (ct.typename, self.typename)
        if self.lltype._needsgc():
            yield '#define OP_INCREF_%s(p) if (p) REFCNT(%s, p)++;' % (
                self.typename, ct.typename)
            yield '#define OP_DECREF_%s(p) if (p && !--REFCNT(%s, p)) %s(p);' %(
                self.typename, ct.typename, ct.destructorname)
        else:
            yield '#define OP_INCREF_%s(p)  /* no ref */' % self.typename
            yield '#define OP_DECREF_%s(p)  /* no ref */' % self.typename

    def spec_getattr(self, typer, op):
        v_ptr, v_attrname = op.args
        assert isinstance(v_attrname, Constant)
        attrname = v_attrname.value
        attrtype = self.lltype.TO._flds[attrname]
        cliteral = typer.annotator.translator.getconcretetype(CLiteral)
        s_result = typer.annotator.binding(op.result)
        ctresult = typer.annotation2concretetype(s_result)
        if isinstance(attrtype, lltype.ContainerType):
            yield typer.typed_op(op, [self, cliteral], ctresult,
                                 newopname='getsubstruct')
        else:
            yield typer.typed_op(op, [self, cliteral], ctresult,
                                 newopname='getfield')
        if needs_refcount(ctresult):
            v = Variable()
            yield typer.typed_op(SpaceOperation('incref', [op.result], v),
                                 [ctresult], typer.TNone)

    def spec_setattr(self, typer, op):
        # XXX refcounting
        v_ptr, v_attrname, v_value = op.args
        assert isinstance(v_attrname, Constant)
        attrname = v_attrname.value
        attrtype = self.lltype.TO._flds[attrname]
        cliteral = typer.annotator.translator.getconcretetype(CLiteral)
        if isinstance(attrtype, lltype.ContainerType):
            raise AssertionError("cannot setattr to a substructure")
        ctinput = ll2concretetype(typer.annotator.translator, attrtype)
        yield typer.typed_op(op, [self, cliteral, ctinput], typer.TNone,
                             newopname='setfield')


class CStructType(CLLType):
    Counter = 0

    def __init__(self, translator, lltype):
        super(CStructType, self).__init__(translator, lltype)
        basename = lltype._name.translate(C_IDENTIFIER)
        self.typename = 'struct ll_%s%d' % (basename, CStructType.Counter)
        self.destructorname = 'lldel_%s%d' % (basename, CStructType.Counter)
        CStructType.Counter += 1

    def init_globals(self, genc):
        # make sure that the field types are defined before we use them
        lines = ['%s {' % self.typename]
        destructorlines = []
        for fieldname in self.lltype._names:
            T = self.lltype._flds[fieldname]
            ct = ll2concretetype(genc.translator, T)
            for line in genc.need_typedecl_now(ct):
                yield line
            lines.append('\t%s %s;' % (ct.typename, fieldname))
            if isinstance(ct, (CStructType, CArrayType)):
                destructorlines.append('\tsubstruct_%s(&p->%s);' % (
                                       ct.destructorname, fieldname))
            elif needs_refcount(ct):
                destructorlines.append('\tOP_DECREF_%s((p->%s))' % (
                    ct.typename, fieldname))
        lines.append('};')
        for line in lines:
            yield line
        # declare the wrapper structure used by gc pointers
        yield '%s_gc { int refcount; %s data; };' % (
            self.typename, self.typename)
        # declare the destructor function
        yield 'static void substruct_%s(%s *p);' % (
            self.destructorname, self.typename)
        yield 'static void %s(%s *p);' % (self.destructorname, self.typename)
        def gen():
            yield 'static void substruct_%s(%s *p) {' % (
                self.destructorname, self.typename)
            for line in destructorlines:
                yield line
            yield '}'
            yield 'static void %s(%s *p) {' % (
                self.destructorname, self.typename)
            yield '\tsubstruct_%s(p);' % self.destructorname
            yield '\tSTRUCTFREE(%s, p)' % self.typename
            yield '}'
        self.globaldecl += list(gen())


class CArrayType(CLLType):
    Counter = 0

    def __init__(self, translator, lltype):
        super(CArrayType, self).__init__(translator, lltype)
        self.typename = 'struct array%d' % CArrayType.Counter
        self.destructorname = 'lldelarray%d' % CArrayType.Counter
        CArrayType.Counter += 1

    def init_globals(self, genc):
        # define first the struct containing one item of this array
        ct = ll2concretetype(genc.translator, self.lltype.OF)
        for line in genc.need_typedecl_now(ct):
            yield line
        # the array struct itself
        yield '%s {' % self.typename
        yield '\tlong size;'
        yield '\t%s items[1];  /* variable-sized */' % ct.typename
        yield '};'
        # declare the wrapper structure used by gc pointers
        yield '%s_gc { int refcount; %s data; };' % (
            self.typename, self.typename)
        # declare the destructor function
        yield 'static void substruct_%s(%s *p);' % (
            self.destructorname, self.typename)
        yield 'static void %s(%s *p);' % (self.destructorname, self.typename)
        def gen():
            yield 'static void substruct_%s(%s *p) {' % (
                self.destructorname, self.typename)
            yield '\tint i = p->size;'
            yield '\twhile (i--) {'
            yield '\t\tsubstruct_%s(p->items+i);' % ct.destructorname
            yield '\t}'
            yield 'static void %s(%s *p) {' % (
                self.destructorname, self.typename)
            yield '\tsubstruct_%s(p);' % self.destructorname
            yield '\tSTRUCTFREE(%s, p)' % self.typename
            yield '}'
        self.globaldecl += list(gen())


# ____________________________________________________________

from pypy.translator.genc import inttype, nonetype

primitivetypemap = {
    lltype.Signed: inttype.CIntType,
    lltype.Unsigned: inttype.CUnsignedType,
    #lltype.Char: ...
    lltype.Bool: inttype.CIntType,
    lltype.Void: nonetype.CNoneType,
    }

def get_primitive_type(translator, lltype):
    cls = primitivetypemap[lltype]
    return translator.getconcretetype(cls)

ll2concretetypemap = {
    lltype.Struct: CStructType,
    lltype.GcStruct: CStructType,
    lltype.Array: CArrayType,
    lltype.GcArray: CArrayType,
    lltype.Ptr: CPtrType,
    lltype.Primitive: get_primitive_type,
    }

def ll2concretetype(translator, lltype):
    cls = ll2concretetypemap[lltype.__class__]
    return translator.getconcretetype(cls, lltype)
