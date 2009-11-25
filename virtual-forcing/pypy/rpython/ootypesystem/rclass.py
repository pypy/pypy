import types
from pypy.annotation import model as annmodel
from pypy.annotation import description
from pypy.objspace.flow import model as flowmodel
from pypy.rpython.rmodel import inputconst, TyperError, warning
from pypy.rpython.rmodel import mangle as pbcmangle
from pypy.rpython.rclass import AbstractClassRepr, AbstractInstanceRepr, \
                                getinstancerepr, getclassrepr, get_type_repr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.exceptiondata import standardexceptions
from pypy.tool.pairtype import pairtype
from pypy.tool.sourcetools import func_with_new_name

OBJECT = ootype.ROOT
META = ootype.Instance("Meta", ootype.ROOT,
                       fields={"class_": ootype.Class})


class ClassRepr(AbstractClassRepr):
    def __init__(self, rtyper, classdef):
        AbstractClassRepr.__init__(self, rtyper, classdef)
        # This is the Repr for a reference to the class 'classdef' or
        # any subclass.  In the simple case, the lowleveltype is just
        # ootype.Class.  If we need to store class attributes, we use a
        # "meta" class where the attributes are defined, and the class
        # reference is a reference to an instance of this meta class.
        extra_access_sets = self.rtyper.class_pbc_attributes.get(
            classdef, {})
        has_class_attributes = bool(extra_access_sets)
        if self.classdef is not None:
            self.rbase = getclassrepr(self.rtyper, self.classdef.basedef)
            meta_base_type = self.rbase.lowleveltype
            baseclass_has_meta = meta_base_type != ootype.Class
        else:
            baseclass_has_meta = False

        if not has_class_attributes and not baseclass_has_meta:
            self.lowleveltype = ootype.Class   # simple case
        else:
            if self.classdef is None:
                raise TyperError("the root 'object' class should not have"
                                 " class attributes")
            if self.classdef.classdesc.pyobj in standardexceptions:
                raise TyperError("Standard exception class %r should not have"
                                 " class attributes" % (self.classdef.name,))
            if not baseclass_has_meta:
                meta_base_type = META
            self.lowleveltype = ootype.Instance(
                    self.classdef.name + "_meta", meta_base_type)

    def _setup_repr(self):
        pbcfields = {}
        if self.lowleveltype != ootype.Class:
            # class attributes
            llfields = []
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
        self.pbcfields = pbcfields
        self.meta_instance = None
 
    def get_meta_instance(self, cast_to_root_meta=True):
        if self.lowleveltype == ootype.Class:
            raise TyperError("no meta-instance for class %r" % 
                             (self.classdef,))
        if self.meta_instance is None:
            self.meta_instance = ootype.new(self.lowleveltype) 
            self.setup_meta_instance(self.meta_instance, self)
        
        meta_instance = self.meta_instance
        if cast_to_root_meta:
            meta_instance = ootype.ooupcast(META, meta_instance)
        return meta_instance

    def setup_meta_instance(self, meta_instance, rsubcls):
        if self.classdef is None:
            rinstance = getinstancerepr(self.rtyper, rsubcls.classdef)
            meta_instance.class_ = ootype.runtimeClass(rinstance.lowleveltype)
        else:
            # setup class attributes: for each attribute name at the level
            # of 'self', look up its value in the subclass rsubcls
            def assign(mangled_name, value):
                if isinstance(value, flowmodel.Constant) and isinstance(value.value, staticmethod):
                    value = flowmodel.Constant(value.value.__get__(42))   # staticmethod => bare function
                llvalue = r.convert_desc_or_const(value)
                setattr(meta_instance, mangled_name, llvalue)

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
            self.rbase.setup_meta_instance(meta_instance, rsubcls)

    def getruntime(self, expected_type):
        if expected_type == ootype.Class:
            rinstance = getinstancerepr(self.rtyper, self.classdef)
            return ootype.runtimeClass(rinstance.lowleveltype)
        else:
            assert ootype.isSubclass(expected_type, META)
            meta = self.get_meta_instance(cast_to_root_meta=False)
            return ootype.ooupcast(expected_type, meta)

    def fromclasstype(self, vclass, llops):
        assert ootype.isSubclass(vclass.concretetype, META)
        if self.lowleveltype == ootype.Class:
            c_class_ = inputconst(ootype.Void, 'class_')
            return llops.genop('oogetfield', [vclass, c_class_],
                    resulttype=ootype.Class)
        else:
            assert ootype.isSubclass(self.lowleveltype, vclass.concretetype)
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
        vcls1, vcls2 = hop.inputargs(class_repr, class_repr)
        return hop.genop('subclassof', [vcls1, vcls2], resulttype=ootype.Bool)

