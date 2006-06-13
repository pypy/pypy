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
        from pypy.rpython.ootypesystem.bltregistry import ExternalType,_external_type
        if value is None:
            return lltype.Void
        return _external_type(self.knowntype)
    
    def rtype_getattr(self, hop):
##        s_attr = hop.args_s[1]
##        if s_attr.is_constant() and isinstance(s_attr.const, str):
##            field = self.knowntype.get_field(s_attr.const)
##            if isinstance(field, annmodel.SomeBuiltin):
##                # we need to type it as static method
##                return hop.args_v[0]
##                #return hop.genop('oogetfield', hop.args_v, concretetype=self.lowleveltype)
##            ll_type = field.rtyper_makerepr(hop.rtyper).lowleveltype
##            return hop.genop('oogetfield', hop.args_v, ll_type)
##        else:
##            raise TyperError("getattr() with a non-constant attribute name")
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
        attr = hop.args_s[1].const
        #self.lowleveltype._check_field(attr)
        vlist = hop.inputargs(self, ootype.Void, hop.args_r[2])
        s_attr = hop.args_s[1]
        return hop.genop('oosetfield', vlist)
##        if s_attr.is_constant() and isinstance(s_attr.const, str):
##            #field = self.knowntype.get_field(s_attr.const)
##            #if isinstance(hop.args_v[2], Constant):
##            #    hop.args_v[2] = hop.inputconst(field.rtyper_makerepr(hop.rtyper), hop.args_v[2].value)
##            return hop.genop('oosetfield', hop.args_v, ootype.Void)
##        else:
##            raise TyperError("setattr() with a non-constant attribute name")
    
    def call_method(self, name, hop):
        #args, retval = self.knowntype._methods[name]
        #ll_args = [i.rtyper_makerepr(hop.rtyper) for i in args]
        #if retval is None:
        #    ll_retval = ootype.Void
        #else:
        #    ll_retval = retval.rtyper_makerepr(hop.rtyper)
        #ar = hop.args_v[:]
        #for i in xrange(1, len(ar)):
        #    if isinstance(ar[i], Constant):
        #        ar[i] = hop.inputconst(ll_args[i-1], ar[i].value)
        #        ar[i].concretetype = ll_args[i-1].lowleveltype
##        args = hop.inputargs(*hop.args_v)
##        import pdb; pdb.set_trace()
        #attr = hop.args_s[1].const
        vlist = hop.inputargs(self, *(hop.args_r[1:]))
        return hop.genop('oosend', [Constant(name)] + vlist, resulttype=hop.r_result)
    
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
