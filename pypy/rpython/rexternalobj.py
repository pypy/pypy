from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rmodel import Repr
from pypy.rpython.extfunctable import typetable
from pypy.rpython import rbuiltin
from pypy.rpython.module.support import init_opaque_object
from pypy.objspace.flow.model import Constant
from pypy.rpython import extregistry


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

class ExternalBuiltinRepr(Repr):
    def __init__(self, knowntype):
        self.knowntype = knowntype
        self.lowleveltype = knowntype
    
    def convert_const(self, value):
        from pypy.rpython.ootypesystem.bltregistry import ExternalType
        if value is None:
            return lltype.Void
        return ExternalType.get(value)
    
    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            field = self.knowntype.get_field(s_attr.const)
            if isinstance(field, annmodel.SomeBuiltin):
                # we need to type it as static method
                args, retval = self.knowntype._methods[s_attr.const]
                ll_args = [i.rtyper_makerepr(hop.rtyper).lowleveltype for i in args]
                if retval is None:
                    ll_retval = ootype.Void
                else:
                    ll_retval = retval.rtyper_makerepr(hop.rtyper).lowleveltype
                return Constant(hop.args_v[0], concretetype=self.lowleveltype)
                #return Constant(ootype.StaticMethod(ll_args, ll_retval), concretetype=self.lowleveltype)
                #return Constant(ootype.StaticMethod(ll_args, ll_retval), concretetype = lltype.Void)
            return self.knowntype.get_field(s_attr.const).rtyper_makerepr(hop.repr).lowleveltype
        else:
            raise TyperError("getattr() with a non-constant attribute name")
    
    def call_method(self, name, hop):
        return hop.genop('oosend', [Constant(name)] + hop.args_v, resulttype=hop.r_result)
    
    def __getattr__(self, attr):
        if attr.startswith("rtype_method_"):
            name = attr[len("rtype_method_"):]
            return lambda hop: self.call_method(name, hop)
        else:
            raise AttributeError(attr)

class __extend__(annmodel.SomeExternalBuiltin):
    
    def rtyper_makerepr(self, rtyper):
        return ExternalBuiltinRepr(self.knowntype)
    
    def rtyper_makekey(self):
        return self.__class__, self.knowntype
    
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
