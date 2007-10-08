from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype, bltregistry
from pypy.rpython.rmodel import Repr
from pypy.annotation.signature import annotation
from pypy.tool.pairtype import pairtype

    
class ExternalInstanceRepr(Repr):
    def __init__(self, rtyper, knowntype):
        bk = rtyper.annotator.bookkeeper
        self.ext_desc = bk.getexternaldesc(knowntype)
        self.lowleveltype = bltregistry.ExternalType(knowntype)
        self.name = "<class '%s'>" % self.ext_desc._class_.__name__
    
    def convert_const(self, value):
        return bltregistry._external_inst(self.lowleveltype, value)
    
    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        s_inst = hop.args_s[0]
        if self.ext_desc._methods.has_key(attr):
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
        obj = self.ext_desc._class_._fields[field_name]
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
        for s_arg in self.ext_desc._fields[name].analyser.s_args:
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


class __extend__(pairtype(ExternalInstanceRepr, ExternalInstanceRepr)):
    def convert_from_to((from_, to), v, llops):
        type_from = from_.ext_desc._class_
        type_to = to.ext_desc._class_
        if issubclass(type_from, type_to): 
            # XXX ?
            v.concretetype=to.lowleveltype
            return v
        return NotImplemented
