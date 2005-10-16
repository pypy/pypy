from pypy.rpython.rmodel import inputconst
from pypy.rpython.rclass import AbstractClassRepr, AbstractInstanceRepr, \
                                getinstancerepr
from pypy.rpython.rpbc import getsignature
from pypy.rpython.ootypesystem import ootype

CLASSTYPE = ootype.Class

class ClassRepr(AbstractClassRepr):
    def __init__(self, rtyper, classdef):
        AbstractClassRepr.__init__(self, rtyper, classdef)

        self.lowleveltype = ootype.Class

    def _setup_repr(self):
        pass # not actually needed?

    def convert_const(self):
        # FIXME
        pass

class InstanceRepr(AbstractInstanceRepr):
    def __init__(self, rtyper, classdef, does_need_gc=True):
        AbstractInstanceRepr.__init__(self, rtyper, classdef)

        b = self.classdef.basedef
        if b is not None:
            b = getinstancerepr(rtyper, b).lowleveltype

        self.lowleveltype = ootype.Instance(classdef.cls.__name__, b, {}, {})
        self.prebuiltinstances = {}   # { id(x): (x, _ptr) }
        self.allmethods = {}

    def _setup_repr(self):
        # FIXME methods

        fields = {}
        attrs = self.classdef.attrs.items()

        for name, attrdef in attrs:
            if not attrdef.readonly:
                oot = self.rtyper.getrepr(attrdef.s_value).lowleveltype
                fields[name] = oot

        ootype.addFields(self.lowleveltype, fields)

        methods = {}
        baseInstance = self.lowleveltype._superclass

        for name, attrdef in attrs:
            if attrdef.readonly:
                assert len(attrdef.s_value.prebuiltinstances) == 1, 'no support for overridden methods yet'
                # XXX following might not always succeed
                impl = self.classdef.cls.__dict__[name]

                f, inputs, ret = getsignature(self.rtyper, impl)
                M = ootype.Meth([r.lowleveltype for r in inputs[1:]], ret.lowleveltype)
                m = ootype.meth(M, _name=name, _callable=impl)
                
                methods[name] = m

        ootype.addMethods(self.lowleveltype, methods)
            
    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        s_inst = hop.args_s[0]
        meth = self.lowleveltype._lookup(attr)
        if meth is not None:
            # just return instance - will be handled by simple_call
            return hop.inputarg(hop.r_result, arg=0)
        self.lowleveltype._check_field(attr)
        vlist = hop.inputargs(self, ootype.Void)
        return hop.genop("oogetfield", vlist,
                         resulttype = hop.r_result.lowleveltype)

    def rtype_setattr(self, hop):
        attr = hop.args_s[1].const
        self.lowleveltype._check_field(attr)
        vlist = hop.inputargs(self, ootype.Void, hop.args_r[2])
        return hop.genop('oosetfield', vlist)

    def convert_const(self):
        # FIXME
        pass

    def new_instance(self, llops):
        """Build a new instance, without calling __init__."""

        return llops.genop("new",
            [inputconst(ootype.Void, self.lowleveltype)], self.lowleveltype)