def ll_issubclass(class1, class2):
    # helper for exceptiondata.py
    return ootype.subclassof(class1, class2)

# ____________________________________________________________

def mangle(name, config):
    # XXX temporary: for now it looks like a good idea to mangle names
    # systematically to trap bugs related to a confusion between mangled
    # and non-mangled names
    if config.translation.ootype.mangle:
        return 'o' + name
    else:
        not_allowed = ('meta', 'class_')
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
            hints = self._check_for_immutable_hints(hints)
            self.lowleveltype = ootype.Instance(classdef.name, b, {}, {}, _hints = hints)
        self.prebuiltinstances = {}   # { id(x): (x, _ptr) }
        self.object_type = self.lowleveltype
        self.gcflavor = gcflavor

    def _setup_repr(self, llfields=None, hints=None):
        if hints:
            self.lowleveltype._hints.update(hints)

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

        if llfields:
            fields.update(dict(llfields))
        
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

        ootype.addFields(self.lowleveltype, fields)

        self.rbase = getinstancerepr(self.rtyper, self.classdef.basedef)
        self.rbase.setup()

        classattributes = {}
        baseInstance = self.lowleveltype._superclass
        classrepr = getclassrepr(self.rtyper, self.classdef)

        # if this class has a corresponding metaclass, attach
        # a getmeta() method to get the corresponding meta_instance
        if classrepr.lowleveltype != ootype.Class:
            oovalue = classrepr.get_meta_instance()
            self.attach_class_attr_accessor('getmeta', oovalue)

                                        

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

        self.allfields = allfields
        self.allmethods = allmethods
        self.allclassattributes = allclassattributes
        self.classattributes = classattributes
        # the following is done after the rest of the initialization because
        # convert_const can require 'self' to be fully initialized.

        # step 2: provide default values for fields
        for mangled, impl in fielddefaults.items():
            oot = fields[mangled]
            ootype.addFields(self.lowleveltype, {mangled: (oot, impl)},
                             with_default=True)

    def _setup_repr_final(self):
        if self.classdef is None:
            return
        AbstractInstanceRepr._setup_repr_final(self)
        
        # we attach methods here and not in _setup(), because we want
        # to be sure that all the reprs of the input arguments of all
        # our methods have been computed at this point
        methods = {}
        selfattrs = self.classdef.attrs
        for mangled, (name, s_value) in self.allmethods.iteritems():
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
        ootype.addMethods(self.lowleveltype, methods)
        
        
        # step 3: provide accessor methods for class attributes that
        # are really overridden in subclasses. Must be done here
        # instead of _setup_repr to avoid recursion problems if class
        # attributes are Instances of self.lowleveltype.
        
        for mangled, (s_value, value) in self.classattributes.items():
            r = self.rtyper.getrepr(s_value)
            if value is None:
                self.attach_abstract_class_attr_accessor(mangled,
                                                         r.lowleveltype)
            else:
                oovalue = r.convert_desc_or_const(value)
                self.attach_class_attr_accessor(mangled, oovalue)

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

    def _get_field(self, attr):
        mangled = mangle(attr, self.rtyper.getconfig())
        return mangled, self.allfields[mangled]

    def attach_abstract_class_attr_accessor(self, mangled, attrtype):
        M = ootype.Meth([], attrtype)
        m = ootype.meth(M, _name=mangled, abstract=True)
        ootype.addMethods(self.lowleveltype, {mangled: m})

    def attach_class_attr_accessor(self, mangled, oovalue):
        def ll_getclassattr(self):
            return oovalue

        M = ootype.Meth([], ootype.typeOf(oovalue))
        ll_getclassattr = func_with_new_name(ll_getclassattr,
                                             'll_get_' + mangled)
        graph = self.rtyper.annotate_helper(ll_getclassattr, [self.lowleveltype])
        m = ootype.meth(M, _name=mangled, _callable=ll_getclassattr,
                        graph=graph)
        ootype.addMethods(self.lowleveltype, {mangled: m})

    def rtype_getattr(self, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)
        v_inst, _ = hop.inputargs(self, ootype.Void)
        s_inst = hop.args_s[0]
        attr = hop.args_s[1].const
        mangled = mangle(attr, self.rtyper.getconfig())
        if mangled in self.allfields:
            # regular instance attributes
            return self.getfield(v_inst, attr, hop.llops,
                                 flags=hop.args_s[0].flags)
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
            expected_type = hop.r_result.lowleveltype
            if expected_type is ootype.Void:
                # special case for when the result of '.__class__' is constant
                [desc] = hop.s_result.descriptions
                return hop.inputconst(ootype.Void, desc.pyobj)
            elif expected_type == ootype.Class:
                return hop.genop('classof', [v_inst],
                                 resulttype = ootype.Class)
            else:
                assert expected_type == META
                _, meth = v_inst.concretetype._lookup('getmeta')
                assert meth
                c_getmeta = hop.inputconst(ootype.Void, 'getmeta')
                return hop.genop('oosend', [c_getmeta, v_inst],
                                 resulttype = META)
        else:
            raise TyperError("no attribute %r on %r" % (attr, self))

    def rtype_setattr(self, hop):
        attr = hop.args_s[1].const
        mangled = mangle(attr, self.rtyper.getconfig())
        self.lowleveltype._check_field(mangled)
        r_value = self.allfields[mangled]
        v_inst, _, v_newval = hop.inputargs(self, ootype.Void, r_value)
        self.setfield(v_inst, attr, v_newval, hop.llops,
                      flags=hop.args_s[0].flags)

    def getfield(self, v_inst, attr, llops, flags={}):
        mangled = mangle(attr, self.rtyper.getconfig())
        v_attr = inputconst(ootype.Void, mangled)
        r_value = self.allfields[mangled]
        self.lowleveltype._check_field(mangled)
        self.hook_access_field(v_inst, v_attr, llops, flags)
        return llops.genop('oogetfield', [v_inst, v_attr],
                           resulttype = r_value)

    def setfield(self, vinst, attr, vvalue, llops, flags={}):
        mangled_name = mangle(attr, self.rtyper.getconfig())
        cname = inputconst(ootype.Void, mangled_name)
        self.hook_access_field(vinst, cname, llops, flags)
        llops.genop('oosetfield', [vinst, cname, vvalue])

    def hook_access_field(self, vinst, cname, llops, flags):
        pass        # for virtualizables; see rvirtualizable2.py

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
            return hop.genop('classof', [vinst], resulttype=ootype.Class)

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
        return v_instance
        
    def initialize_prebuilt_data(self, value, classdef, result):
        # then add instance attributes from this level
        classrepr = getclassrepr(self.rtyper, self.classdef)
        for mangled, (oot, default) in self.lowleveltype._allfields().items():
            if oot is ootype.Void:
                llattrvalue = None
            elif mangled == 'meta':
                llattrvalue = classrepr.get_meta_instance()
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

    def initialize_prebuilt_hash(self, value, result):
        pass


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

def ll_inst_type(obj):
    if obj:
        return ootype.classof(obj)
    else:
        # type(None) -> NULL  (for now)
        return ootype.nullruntimeclass
