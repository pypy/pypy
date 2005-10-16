from pypy.rpython.rmodel import inputconst
from pypy.rpython.rclass import AbstractClassRepr, AbstractInstanceRepr, \
                                getinstancerepr
from pypy.rpython.rpbc import getsignature
from pypy.rpython.ootypesystem import ootype
from pypy.annotation.pairtype import pairtype

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
	    self.allfields = self.baserepr.allfields.copy()
	else:
	    self.allfields = {}
        self.allmethods = {}

        fields = {}
        attrs = self.classdef.attrs.items()

        for name, attrdef in attrs:
            if not attrdef.readonly:
		repr = self.rtyper.getrepr(attrdef.s_value)
		self.allfields[name] = repr
                oot = repr.lowleveltype
                fields[name] = oot

        ootype.addFields(self.lowleveltype, fields)

        methods = {}
        baseInstance = self.lowleveltype._superclass

	for classdef in self.classdef.getmro():
	    attrs = classdef.attrs.items()
	    for name, attrdef in attrs:
		if attrdef.readonly:
		    try:
			impl = self.classdef.cls.__dict__[name]
		    except KeyError:
			pass
		    else:
			f, inputs, ret = getsignature(self.rtyper, impl)
			M = ootype.Meth([r.lowleveltype for r in inputs[1:]], ret.lowleveltype)
			m = ootype.meth(M, _name=name, _callable=impl)
			methods[name] = m
	
        ootype.addMethods(self.lowleveltype, methods)
            
    def rtype_getattr(self, hop):
        vlist = hop.inputargs(self, ootype.Void)
        attr = hop.args_s[1].const
        s_inst = hop.args_s[0]
        meth = self.lowleveltype._lookup(attr)
        if meth is not None:
            # special case for methods: represented as their 'self' only
            # (see MethodsPBCRepr)
            return hop.r_result.get_method_from_instance(self, vlist[0],
                                                         hop.llops)
        self.lowleveltype._check_field(attr)
        return hop.genop("oogetfield", vlist,
                         resulttype = hop.r_result.lowleveltype)

    def rtype_setattr(self, hop):
        attr = hop.args_s[1].const
        self.lowleveltype._check_field(attr)
        vlist = hop.inputargs(self, ootype.Void, hop.args_r[2])
        return hop.genop('oosetfield', vlist)

    def convert_const(self, value):
        if value is None:
            return null(self.lowleveltype)
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
	for name, (oot, default) in self.lowleveltype._allfields().items():
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
		llattrvalue = self.allfields[name].convert_const(attrvalue)
	    setattr(result, name, llattrvalue)


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
