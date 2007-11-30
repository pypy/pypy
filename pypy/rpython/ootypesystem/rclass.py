import types
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.objspace.flow import model as flowmodel
from pypy.rpython.rmodel import inputconst, TyperError, warning
from pypy.rpython.rmodel import mangle as pbcmangle
from pypy.rpython.rclass import AbstractClassRepr, AbstractInstanceRepr, \
                                getinstancerepr, getclassrepr, get_type_repr
from pypy.rpython.ootypesystem import ootype
from pypy.tool.pairtype import pairtype
from pypy.tool.sourcetools import func_with_new_name

CLASSTYPE = ootype.Instance("Object_meta", ootype.ROOT,
        fields={"class_": ootype.Class})
OBJECT = ootype.Instance("Object", ootype.ROOT,
        fields={'meta': CLASSTYPE})


class ClassRepr(AbstractClassRepr):
    def __init__(self, rtyper, classdef):
        AbstractClassRepr.__init__(self, rtyper, classdef)

        if self.classdef is not None:
            self.rbase = getclassrepr(self.rtyper, self.classdef.basedef)
            base_type = self.rbase.lowleveltype
            self.lowleveltype = ootype.Instance(
                    self.classdef.name + "_meta", base_type)
        else:
            # we are ROOT
            self.lowleveltype = CLASSTYPE

    def _setup_repr(self):
        clsfields = {}
        pbcfields = {}
        if self.classdef is not None:
            # class attributes
            llfields = []
            """
            attrs = self.classdef.attrs.items()
            attrs.sort()
            for name, attrdef in attrs:
                if attrdef.readonly:
                    s_value = attrdef.s_value
                    s_unboundmethod = self.prepare_method(s_value)
                    if s_unboundmethod is not None:
                        allmethods[name] = True
                        s_value = s_unboundmethod
                    r = self.rtyper.getrepr(s_value)
                    mangled_name = 'cls_' + name
                    clsfields[name] = mangled_name, r
                    llfields.append((mangled_name, r.lowleveltype))
            """
            # attributes showing up in getattrs done on the class as a PBC
            extra_access_sets = self.rtyper.class_pbc_attributes.get(
                self.classdef, {})
            for access_set, (attr, counter) in extra_access_sets.items():
                r = self.rtyper.getrepr(access_set.s_value)
                mangled_name = pbcmangle('pbc%d' % counter, attr)
                pbcfields[access_set, attr] = mangled_name, r
                llfields.append((mangled_name, r.lowleveltype))
            
            self.rbase.setup()
            ootype.addFields(self.lowleveltype, dict(llfields))
        #self.clsfields = clsfields
        self.pbcfields = pbcfields
        self.meta_instance = None
 
    def get_meta_instance(self, cast_to_root_meta=True):
        if self.meta_instance is None:
            self.meta_instance = ootype.new(self.lowleveltype) 
            self.setup_meta_instance(self.meta_instance, self)
        
        meta_instance = self.meta_instance
        if cast_to_root_meta:
            meta_instance = ootype.ooupcast(CLASSTYPE, meta_instance)
        return meta_instance

    def setup_meta_instance(self, meta_instance, rsubcls):
        if self.classdef is None:
            rinstance = getinstancerepr(self.rtyper, rsubcls.classdef)
            setattr(meta_instance, 'class_', rinstance.lowleveltype._class)
        else:
            # setup class attributes: for each attribute name at the level
            # of 'self', look up its value in the subclass rsubcls
            def assign(mangled_name, value):
                if isinstance(value, flowmodel.Constant) and isinstance(value.value, staticmethod):
                    value = flowmodel.Constant(value.value.__get__(42))   # staticmethod => bare function
                llvalue = r.convert_desc_or_const(value)
                setattr(meta_instance, mangled_name, llvalue)

            #mro = list(rsubcls.classdef.getmro())
            #for fldname in self.clsfields:
            #    mangled_name, r = self.clsfields[fldname]
            #    if r.lowleveltype is Void:
            #        continue
            #    value = rsubcls.classdef.classdesc.read_attribute(fldname, None)
            #    if value is not None:
            #        assign(mangled_name, value)
            # extra PBC attributes
            for (access_set, attr), (mangled_name, r) in self.pbcfields.items():
                if rsubcls.classdef.classdesc not in access_set.descs:
                    continue   # only for the classes in the same pbc access set
                if r.lowleveltype is ootype.Void:
                    continue
                attrvalue = rsubcls.classdef.classdesc.read_attribute(attr, None)
                if attrvalue is not None:
                    assign(mangled_name, attrvalue)

            # then initialize the 'super' portion of the vtable
            meta_instance_super = ootype.ooupcast(
                    self.rbase.lowleveltype, meta_instance)
            self.rbase.setup_meta_instance(meta_instance_super, rsubcls)

    getruntime = get_meta_instance
    
    def fromclasstype(self, vclass, llops):
        return llops.genop('oodowncast', [vclass],
                resulttype=self.lowleveltype)

    def getpbcfield(self, vcls, access_set, attr, llops):
        if (access_set, attr) not in self.pbcfields:
            raise TyperError("internal error: missing PBC field")
        mangled_name, r = self.pbcfields[access_set, attr]
        v_meta = self.fromclasstype(vcls, llops)
        cname = inputconst(ootype.Void, mangled_name)
        return llops.genop('oogetfield', [v_meta, cname], resulttype=r)

    def rtype_issubtype(self, hop):
        class_repr = get_type_repr(self.rtyper)
        vmeta1, vmeta2 = hop.inputargs(class_repr, class_repr)
        return hop.gendirectcall(ll_issubclass, vmeta1, vmeta2)

