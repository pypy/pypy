from pypy.rpython.rmodel import inputconst
from pypy.rpython.rclass import AbstractClassRepr, AbstractInstanceRepr, \
                                getclassrepr
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

        self.lowleveltype = ootype.Instance(classdef.cls.__name__, None, {}, {})
        self.prebuiltinstances = {}   # { id(x): (x, _ptr) }

    def _setup_repr(self):
        # FIXME methods
        assert self.classdef.basedef is None

        fields = {}
        attrs = self.classdef.attrs.items()

        for name, attrdef in attrs:
            if not attrdef.readonly:
                oot = self.rtyper.getrepr(attrdef.s_value).lowleveltype
                fields[name] = oot

        ootype.addFields(self.lowleveltype, fields)
            
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
