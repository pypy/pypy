import types
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import isclassdef
from pypy.rpython.rmodel import Repr, TyperError, inputconst, warning
from pypy.rpython.lltype import ForwardReference, GcForwardReference
from pypy.rpython.lltype import Ptr, Struct, GcStruct, malloc
from pypy.rpython.lltype import cast_pointer, castable, nullptr
from pypy.rpython.lltype import RuntimeTypeInfo, getRuntimeTypeInfo, typeOf
from pypy.rpython.lltype import Array, Char, Void, attachRuntimeTypeInfo

#
#  There is one "vtable" per user class, with the following structure:
#  A root class "object" has:
#
#      struct object_vtable {
#          struct object_vtable* parenttypeptr;
#          RuntimeTypeInfo * rtti;
#          array { char } * name;
#      }
#
#  Every other class X, with parent Y, has the structure:
#
#      struct vtable_X {
#          struct vtable_Y super;   // inlined
#          ...                      // extra class attributes
#      }

# The type of the instances is:
#
#     struct object {       // for the root class
#         struct object_vtable* typeptr;
#     }
#
#     struct X {
#         struct Y super;   // inlined
#         ...               // extra instance attributes
#     }
#

OBJECT_VTABLE = ForwardReference()
TYPEPTR = Ptr(OBJECT_VTABLE)
OBJECT_VTABLE.become(Struct('object_vtable',
                            ('parenttypeptr', TYPEPTR),
                            ('rtti', Ptr(RuntimeTypeInfo)),
                            ('name', Ptr(Array(Char)))))

OBJECT = GcStruct('object', ('typeptr', TYPEPTR))
OBJECTPTR = Ptr(OBJECT)

def getclassrepr(rtyper, classdef):
    try:
        result = rtyper.class_reprs[classdef]
    except KeyError:
        if classdef and classdef.cls is Exception:
            # skip Exception as a base class and go directly to 'object'.
            # the goal is to allow any class anywhere in the hierarchy
            # to have Exception as a second base class.  It should be an
            # empty class anyway.
            if classdef.attrs:
                raise TyperError("the Exception class should not "
                                 "have any attribute attached to it")
            result = getclassrepr(rtyper, None)
        else:
            result = ClassRepr(rtyper, classdef)
        rtyper.class_reprs[classdef] = result
        rtyper.reprs_must_call_setup.append(result)
    return result

def getinstancerepr(rtyper, classdef):
    try:
        result = rtyper.instance_reprs[classdef]
    except KeyError:
        if classdef and classdef.cls is Exception:
            # see getclassrepr()
            result = getinstancerepr(rtyper, None)
        else:
            result = InstanceRepr(rtyper,classdef)
        rtyper.instance_reprs[classdef] = result
        rtyper.reprs_must_call_setup.append(result)
    return result

class MissingRTypeAttribute(TyperError):
    pass


def cast_vtable_to_typeptr(vtable):
    while typeOf(vtable).TO != OBJECT_VTABLE:
        vtable = vtable.super
    return vtable


