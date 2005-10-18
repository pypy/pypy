import types
from pypy.rpython.rmodel import inputconst
from pypy.rpython.rclass import AbstractClassRepr, AbstractInstanceRepr, \
                                getinstancerepr, getclassrepr, get_type_repr
from pypy.rpython.rpbc import getsignature
from pypy.rpython.ootypesystem import ootype
from pypy.annotation.pairtype import pairtype
from pypy.tool.sourcetools import func_with_new_name

CLASSTYPE = ootype.Class

class ClassRepr(AbstractClassRepr):
    def __init__(self, rtyper, classdef):
        AbstractClassRepr.__init__(self, rtyper, classdef)

        self.lowleveltype = ootype.Class

    def _setup_repr(self):
        pass # not actually needed?

    def convert_const(self, value):
        if not isinstance(value, (type, types.ClassType)):
            raise TyperError("not a class: %r" % (value,))
        try:
            subclassdef = self.rtyper.annotator.getuserclasses()[value]
        except KeyError:
            raise TyperError("no classdef: %r" % (value,))
        if self.classdef is not None:
            if self.classdef.commonbase(subclassdef) != self.classdef:
                raise TyperError("not a subclass of %r: %r" % (
                    self.classdef.cls, value))
        #
        return getinstancerepr(self.rtyper, subclassdef).lowleveltype._class


def mangle(name):
    # XXX temporary: for now it looks like a good idea to mangle names
    # systematically to trap bugs related to a confusion between mangled
    # and non-mangled names
    return 'o' + name

def unmangle(mangled):
    assert mangled.startswith('o')
    return mangled[1:]