def ll_issubclass(meta1, meta2):
    class1 = meta1.class_
    class2 = meta2.class_
    return ootype.subclassof(class1, class2)

# ____________________________________________________________

def mangle(name, config):
    # XXX temporary: for now it looks like a good idea to mangle names
    # systematically to trap bugs related to a confusion between mangled
    # and non-mangled names
    if config.translation.ootype.mangle:
        return 'o' + name
    else:
        not_allowed = ('_hash_cache_', 'meta', 'class_')
        assert name not in not_allowed, "%s is a reserved name" % name
        return name

def unmangle(mangled, config):
    if config.translation.ootype.mangle:
        assert mangled.startswith('o')
        return mangled[1:]
    else:
        return mangled

class InstanceRepr(AbstractInstanceRepr):
    def __init__(self, rtyper, classdef, gcflavor='ignored'):
        AbstractInstanceRepr.__init__(self, rtyper, classdef)

        self.baserepr = None
        if self.classdef is None:
            self.lowleveltype = OBJECT
        else:
            b = self.classdef.basedef
            if b is not None:
                self.baserepr = getinstancerepr(rtyper, b)
                b = self.baserepr.lowleveltype
            else:
                b = OBJECT

            if hasattr(classdef.classdesc.pyobj, '_rpython_hints'):
                hints = classdef.classdesc.pyobj._rpython_hints
            else:
                hints = {}
            self.lowleveltype = ootype.Instance(classdef.name, b, {}, {}, _hints = hints)
        self.prebuiltinstances = {}   # { id(x): (x, _ptr) }
        self.object_type = self.lowleveltype
        self.gcflavor = gcflavor

    def _setup_repr(self):
        if self.classdef is None:
            self.allfields = {}
            self.allmethods = {}
            self.allclassattributes = {}
            self.classattributes = {}
            return

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
        
        selfattrs = self.classdef.attrs

        for name, attrdef in selfattrs.iteritems():
            mangled = mangle(name, self.rtyper.getconfig())
            if not attrdef.readonly:
                repr = self.rtyper.getrepr(attrdef.s_value)
                allfields[mangled] = repr
                oot = repr.lowleveltype
                fields[mangled] = oot
                try:
                    value = self.classdef.classdesc.read_attribute(name)
                    fielddefaults[mangled] = repr.convert_desc_or_const(value)
                except AttributeError:
                    pass
            else:
                s_value = attrdef.s_value
                if isinstance(s_value, annmodel.SomePBC):
                    if len(s_value.descriptions) > 0 and s_value.getKind() == description.MethodDesc:
                        # attrdef is for a method
                        if mangled in allclassattributes:
                            raise TyperError("method overrides class attribute")
                        allmethods[mangled] = name, self.classdef.lookup_filter(s_value)
                        continue
                # class attribute
                if mangled in allmethods:
                    raise TyperError("class attribute overrides method")
                allclassattributes[mangled] = name, s_value

        special_methods = ["__init__", "__del__"]
        for meth_name in special_methods:
            if meth_name not in selfattrs and \
                    self.classdef.classdesc.find_source_for(meth_name) is not None:
                s_meth = self.classdef.classdesc.s_get_value(self.classdef,
                        meth_name)
                if isinstance(s_meth, annmodel.SomePBC):
                    mangled = mangle(meth_name, self.rtyper.getconfig())
                    allmethods[mangled] = meth_name, s_meth
                # else: it's the __init__ of a builtin exception
            
        #
        # hash() support
        if self.rtyper.needs_hash_support(self.classdef):
            from pypy.rpython import rint
            allfields['_hash_cache_'] = rint.signed_repr
            fields['_hash_cache_'] = ootype.Signed

        ootype.addFields(self.lowleveltype, fields)

        self.rbase = getinstancerepr(self.rtyper, self.classdef.basedef)
        self.rbase.setup()

        methods = {}
        classattributes = {}
        baseInstance = self.lowleveltype._superclass
        classrepr = getclassrepr(self.rtyper, self.classdef)

        for mangled, (name, s_value) in allmethods.iteritems():
            methdescs = s_value.descriptions
            origin = dict([(methdesc.originclassdef, methdesc) for
                           methdesc in methdescs])
            if self.classdef in origin:
                methdesc = origin[self.classdef]
            else:
                if name in selfattrs:
                    for superdef in self.classdef.getmro():
                        if superdef in origin:
                            # put in methods
                            methdesc = origin[superdef]
                            break
                    else:
                        # abstract method
                        methdesc = None
                else:
                    continue

            # get method implementation
            from pypy.rpython.ootypesystem.rpbc import MethodImplementations
            methimpls = MethodImplementations.get(self.rtyper, s_value)
            m_impls = methimpls.get_impl(mangled, methdesc,
                    is_finalizer=name == "__del__")
            
            methods.update(m_impls)
                                        

        for classdef in self.classdef.getmro():
            for name, attrdef in classdef.attrs.iteritems():
                if not attrdef.readonly:
                    continue
                mangled = mangle(name, self.rtyper.getconfig())
                if mangled in allclassattributes:
                    selfdesc = self.classdef.classdesc
                    if name not in selfattrs:
                        # if the attr was already found in a parent class,
                        # we register it again only if it is overridden.
                        if selfdesc.find_source_for(name) is None:
                            continue
                        value = selfdesc.read_attribute(name)
                    else:
                        # otherwise, for new attrs, we look in all parent
                        # classes to see if it's defined in a parent but only
                        # actually first used in self.classdef.
                        value = selfdesc.read_attribute(name, None)

                    # a non-method class attribute
                    if not attrdef.s_value.is_constant():
                        classattributes[mangled] = attrdef.s_value, value

        ootype.addMethods(self.lowleveltype, methods)
        
        self.allfields = allfields
        self.allmethods = allmethods
        self.allclassattributes = allclassattributes
        self.classattributes = classattributes

        # the following is done after the rest of the initialization because
        # convert_const can require 'self' to be fully initialized.

        # step 2: provide default values for fields
        for mangled, impl in fielddefaults.items():
            oot = fields[mangled]
            ootype.addFields(self.lowleveltype, {mangled: (oot, impl)})

    def _setup_repr_final(self):
        # step 3: provide accessor methods for class attributes that
        # are really overridden in subclasses. Must be done here
        # instead of _setup_repr to avoid recursion problems if class
        # attributes are Instances of self.lowleveltype.
        
        for mangled, (s_value, value) in self.classattributes.items():
            r = self.rtyper.getrepr(s_value)
            m = self.attach_class_attr_accessor(mangled, value, r)

        # step 4: do the same with instance fields whose default
        # values are overridden in subclasses. Not sure it's the best
        # way to do it.
        overridden_defaults = {}

        if self.classdef is not None:
            for name, constant in self.classdef.classdesc.classdict.iteritems():
                # look for the attrdef in the superclasses
                classdef = self.classdef.basedef
                attrdef = None
                while classdef is not None:
                    if name in classdef.attrs:
                        attrdef = classdef.attrs[name]
                        break
                    classdef = classdef.basedef
                if attrdef is not None and not attrdef.readonly:
                    # it means that the default value for this field
                    # is overridden in this subclass. Record we know
                    # about it
                    repr = self.rtyper.getrepr(attrdef.s_value)
                    oot = repr.lowleveltype
                    mangled = mangle(name, self.rtyper.getconfig())
                    value = self.classdef.classdesc.read_attribute(name)
                    default = repr.convert_desc_or_const(value)
                    overridden_defaults[mangled] = oot, default

        ootype.overrideDefaultForFields(self.lowleveltype, overridden_defaults)

    def attach_class_attr_accessor(self, mangled, value, r_value):
        def ll_getclassattr(self):
            return oovalue

        M = ootype.Meth([], r_value.lowleveltype)
        if value is None:
            m = ootype.meth(M, _name=mangled, abstract=True)
        else:
            oovalue = r_value.convert_desc_or_const(value)
            ll_getclassattr = func_with_new_name(ll_getclassattr,
                                                 'll_get_' + mangled)
            graph = self.rtyper.annotate_helper(ll_getclassattr, [self.lowleveltype])
            m = ootype.meth(M, _name=mangled, _callable=ll_getclassattr,
                            graph=graph)

        ootype.addMethods(self.lowleveltype, {mangled: m})

    def get_ll_hash_function(self):
        return ll_inst_hash

    def rtype_getattr(self, hop):
        v_inst, _ = hop.inputargs(self, ootype.Void)
        s_inst = hop.args_s[0]
        attr = hop.args_s[1].const
        mangled = mangle(attr, self.rtyper.getconfig())
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
                return hop.inputconst(hop.r_result, hop.s_result.const)
            else:
                cname = hop.inputconst(ootype.Void, mangled)
                return hop.genop("oosend", [cname, v_inst],
                                 resulttype = hop.r_result.lowleveltype)
        elif attr == '__class__':
            if hop.r_result.lowleveltype is ootype.Void:
                # special case for when the result of '.__class__' is constant
                [desc] = hop.s_result.descriptions
                return hop.inputconst(ootype.Void, desc.pyobj)
            else:
                cmeta = inputconst(ootype.Void, "meta")
                return hop.genop('oogetfield', [v_inst, cmeta],
                                 resulttype=CLASSTYPE)
        else:
            raise TyperError("no attribute %r on %r" % (attr, self))

    def rtype_setattr(self, hop):
        attr = hop.args_s[1].const
        mangled = mangle(attr, self.rtyper.getconfig())
        self.lowleveltype._check_field(mangled)
        r_value = self.allfields[mangled]
        v_inst, _, v_newval = hop.inputargs(self, ootype.Void, r_value)
        v_attr = hop.inputconst(ootype.Void, mangled)
        return hop.genop('oosetfield', [v_inst, v_attr, v_newval])

    def setfield(self, vinst, attr, vvalue, llops):
        # this method emulates behaviour from the corresponding
        # lltypesystem one. It is referenced in some obscure corners
        # like rtyping of OSError.
        mangled_name = mangle(attr, self.rtyper.getconfig())
        cname = inputconst(ootype.Void, mangled_name)
        llops.genop('oosetfield', [vinst, cname, vvalue])

    def rtype_is_true(self, hop):
        vinst, = hop.inputargs(self)
        return hop.genop('oononnull', [vinst], resulttype=ootype.Bool)

    def ll_str(self, instance):
        return ootype.oostring(instance, -1)

    def rtype_type(self, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)
        vinst, = hop.inputargs(self)
        if hop.args_s[0].can_be_none():
            return hop.gendirectcall(ll_inst_type, vinst)
        else:
            cmeta = inputconst(ootype.Void, "meta")
            return hop.genop('oogetfield', [vinst, cmeta], resulttype=CLASSTYPE)

    def null_instance(self):
        return ootype.null(self.lowleveltype)

    def upcast(self, result):
        return ootype.ooupcast(self.lowleveltype, result)

    def create_instance(self):
        return ootype.new(self.object_type)

    def new_instance(self, llops, classcallhop=None):
        """Build a new instance, without calling __init__."""
        classrepr = getclassrepr(self.rtyper, self.classdef) 
        v_instance =  llops.genop("new",
            [inputconst(ootype.Void, self.lowleveltype)], self.lowleveltype)
        cmeta = inputconst(ootype.Void, "meta")
        cmeta_instance = inputconst(CLASSTYPE, classrepr.get_meta_instance())
        llops.genop("oosetfield", [v_instance, cmeta, cmeta_instance], 
                  resulttype=ootype.Void)
        return v_instance
        
    def initialize_prebuilt_instance(self, value, classdef, result):
        # then add instance attributes from this level
        classrepr = getclassrepr(self.rtyper, self.classdef)
        for mangled, (oot, default) in self.lowleveltype._allfields().items():
            if oot is ootype.Void:
                llattrvalue = None
            elif mangled == 'meta':
                llattrvalue = classrepr.get_meta_instance()
            elif mangled == '_hash_cache_': # hash() support
                llattrvalue = hash(value)
            else:
                name = unmangle(mangled, self.rtyper.getconfig())
                try:
                    attrvalue = getattr(value, name)
                except AttributeError:
                    attrvalue = self.classdef.classdesc.read_attribute(name, None)
                    if attrvalue is None:
                        warning("prebuilt instance %r has no attribute %r" % (
                                value, name))
                        continue
                    llattrvalue = self.allfields[mangled].convert_desc_or_const(attrvalue)
                else:
                    llattrvalue = self.allfields[mangled].convert_const(attrvalue)
            setattr(result, mangled, llattrvalue)

buildinstancerepr = InstanceRepr


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

    def rtype_is_((r_ins1, r_ins2), hop):
        # NB. this version performs no cast to the common base class
        vlist = hop.inputargs(r_ins1, r_ins2)
        return hop.genop('oois', vlist, resulttype=ootype.Bool)

    rtype_eq = rtype_is_

    def rtype_ne(rpair, hop):
        v = rpair.rtype_eq(hop)
        return hop.genop("bool_not", [v], resulttype=ootype.Bool)


def ll_inst_hash(ins):
    cached = ins._hash_cache_
    if cached == 0:
        cached = ins._hash_cache_ = ootype.ooidentityhash(ins)
    return cached

def ll_inst_type(obj):
    if obj:
        return obj.meta
    else:
        # type(None) -> NULL  (for now)
        return ootype.null(CLASSTYPE)