class ClassRepr(Repr):
    initialized = False

    def __init__(self, rtyper, classdef):
        self.rtyper = rtyper
        self.classdef = classdef
        if classdef is None:
            # 'object' root type
            self.vtable_type = OBJECT_VTABLE
        else:
            self.vtable_type = ForwardReference()
        self.lowleveltype = Ptr(self.vtable_type)

    def __repr__(self):
        if self.classdef is None:
            cls = object
        else:
            cls = self.classdef.cls
        return '<ClassRepr for %s.%s>' % (cls.__module__, cls.__name__)

    def setup(self):
        if self.initialized:
            assert self.initialized == True
            return
        self.initialized = "in progress"
        # NOTE: don't store mutable objects like the dicts below on 'self'
        #       before they are fully built, to avoid strange bugs in case
        #       of recursion where other code would uses these
        #       partially-initialized dicts.
        clsfields = {}
        allmethods = {}
        if self.classdef is not None:
            # class attributes
            llfields = []
            attrs = self.classdef.attrs.items()
            attrs.sort()
            for name, attrdef in attrs:
                if attrdef.readonly:
                    s_value = attrdef.s_value
                    s_value = self.prepare_method(name, s_value, allmethods)
                    r = self.rtyper.getrepr(s_value)
                    mangled_name = 'cls_' + name
                    clsfields[name] = mangled_name, r
                    llfields.append((mangled_name, r.lowleveltype))
            #
            self.rbase = getclassrepr(self.rtyper, self.classdef.basedef)
            self.rbase.setup()
            vtable_type = Struct('%s_vtable' % self.classdef.cls.__name__,
                                 ('super', self.rbase.vtable_type),
                                 *llfields)
            self.vtable_type.become(vtable_type)
            allmethods.update(self.rbase.allmethods)
        self.clsfields = clsfields
        self.allmethods = allmethods
        self.vtable = None
        self.initialized = True

    def prepare_method(self, name, s_value, allmethods):
        # special-casing for methods:
        #  - a class (read-only) attribute that would contain a PBC
        #    with {func: classdef...} is probably meant to be used as a
        #    method, but in corner cases it could be a constant object
        #    of type MethodType that just sits here in the class.  But
        #    as MethodType has a custom __get__ too and we don't support
        #    it, it's a very bad idea anyway.
        if isinstance(s_value, annmodel.SomePBC):
            s_value = self.classdef.matching(s_value)
            debound = {}
            count = 0
            for x, classdef in s_value.prebuiltinstances.items():
                if isclassdef(classdef):
                    #if classdef.commonbase(self.classdef) != self.classdef:
                    #    raise TyperError("methods from PBC set %r don't belong "
                    #                     "in %r" % (s_value.prebuiltinstances,
                    #                                self.classdef.cls))
                    count += 1
                    classdef = True
                debound[x] = classdef
            if count > 0:
                if count != len(s_value.prebuiltinstances):
                    raise TyperError("mixing functions and methods "
                                     "in PBC set %r" % (
                        s_value.prebuiltinstances,))
                s_value = annmodel.SomePBC(debound)
                allmethods[name] = True
        return s_value

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
        return getclassrepr(self.rtyper, subclassdef).getvtable()

    def getvtable(self, cast_to_typeptr=True):
        """Return a ptr to the vtable of this type."""
        if self.vtable is None:
            self.vtable = malloc(self.vtable_type, immortal=True)
            self.setup_vtable(self.vtable, self)
        #
        vtable = self.vtable
        if cast_to_typeptr:
            vtable = cast_vtable_to_typeptr(vtable)
        return vtable

    def setup_vtable(self, vtable, rsubcls):
        """Initialize the 'self' portion of the 'vtable' belonging to the
        given subclass."""
        if self.classdef is None:
            # initialize the 'parenttypeptr' and 'name' fields
            if rsubcls.classdef is not None:
                vtable.parenttypeptr = rsubcls.rbase.getvtable()
            rinstance = getinstancerepr(self.rtyper, rsubcls.classdef)
            rinstance.setup()
            vtable.rtti = getRuntimeTypeInfo(rinstance.object_type)
            if rsubcls.classdef is None:
                name = 'object'
            else:
                name = rsubcls.classdef.cls.__name__
            vtable.name = malloc(Array(Char), len(name)+1, immortal=True)
            for i in range(len(name)):
                vtable.name[i] = name[i]
            vtable.name[len(name)] = '\x00'
        else:
            # setup class attributes: for each attribute name at the level
            # of 'self', look up its value in the subclass rsubcls
            mro = list(rsubcls.classdef.getmro())
            for fldname in self.clsfields:
                mangled_name, r = self.clsfields[fldname]
                if r.lowleveltype == Void:
                    continue
                for clsdef in mro:
                    if fldname in clsdef.cls.__dict__:
                        value = clsdef.cls.__dict__[fldname]
                        llvalue = r.convert_const(value)
                        setattr(vtable, mangled_name, llvalue)
                        break
            # then initialize the 'super' portion of the vtable
            self.rbase.setup_vtable(vtable.super, rsubcls)

    #def fromparentpart(self, v_vtableptr, llops):
    #    """Return the vtable pointer cast from the parent vtable's type
    #    to self's vtable type."""

    def fromtypeptr(self, vcls, llops):
        """Return the type pointer cast to self's vtable type."""
        castable(self.lowleveltype, vcls.concretetype) # sanity check
        return llops.genop('cast_pointer', [vcls],
                           resulttype=self.lowleveltype)

    def getclsfieldrepr(self, attr):
        """Return the repr used for the given attribute."""
        if attr in self.clsfields:
            mangled_name, r = self.clsfields[attr]
            return r
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            return self.rbase.getfieldrepr(attr)

    def getclsfield(self, vcls, attr, llops):
        """Read the given attribute of 'vcls'."""
        if attr in self.clsfields:
            mangled_name, r = self.clsfields[attr]
            v_vtable = self.fromtypeptr(vcls, llops)
            cname = inputconst(Void, mangled_name)
            return llops.genop('getfield', [v_vtable, cname], resulttype=r)
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            return self.rbase.getclsfield(vcls, attr, llops)

    def setclsfield(self, vcls, attr, vvalue, llops):
        """Write the given attribute of 'vcls'."""
        if attr in self.clsfields:
            mangled_name, r = self.clsfields[attr]
            v_vtable = self.fromtypeptr(vcls, llops)
            cname = inputconst(Void, mangled_name)
            llops.genop('setfield', [v_vtable, cname, vvalue])
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            self.rbase.setclsfield(vcls, attr, vvalue, llops)

    def rtype_issubtype(self, hop): 
        class_repr = get_type_repr(self.rtyper)
        v_cls1, v_cls2 = hop.inputargs(class_repr, class_repr)
        return hop.gendirectcall(ll_issubclass, v_cls1, v_cls2)