class InstanceRepr(AbstractInstanceRepr):
    def __init__(self, rtyper, classdef, does_need_gc=True):
        AbstractInstanceRepr.__init__(self, rtyper, classdef)

        self.baserepr = None
        b = self.classdef.basedef
        if b is not None:
            self.baserepr = getinstancerepr(rtyper, b)
            b = self.baserepr.lowleveltype

        self.lowleveltype = ootype.Instance(classdef.cls.__name__, b, {}, {})
        self.prebuiltinstances = {}   # { id(x): (x, _ptr) }
        self.object_type = self.lowleveltype

    def _setup_repr(self):
        if self.baserepr is not None:
            allfields = self.baserepr.allfields.copy()
            allmethods = self.baserepr.allmethods.copy()
            allclassattributes = self.baserepr.allclassattributes.copy()
        else:
            allfields = {}
            allmethods = {}
            allclassattributes = {}

        fields = {}
        fielddefaults = {}
        attrs = self.classdef.attrs.items()

        for name, attrdef in attrs:
            if not attrdef.readonly:
                mangled = mangle(name)
                repr = self.rtyper.getrepr(attrdef.s_value)
                allfields[mangled] = repr
                oot = repr.lowleveltype
                fields[mangled] = oot
                try:
                    fielddefaults[mangled] = getattr(self.classdef.cls, name)
                except AttributeError:
                    pass

        ootype.addFields(self.lowleveltype, fields)

        methods = {}
        classattributes = {}
        baseInstance = self.lowleveltype._superclass
        classrepr = getclassrepr(self.rtyper, self.classdef)

        for classdef in self.classdef.getmro():
            attrs = classdef.attrs.items()
            for name, attrdef in attrs:
                if not attrdef.readonly:
                    continue
                try:
                    impl = self.classdef.cls.__dict__[name]
                except KeyError:
                    continue
                mangled = mangle(name)
                if classrepr.prepare_method(attrdef.s_value) is not None:
                    # a regular method
                    f, inputs, ret = getsignature(self.rtyper, impl)
                    M = ootype.Meth([r.lowleveltype for r in inputs[1:]], ret.lowleveltype)
                    m = ootype.meth(M, _name=mangled, _callable=impl,
                                    graph=f.graph)
                    methods[mangled] = m
                    allmethods[mangled] = True
                else:
                    # a non-method class attribute
                    allclassattributes[mangled] = True
                    if not attrdef.s_value.is_constant():
                        classattributes[mangled] = attrdef.s_value, impl
        
        ootype.addMethods(self.lowleveltype, methods)
        self.allfields = allfields
        self.allmethods = allmethods
        self.allclassattributes = allclassattributes

        # the following is done after the rest of the initialization because
        # convert_const can require 'self' to be fully initialized.

        # step 2: provide default values for fields
        for mangled, impl in fielddefaults.items():
            oot = fields[mangled]
            r = allfields[mangled]
            oovalue = r.convert_const(impl)
            ootype.addFields(self.lowleveltype, {mangled: (oot, oovalue)})

        # step 3: provide accessor methods for class attributes that are
        # really overridden in subclasses
        for mangled, (s_value, impl) in classattributes.items():
            r = self.rtyper.getrepr(s_value)
            oovalue = r.convert_const(impl)
            m = self.attach_class_attr_accessor(mangled, oovalue,
                                                r.lowleveltype)

    def attach_class_attr_accessor(self, mangled, oovalue, oovaluetype):
        def ll_getclassattr(self):
            return oovalue
        ll_getclassattr = func_with_new_name(ll_getclassattr,
                                             'll_get_' + mangled)
        sm = self.rtyper.annotate_helper(ll_getclassattr, [self.lowleveltype])
        M = ootype.Meth([], oovaluetype)
        m = ootype.meth(M, _name=mangled, _callable=ll_getclassattr,
                        graph=sm.graph)
        ootype.addMethods(self.lowleveltype, {mangled: m})

    def rtype_getattr(self, hop):
        v_inst, _ = hop.inputargs(self, ootype.Void)
        s_inst = hop.args_s[0]
        attr = hop.args_s[1].const
        mangled = mangle(attr)
        v_attr = hop.inputconst(ootype.Void, mangled)
        if mangled in self.allfields:
            # regular instance attributes
            self.lowleveltype._check_field(mangled)
            return hop.genop("oogetfield", [v_inst, v_attr],
                             resulttype = hop.r_result.lowleveltype)
        elif mangled in self.allmethods:
            # special case for methods: represented as their 'self' only
            # (see MethodsPBCRepr)
            return hop.r_result.get_method_from_instance(self, v_inst,
                                                         hop.llops)
        elif mangled in self.allclassattributes:
            # class attributes
            if hop.s_result.is_constant():
                oovalue = hop.r_result.convert_const(hop.s_result.const)
                return hop.inputconst(hop.r_result, oovalue)
            else:
                cname = hop.inputconst(ootype.Void, mangled)
                return hop.genop("oosend", [cname, v_inst],
                                 resulttype = hop.r_result.lowleveltype)
        else:
            raise TyperError("no attribute %r on %r" % (attr, self))

    def rtype_setattr(self, hop):
        attr = hop.args_s[1].const
        mangled = mangle(attr)
        self.lowleveltype._check_field(mangled)
        v_inst, _, v_newval = hop.inputargs(self, ootype.Void, hop.args_r[2])
        v_attr = hop.inputconst(ootype.Void, mangled)
        return hop.genop('oosetfield', [v_inst, v_attr, v_newval])

    def rtype_is_true(self, hop):
        vinst, = hop.inputargs(self)
        return hop.genop('oononnull', [vinst], resulttype=ootype.Bool)

    def convert_const(self, value):
        if value is None:
            return ootype.null(self.lowleveltype)
        try:
            classdef = self.rtyper.annotator.getuserclasses()[value.__class__]
        except KeyError:
            raise TyperError("no classdef: %r" % (value.__class__,))
        if classdef != self.classdef:
            # if the class does not match exactly, check that 'value' is an
            # instance of a subclass and delegate to that InstanceRepr
            if classdef is None:
                raise TyperError("not implemented: object() instance")
            if classdef.commonbase(self.classdef) != self.classdef:
                raise TyperError("not an instance of %r: %r" % (
                    self.classdef.cls, value))
            rinstance = getinstancerepr(self.rtyper, classdef)
            result = rinstance.convert_const(value)
            return ootype.ooupcast(self.lowleveltype, result)
        # common case
        try:
            return self.prebuiltinstances[id(value)][1]
        except KeyError:
            self.setup()
            result = ootype.new(self.object_type)
            self.prebuiltinstances[id(value)] = value, result
            self.initialize_prebuilt_instance(value, result)
            return result

    def new_instance(self, llops):
        """Build a new instance, without calling __init__."""

        return llops.genop("new",
            [inputconst(ootype.Void, self.lowleveltype)], self.lowleveltype)

    def initialize_prebuilt_instance(self, value, result):
        # then add instance attributes from this level
        for mangled, (oot, default) in self.lowleveltype._allfields().items():
            name = unmangle(mangled)
            if oot is ootype.Void:
                llattrvalue = None
            elif name == '_hash_cache_': # hash() support
                llattrvalue = hash(value)
            else:
                try:
                    attrvalue = getattr(value, name)
                except AttributeError:
                    warning("prebuilt instance %r has no attribute %r" % (
                        value, name))
                    continue
                llattrvalue = self.allfields[mangled].convert_const(attrvalue)
            setattr(result, mangled, llattrvalue)


class __extend__(pairtype(InstanceRepr, InstanceRepr)):
    def convert_from_to((r_ins1, r_ins2), v, llops):
        # which is a subclass of which?
        if r_ins1.classdef is None or r_ins2.classdef is None:
            basedef = None
        else:
            basedef = r_ins1.classdef.commonbase(r_ins2.classdef)
        if basedef == r_ins2.classdef:
            # r_ins1 is an instance of the subclass: converting to parent
            v = llops.genop('ooupcast', [v],
                            resulttype = r_ins2.lowleveltype)
            return v
        elif basedef == r_ins1.classdef:
            # r_ins2 is an instance of the subclass: potentially unsafe
            # casting, but we do it anyway (e.g. the annotator produces
            # such casts after a successful isinstance() check)
            v = llops.genop('oodowncast', [v],
                            resulttype = r_ins2.lowleveltype)
            return v
        else:
            return NotImplemented
