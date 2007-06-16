from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rmodel import Repr, HalfConcreteWrapper
from pypy.rpython.extfunctable import typetable
from pypy.rpython import rbuiltin
from pypy.rpython.module.support import init_opaque_object
from pypy.objspace.flow.model import Constant, Variable
from pypy.rpython import extregistry
from pypy.annotation.signature import annotation
from pypy.annotation.pairtype import pairtype

# ExternalObjects

class __extend__(annmodel.SomeExternalObject):

    def rtyper_makerepr(self, rtyper):
        if self.knowntype in typetable:
            return ExternalObjRepr(self.knowntype)
        else:
            # delegate to the get_repr() of the extregistrered Entry class
            entry = extregistry.lookup_type(self.knowntype)
            return entry.get_repr(rtyper, self)

    def rtyper_makekey(self):
        # grab all attributes of the SomeExternalObject for the key
        attrs = lltype.frozendict(self.__dict__)
        if 'const' in attrs:
            del attrs['const']
        if 'const_box' in attrs:
            del attrs['const_box']
        return self.__class__, attrs
    
class ExternalObjRepr(Repr):
    """Repr for the (obsolecent) extfunctable.declaretype() case.
    If you use the extregistry instead you get to pick your own Repr.
    """

    def __init__(self, knowntype):
        self.exttypeinfo = typetable[knowntype]
        TYPE = self.exttypeinfo.get_lltype()
        self.lowleveltype = lltype.Ptr(TYPE)
        self.instance_cache = {}
        # The set of methods supported depends on 'knowntype', so we
        # cannot have rtype_method_xxx() methods directly on the
        # ExternalObjRepr class.  But we can store them in 'self' now.
        for name, extfuncinfo in self.exttypeinfo.methods.items():
            methodname = 'rtype_method_' + name
            bltintyper = rbuiltin.make_rtype_extfunc(extfuncinfo)
            setattr(self, methodname, bltintyper)

    def convert_const(self, value):
        T = self.exttypeinfo.get_lltype()
        if value is None:
            return lltype.nullptr(T)
        if not isinstance(value, self.exttypeinfo.typ):
            raise TyperError("expected a %r: %r" % (self.exttypeinfo.typ,
                                                    value))
        key = Constant(value)
        try:
            p = self.instance_cache[key]
        except KeyError:
            p = lltype.malloc(T)
            init_opaque_object(p.obj, value)
            self.instance_cache[key] = p
        return p

    def rtype_is_true(self, hop):
        vlist = hop.inputargs(self)
        return hop.genop('ptr_nonzero', vlist, resulttype=lltype.Bool)

# ExternalBuiltins

class __extend__(annmodel.SomeExternalBuiltin):
    
    def rtyper_makerepr(self, rtyper):
        return ExternalBuiltinRepr(self.knowntype)
    
    def rtyper_makekey(self):
        return self.__class__, self.knowntype
    
class ExternalBuiltinRepr(Repr):
    def __init__(self, knowntype):
        self.knowntype = knowntype
        self.lowleveltype = knowntype
        self.name = "<class '%s'>" % self.knowntype._class_.__name__
    
    def convert_const(self, value):
        from pypy.rpython.ootypesystem.bltregistry import ExternalType,_external_type
        return _external_type(self.knowntype, value)
    
    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        s_inst = hop.args_s[0]
        if self.knowntype._methods.has_key(attr):
            # just return instance - will be handled by simple_call
            return hop.inputarg(hop.args_r[0], arg=0)
        vlist = hop.inputargs(self, ootype.Void)
        return hop.genop("oogetfield", vlist,
                         resulttype = hop.r_result.lowleveltype)

    def rtype_setattr(self, hop):
        if self.lowleveltype is ootype.Void:
            return
        vlist = [hop.inputarg(self, arg=0), hop.inputarg(ootype.Void, arg=1)]
        field_name = hop.args_s[1].const
        obj = self.knowntype._class_._fields[field_name]
        bookkeeper = hop.rtyper.annotator.bookkeeper
        # XXX WARNING XXX
        # annotation() here should not be called, but we somehow
        # have overwritten _fields. This will do no harm, but may hide some
        # errors
        r = hop.rtyper.getrepr(annotation(obj, bookkeeper))
        r.setup()
        v = hop.inputarg(r, arg=2)
        vlist.append(v)
        return hop.genop('oosetfield', vlist)
    
    def call_method(self, name, hop):
        bookkeeper = hop.rtyper.annotator.bookkeeper
        args_r = []
        for s_arg in self.knowntype._fields[name].analyser.s_args:
            r = hop.rtyper.getrepr(s_arg)
            r.setup()
            args_r.append(r)
        vlist = hop.inputargs(self, *args_r)
        c_name = hop.inputconst(ootype.Void, name)
        hop.exception_is_here()
        return hop.genop('oosend', [c_name] + vlist, resulttype=hop.r_result)
    
    def rtype_is_true(self, hop):
        vlist = hop.inputargs(self)
        return hop.genop('is_true', vlist, resulttype=lltype.Bool)
    
    def ll_str(self, val):
        return ootype.oostring(self.name, -1)
    
    def __getattr__(self, attr):
        if attr.startswith("rtype_method_"):
            name = attr[len("rtype_method_"):]
            return lambda hop: self.call_method(name, hop)
        else:
            raise AttributeError(attr)


class __extend__(pairtype(ExternalBuiltinRepr, ExternalBuiltinRepr)):
    def convert_from_to((from_, to), v, llops):
        type_from = from_.knowntype._class_
        type_to = to.knowntype._class_
        if issubclass(type_from, type_to):
            v.concretetype=to.knowntype
            return v
        return NotImplemented