def get_type_repr(rtyper):
    return getclassrepr(rtyper, None)

# ____________________________________________________________


class __extend__(annmodel.SomeInstance):
    def rtyper_makerepr(self, rtyper):
        return getinstancerepr(rtyper, self.classdef)
    def rtyper_makekey(self):
        return self.classdef


class InstanceRepr(Repr):
    initialized = False

    def __init__(self, rtyper, classdef):
        self.rtyper = rtyper
        self.classdef = classdef
        if classdef is None:
            self.object_type = OBJECT
        else:
            self.object_type = GcForwardReference()
        self.prebuiltinstances = {}   # { id(x): (x, _ptr) }
        self.lowleveltype = Ptr(self.object_type)

    def __repr__(self):
        if self.classdef is None:
            cls = object
        else:
            cls = self.classdef.cls
        return '<InstanceRepr for %s.%s>' % (cls.__module__, cls.__name__)

    def setup(self):
        if self.initialized:
            assert self.initialized == True
            return
        self.initialized = "in progress"
        # NOTE: don't store mutable objects like the dicts below on 'self'
        #       before they are fully built, to avoid strange bugs in case
        #       of recursion where other code would uses these
        #       partially-initialized dicts.
        self.rclass = getclassrepr(self.rtyper, self.classdef)
        fields = {}
        allinstancefields = {}
        if self.classdef is None:
            fields['__class__'] = 'typeptr', get_type_repr(self.rtyper)
        else:
            # instance attributes
            llfields = []
            attrs = self.classdef.attrs.items()
            attrs.sort()
            for name, attrdef in attrs:
                if not attrdef.readonly:
                    r = self.rtyper.getrepr(attrdef.s_value)
                    mangled_name = 'inst_' + name
                    fields[name] = mangled_name, r
                    llfields.append((mangled_name, r.lowleveltype))
            #
            self.rbase = getinstancerepr(self.rtyper, self.classdef.basedef)
            self.rbase.setup()
            object_type = GcStruct(self.classdef.cls.__name__,
                                   ('super', self.rbase.object_type),
                                   *llfields)
            self.object_type.become(object_type)
            allinstancefields.update(self.rbase.allinstancefields)
        allinstancefields.update(fields)
        self.fields = fields
        self.allinstancefields = allinstancefields
        attachRuntimeTypeInfo(self.object_type)
        self.initialized = True

    def setup_final_touch(self):
        self.rtyper.attachRuntimeTypeInfoFunc(self.object_type,
                                              ll_runtime_type_info,
                                              OBJECT)

    def convert_const(self, value):
        if value is None:
            return nullptr(self.object_type)
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
            return cast_pointer(self.lowleveltype, result)
        # common case
        try:
            return self.prebuiltinstances[id(value)][1]
        except KeyError:
            self.setup()
            result = malloc(self.object_type)
            self.prebuiltinstances[id(value)] = value, result
            self.initialize_prebuilt_instance(value, classdef, result)
            return result

    def get_ll_eq_function(self):
        return None

    def initialize_prebuilt_instance(self, value, classdef, result):
        if self.classdef is not None:
            # recursively build the parent part of the instance
            self.rbase.initialize_prebuilt_instance(value, classdef,
                                                    result.super)
            # then add instance attributes from this level
            for name, (mangled_name, r) in self.fields.items():
                if r.lowleveltype == Void:
                    llattrvalue = None
                else:
                    try:
                        attrvalue = getattr(value, name)
                    except AttributeError:
                        warning("prebuilt instance %r has no attribute %r" % (
                            value, name))
                        continue
                    llattrvalue = r.convert_const(attrvalue)
                setattr(result, mangled_name, llattrvalue)
        else:
            # OBJECT part
            rclass = getclassrepr(self.rtyper, classdef)
            result.typeptr = rclass.getvtable()

    #def parentpart(self, vinst, llops):
    #    """Return the pointer 'vinst' cast to the parent type."""
    #    cname = inputconst(Void, 'super')
    #    return llops.genop('getsubstruct', [vinst, cname],
    #                       resulttype=self.rbase.lowleveltype)

    def getfieldrepr(self, attr):
        """Return the repr used for the given attribute."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            return r
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            return self.rbase.getfieldrepr(attr)

    def getfield(self, vinst, attr, llops, force_cast=False):
        """Read the given attribute (or __class__ for the type) of 'vinst'."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            cname = inputconst(Void, mangled_name)
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            return llops.genop('getfield', [vinst, cname], resulttype=r)
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            return self.rbase.getfield(vinst, attr, llops, force_cast=True)

    def setfield(self, vinst, attr, vvalue, llops, force_cast=False):
        """Write the given attribute (or __class__ for the type) of 'vinst'."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            cname = inputconst(Void, mangled_name)
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            llops.genop('setfield', [vinst, cname, vvalue])
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            self.rbase.setfield(vinst, attr, vvalue, llops, force_cast=True)

    def new_instance(self, llops):
        """Build a new instance, without calling __init__."""
        ctype = inputconst(Void, self.object_type)
        vptr = llops.genop('malloc', [ctype],
                           resulttype = Ptr(self.object_type))
        ctypeptr = inputconst(TYPEPTR, self.rclass.getvtable())
        self.setfield(vptr, '__class__', ctypeptr, llops)
        # initialize instance attributes from their defaults from the class
        if self.classdef is not None:
            flds = self.allinstancefields.keys()
            flds.sort()
            mro = list(self.classdef.getmro())
            for fldname in flds:
                if fldname == '__class__':
                    continue
                mangled_name, r = self.allinstancefields[fldname]
                if r.lowleveltype == Void:
                    continue
                for clsdef in mro:
                    if fldname in clsdef.cls.__dict__:
                        value = clsdef.cls.__dict__[fldname]
                        cvalue = inputconst(r, value)
                        self.setfield(vptr, fldname, cvalue, llops)
                        break
        return vptr

    def rtype_type(self, hop):
        vinst, = hop.inputargs(self)
        return self.getfield(vinst, '__class__', hop.llops)

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        vinst, vattr = hop.inputargs(self, Void)
        if attr in self.allinstancefields:
            return self.getfield(vinst, attr, hop.llops)
        elif attr in self.rclass.allmethods:
            # special case for methods: represented as their 'self' only
            # (see MethodsPBCRepr)
            return hop.r_result.get_method_from_instance(self, vinst,
                                                         hop.llops)
        else:
            vcls = self.getfield(vinst, '__class__', hop.llops)
            return self.rclass.getclsfield(vcls, attr, hop.llops)

    def rtype_setattr(self, hop):
        attr = hop.args_s[1].const
        r_value = self.getfieldrepr(attr)
        vinst, vattr, vvalue = hop.inputargs(self, Void, r_value)
        self.setfield(vinst, attr, vvalue, hop.llops)

    def ll_str(i, r):
        instance = cast_pointer(OBJECTPTR, i)
        from pypy.rpython import rstr
        nameLen = len(instance.typeptr.name)
        nameString = malloc(rstr.STR, nameLen-1)
        i = 0
        while i < nameLen - 1:
            nameString.chars[i] = instance.typeptr.name[i]
            i += 1
        return rstr.ll_strconcat(rstr.instance_str_prefix,
                                 rstr.ll_strconcat(nameString,
                                                   rstr.instance_str_suffix))
    ll_str = staticmethod(ll_str)


class __extend__(pairtype(InstanceRepr, InstanceRepr)):
    def convert_from_to((r_ins1, r_ins2), v, llops):
        # which is a subclass of which?
        if r_ins1.classdef is None or r_ins2.classdef is None:
            basedef = None
        else:
            basedef = r_ins1.classdef.commonbase(r_ins2.classdef)
        if basedef == r_ins2.classdef:
            # r_ins1 is an instance of the subclass: converting to parent
            v = llops.genop('cast_pointer', [v],
                            resulttype = r_ins2.lowleveltype)
            return v
        elif basedef == r_ins1.classdef:
            # r_ins2 is an instance of the subclass: potentially unsafe
            # casting, but we do it anyway (e.g. the annotator produces
            # such casts after a successful isinstance() check)
            v = llops.genop('cast_pointer', [v],
                            resulttype = r_ins2.lowleveltype)
            return v
        else:
            return NotImplemented

# ____________________________________________________________

def rtype_new_instance(rtyper, cls, llops):
    classdef = rtyper.annotator.getuserclasses()[cls]
    rinstance = getinstancerepr(rtyper, classdef)
    return rinstance.new_instance(llops)

def instance_annotation_for_cls(rtyper, cls):
    try:
        classdef = rtyper.annotator.getuserclasses()[cls]
    except KeyError:
        raise TyperError("no classdef: %r" % (cls,))
    return annmodel.SomeInstance(classdef)

# ____________________________________________________________
#
#  Low-level implementation of operations on classes and instances

def ll_cast_to_object(obj):
    return cast_pointer(OBJECTPTR, obj)

def ll_type(obj):
    return cast_pointer(OBJECTPTR, obj).typeptr

def ll_issubclass(subcls, cls):
    while subcls != cls:
        if not subcls:
            return False
        subcls = subcls.parenttypeptr
    return True

def ll_runtime_type_info(obj):
    return obj.typeptr.rtti
