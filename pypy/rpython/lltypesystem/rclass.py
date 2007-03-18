import sys
import types
from pypy.annotation.pairtype import pairtype, pair
from pypy.objspace.flow.model import Constant
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, inputconst, warning, mangle
from pypy.rpython.rclass import AbstractClassRepr,\
                                AbstractInstanceRepr,\
                                MissingRTypeAttribute,\
                                getclassrepr, getinstancerepr,\
                                get_type_repr, rtype_new_instance
from pypy.rpython.lltypesystem.lltype import \
     Ptr, Struct, GcStruct, malloc, \
     cast_pointer, castable, nullptr, \
     RuntimeTypeInfo, getRuntimeTypeInfo, typeOf, \
     Array, Char, Void, attachRuntimeTypeInfo, \
     FuncType, Bool, Signed, functionptr, FuncType, PyObject
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation import model as annmodel
from pypy.rlib.objectmodel import UnboxedValue
from pypy.rlib.rarithmetic import intmask

#
#  There is one "vtable" per user class, with the following structure:
#  A root class "object" has:
#
#      struct object_vtable {
#          // struct object_vtable* parenttypeptr;  not used any more
#          RuntimeTypeInfo * rtti;
#          Signed subclassrange_min;  //this is also the id of the class itself
#          Signed subclassrange_max;
#          array { char } * name;
#          struct object * instantiate();
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
# there's also a nongcobject 

OBJECT_VTABLE = lltype.ForwardReference()
CLASSTYPE = Ptr(OBJECT_VTABLE)
OBJECT = GcStruct('object', ('typeptr', CLASSTYPE),
                  hints = {'immutable': True, 'shouldntbenull': True})
OBJECTPTR = Ptr(OBJECT)
OBJECT_VTABLE.become(Struct('object_vtable',
                            #('parenttypeptr', CLASSTYPE),
                            ('subclassrange_min', Signed),
                            ('subclassrange_max', Signed),
                            ('rtti', Ptr(RuntimeTypeInfo)),
                            ('name', Ptr(Array(Char))),
                            ('instantiate', Ptr(FuncType([], OBJECTPTR))),
                            hints = {'immutable': True}))
# non-gc case
NONGCOBJECT = Struct('nongcobject', ('typeptr', CLASSTYPE))
NONGCOBJECTPTR = Ptr(OBJECT)

# cpy case (XXX try to merge the typeptr with the ob_type)
CPYOBJECT = lltype.PyStruct('cpyobject', ('head', PyObject),
                                         ('typeptr', CLASSTYPE))
CPYOBJECTPTR = Ptr(CPYOBJECT)

OBJECT_BY_FLAVOR = {'gc': OBJECT,
                    'raw': NONGCOBJECT,
                    'cpy': CPYOBJECT}

LLFLAVOR = {'gc'   : 'gc',
            'raw'  : 'raw',
            'cpy'  : 'cpy',
            'stack': 'raw',
            }
RTTIFLAVORS = ('gc', 'cpy')

def cast_vtable_to_typeptr(vtable):
    while typeOf(vtable).TO != OBJECT_VTABLE:
        vtable = vtable.super
    return vtable


class ClassRepr(AbstractClassRepr):
    def __init__(self, rtyper, classdef):
        AbstractClassRepr.__init__(self, rtyper, classdef)
        if classdef is None:
            # 'object' root type
            self.vtable_type = OBJECT_VTABLE
        else:
            self.vtable_type = lltype.ForwardReference()
        self.lowleveltype = Ptr(self.vtable_type)

    def _setup_repr(self):
        # NOTE: don't store mutable objects like the dicts below on 'self'
        #       before they are fully built, to avoid strange bugs in case
        #       of recursion where other code would uses these
        #       partially-initialized dicts.
        clsfields = {}
        pbcfields = {}
        allmethods = {}
        if self.classdef is not None:
            # class attributes
            llfields = []
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
            # attributes showing up in getattrs done on the class as a PBC
            extra_access_sets = self.rtyper.class_pbc_attributes.get(
                self.classdef, {})
            for access_set, (attr, counter) in extra_access_sets.items():
                r = self.rtyper.getrepr(access_set.s_value)
                mangled_name = mangle('pbc%d' % counter, attr)
                pbcfields[access_set, attr] = mangled_name, r
                llfields.append((mangled_name, r.lowleveltype))
            #
            self.rbase = getclassrepr(self.rtyper, self.classdef.basedef)
            self.rbase.setup()
            kwds = {'hints': {'immutable': True}}
            vtable_type = Struct('%s_vtable' % self.classdef.name,
                                 ('super', self.rbase.vtable_type),
                                 *llfields, **kwds)
            self.vtable_type.become(vtable_type)
            allmethods.update(self.rbase.allmethods)
        self.clsfields = clsfields
        self.pbcfields = pbcfields
        self.allmethods = allmethods
        self.vtable = None

#    def convert_const(self, value):
#        if not isinstance(value, (type, types.ClassType)):
#            raise TyperError("not a class: %r" % (value,))
#        try:
#            subclassdef = self.rtyper.annotator.getuserclasses()[value]
#        except KeyError:
#            raise TyperError("no classdef: %r" % (value,))
#        if self.classdef is not None:
#            if self.classdef.commonbase(subclassdef) != self.classdef:
#                raise TyperError("not a subclass of %r: %r" % (
#                    self.classdef.cls, value))
#        #
#        return getclassrepr(self.rtyper, subclassdef).getvtable()

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
    getruntime = getvtable

    def setup_vtable(self, vtable, rsubcls):
        """Initialize the 'self' portion of the 'vtable' belonging to the
        given subclass."""
        if self.classdef is None:
            # initialize the 'subclassrange_*' and 'name' fields
            if rsubcls.classdef is not None:
                #vtable.parenttypeptr = rsubcls.rbase.getvtable()
                vtable.subclassrange_min = rsubcls.classdef.minid
                vtable.subclassrange_max = rsubcls.classdef.maxid
            else: #for the root class
                vtable.subclassrange_min = 0
                vtable.subclassrange_max = sys.maxint
            rinstance = getinstancerepr(self.rtyper, rsubcls.classdef)
            rinstance.setup()
            if rinstance.gcflavor in RTTIFLAVORS:
                vtable.rtti = getRuntimeTypeInfo(rinstance.object_type)
            if rsubcls.classdef is None:
                name = 'object'
            else:
                name = rsubcls.classdef.shortname
            vtable.name = malloc(Array(Char), len(name)+1, immortal=True)
            for i in range(len(name)):
                vtable.name[i] = name[i]
            vtable.name[len(name)] = '\x00'
            if hasattr(rsubcls.classdef, 'my_instantiate_graph'):
                graph = rsubcls.classdef.my_instantiate_graph
                vtable.instantiate = self.rtyper.getcallable(graph)
            #else: the classdef was created recently, so no instantiate()
            #      could reach it
        else:
            # setup class attributes: for each attribute name at the level
            # of 'self', look up its value in the subclass rsubcls
            def assign(mangled_name, value):
                if isinstance(value, Constant) and isinstance(value.value, staticmethod):
                    value = Constant(value.value.__get__(42))   # staticmethod => bare function
                llvalue = r.convert_desc_or_const(value)
                setattr(vtable, mangled_name, llvalue)

            mro = list(rsubcls.classdef.getmro())
            for fldname in self.clsfields:
                mangled_name, r = self.clsfields[fldname]
                if r.lowleveltype is Void:
                    continue
                value = rsubcls.classdef.classdesc.read_attribute(fldname, None)
                if value is not None:
                    assign(mangled_name, value)
            # extra PBC attributes
            for (access_set, attr), (mangled_name, r) in self.pbcfields.items():
                if rsubcls.classdef.classdesc not in access_set.descs:
                    continue   # only for the classes in the same pbc access set
                if r.lowleveltype is Void:
                    continue
                attrvalue = rsubcls.classdef.classdesc.read_attribute(attr, None)
                if attrvalue is not None:
                    assign(mangled_name, attrvalue)

            # then initialize the 'super' portion of the vtable
            self.rbase.setup_vtable(vtable.super, rsubcls)

    #def fromparentpart(self, v_vtableptr, llops):
    #    """Return the vtable pointer cast from the parent vtable's type
    #    to self's vtable type."""

    def fromtypeptr(self, vcls, llops):
        """Return the type pointer cast to self's vtable type."""
        self.setup()
        castable(self.lowleveltype, vcls.concretetype) # sanity check
        return llops.genop('cast_pointer', [vcls],
                           resulttype=self.lowleveltype)

    fromclasstype = fromtypeptr

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

    def getpbcfield(self, vcls, access_set, attr, llops):
        if (access_set, attr) not in self.pbcfields:
            raise TyperError("internal error: missing PBC field")
        mangled_name, r = self.pbcfields[access_set, attr]
        v_vtable = self.fromtypeptr(vcls, llops)
        cname = inputconst(Void, mangled_name)
        return llops.genop('getfield', [v_vtable, cname], resulttype=r)

    def rtype_issubtype(self, hop): 
        class_repr = get_type_repr(self.rtyper)
        v_cls1, v_cls2 = hop.inputargs(class_repr, class_repr)
        if isinstance(v_cls2, Constant):
            cls2 = v_cls2.value
            # XXX re-implement the following optimization
##            if cls2.subclassrange_max == cls2.subclassrange_min:
##                # a class with no subclass
##                return hop.genop('ptr_eq', [v_cls1, v_cls2], resulttype=Bool)
##            else:
            minid = hop.inputconst(Signed, cls2.subclassrange_min)
            maxid = hop.inputconst(Signed, cls2.subclassrange_max)
            return hop.gendirectcall(ll_issubclass_const, v_cls1, minid,
                                     maxid)
        else:
            v_cls1, v_cls2 = hop.inputargs(class_repr, class_repr)
            return hop.gendirectcall(ll_issubclass, v_cls1, v_cls2)

# ____________________________________________________________


class InstanceRepr(AbstractInstanceRepr):
    def __init__(self, rtyper, classdef, gcflavor='gc'):
        AbstractInstanceRepr.__init__(self, rtyper, classdef)
        if classdef is None:
            self.object_type = OBJECT_BY_FLAVOR[LLFLAVOR[gcflavor]]
        else:
            ForwardRef = lltype.FORWARDREF_BY_FLAVOR[LLFLAVOR[gcflavor]]
            self.object_type = ForwardRef()
            
        self.prebuiltinstances = {}   # { id(x): (x, _ptr) }
        self.lowleveltype = Ptr(self.object_type)
        self.gcflavor = gcflavor

    def _setup_repr(self, llfields=None, hints=None, adtmeths=None):
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
            if llfields is None:
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
            # hash() support
            if self.rtyper.needs_hash_support(self.classdef):
                from pypy.rpython import rint
                fields['_hash_cache_'] = 'hash_cache', rint.signed_repr
                llfields.append(('hash_cache', Signed))

            self.rbase = getinstancerepr(self.rtyper, self.classdef.basedef,
                                         self.gcflavor)
            self.rbase.setup()
            #
            # PyObject wrapper support
            if self.has_wrapper and '_wrapper_' not in self.rbase.allinstancefields:
                fields['_wrapper_'] = 'wrapper', pyobj_repr
                llfields.append(('wrapper', Ptr(PyObject)))

            MkStruct = lltype.STRUCT_BY_FLAVOR[LLFLAVOR[self.gcflavor]]
            if adtmeths is None:
                adtmeths = {}
            if hints is None:
                hints = {}
            object_type = MkStruct(self.classdef.name,
                                   ('super', self.rbase.object_type),
                                   hints=hints,
                                   adtmeths=adtmeths,
                                   *llfields)
            self.object_type.become(object_type)
            allinstancefields.update(self.rbase.allinstancefields)
        allinstancefields.update(fields)
        self.fields = fields
        self.allinstancefields = allinstancefields
        if self.gcflavor in RTTIFLAVORS:
            attachRuntimeTypeInfo(self.object_type)

    def _setup_repr_final(self):
        if self.gcflavor in RTTIFLAVORS:
            if (self.classdef is not None and
                self.classdef.classdesc.lookup('__del__') is not None):
                s_func = self.classdef.classdesc.s_read_attribute('__del__')
                source_desc = self.classdef.classdesc.lookup('__del__')
                source_classdef = source_desc.getclassdef(None)
                source_repr = getinstancerepr(self.rtyper, source_classdef)
                assert len(s_func.descriptions) == 1
                funcdesc = s_func.descriptions.keys()[0]
                graph = funcdesc.getuniquegraph()
                FUNCTYPE = FuncType([Ptr(source_repr.object_type)], Void)
                destrptr = functionptr(FUNCTYPE, graph.name,
                                       graph=graph,
                                       _callable=graph.func)
            else:
                destrptr = None
            OBJECT = OBJECT_BY_FLAVOR[LLFLAVOR[self.gcflavor]]
            self.rtyper.attachRuntimeTypeInfoFunc(self.object_type,
                                                  ll_runtime_type_info,
                                                  OBJECT, destrptr)
    def common_repr(self): # -> object or nongcobject reprs
        return getinstancerepr(self.rtyper, None, self.gcflavor)

    def null_instance(self):
        return nullptr(self.object_type)

    def upcast(self, result):
        return cast_pointer(self.lowleveltype, result)

    def create_instance(self):
        if self.gcflavor == 'cpy':
            from pypy.rpython import rcpy
            extra_args = (rcpy.build_pytypeobject(self),)
        else:
            extra_args = ()
        return malloc(self.object_type, flavor=self.gcflavor,
                      extra_args=extra_args)

    def has_wrapper(self):
        return self.classdef is not None and (
            self.rtyper.needs_wrapper(self.classdef.classdesc.pyobj))
    has_wrapper = property(has_wrapper)

    def get_ll_hash_function(self):
        if self.classdef is None:
            raise TyperError, 'missing hash support flag in classdef'
        if self.rtyper.needs_hash_support(self.classdef):
            try:
                return self._ll_hash_function
            except AttributeError:
                INSPTR = self.lowleveltype
                def _ll_hash_function(ins):
                    return ll_inst_hash(cast_pointer(INSPTR, ins))
                self._ll_hash_function = _ll_hash_function
                return _ll_hash_function
        else:
            return self.rbase.get_ll_hash_function()

    def initialize_prebuilt_instance(self, value, classdef, result):
        if self.classdef is not None:
            # recursively build the parent part of the instance
            self.rbase.initialize_prebuilt_instance(value, classdef,
                                                    result.super)
            # then add instance attributes from this level
            for name, (mangled_name, r) in self.fields.items():
                if r.lowleveltype is Void:
                    llattrvalue = None
                elif name == '_hash_cache_': # hash() support
                    llattrvalue = hash(value)
                else:
                    try:
                        attrvalue = getattr(value, name)
                    except AttributeError:
                        attrvalue = self.classdef.classdesc.read_attribute(name, None)
                        if attrvalue is None:
                            warning("prebuilt instance %r has no attribute %r" % (
                                    value, name))
                            llattrvalue = r.lowleveltype._defl()
                        else:
                            llattrvalue = r.convert_desc_or_const(attrvalue)
                    else:
                        llattrvalue = r.convert_const(attrvalue)
                setattr(result, mangled_name, llattrvalue)
        else:
            # OBJECT part
            rclass = getclassrepr(self.rtyper, classdef)
            result.typeptr = rclass.getvtable()

    def getfieldrepr(self, attr):
        """Return the repr used for the given attribute."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            return r
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            return self.rbase.getfieldrepr(attr)

    def getfield(self, vinst, attr, llops, force_cast=False, flags={}):
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
            return self.rbase.getfield(vinst, attr, llops, force_cast=True,
                                       flags=flags)

    def setfield(self, vinst, attr, vvalue, llops, force_cast=False,
                 opname='setfield', flags={}):
        """Write the given attribute (or __class__ for the type) of 'vinst'."""
        if attr in self.fields:
            mangled_name, r = self.fields[attr]
            cname = inputconst(Void, mangled_name)
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            llops.genop(opname, [vinst, cname, vvalue])
            # XXX this is a temporary hack to clear a dead PyObject
        else:
            if self.classdef is None:
                raise MissingRTypeAttribute(attr)
            self.rbase.setfield(vinst, attr, vvalue, llops, force_cast=True,
                                opname=opname, flags=flags)

    def new_instance(self, llops, classcallhop=None, v_cpytype=None):
        """Build a new instance, without calling __init__."""
        mallocop = 'malloc'
        ctype = inputconst(Void, self.object_type)
        vlist = [ctype]
        if self.classdef is not None:
            flavor = self.gcflavor
            if flavor != 'gc': # not default flavor
                mallocop = 'flavored_malloc'
                vlist.insert(0, inputconst(Void, flavor))
                if flavor == 'cpy':
                    if v_cpytype is None:
                        from pypy.rpython import rcpy
                        cpytype = rcpy.build_pytypeobject(self)
                        v_cpytype = inputconst(Ptr(PyObject), cpytype)
                    vlist.append(v_cpytype)
        vptr = llops.genop(mallocop, vlist,
                           resulttype = Ptr(self.object_type))
        ctypeptr = inputconst(CLASSTYPE, self.rclass.getvtable())
        self.setfield(vptr, '__class__', ctypeptr, llops)
        # initialize instance attributes from their defaults from the class
        if self.classdef is not None:
            flds = self.allinstancefields.keys()
            flds.sort()
            for fldname in flds:
                if fldname == '__class__':
                    continue
                mangled_name, r = self.allinstancefields[fldname]
                if r.lowleveltype is Void:
                    continue
                if fldname == '_hash_cache_':
                    value = Constant(0, Signed)
                else:
                    value = self.classdef.classdesc.read_attribute(fldname, None)
                if value is not None:
                    cvalue = inputconst(r.lowleveltype,
                                        r.convert_desc_or_const(value))
                    self.setfield(vptr, fldname, cvalue, llops,
                                  {'access_directly': True})
        return vptr

    def rtype_type(self, hop):
        if hop.s_result.is_constant():
            return hop.inputconst(hop.r_result, hop.s_result.const)
        instance_repr = self.common_repr()
        vinst, = hop.inputargs(instance_repr)
        if hop.args_s[0].can_be_none():
            return hop.gendirectcall(ll_inst_type, vinst)
        else:
            return instance_repr.getfield(vinst, '__class__', hop.llops)

    def rtype_getattr(self, hop):
        attr = hop.args_s[1].const
        vinst, vattr = hop.inputargs(self, Void)
        if attr == '__class__' and hop.r_result.lowleveltype is Void:
            # special case for when the result of '.__class__' is a constant
            [desc] = hop.s_result.descriptions
            return hop.inputconst(Void, desc.pyobj)
        if attr in self.allinstancefields:
            return self.getfield(vinst, attr, hop.llops,
                                 flags=hop.args_s[0].flags)
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
        self.setfield(vinst, attr, vvalue, hop.llops,
                      flags=hop.args_s[0].flags)

    def rtype_is_true(self, hop):
        vinst, = hop.inputargs(self)
        return hop.genop('ptr_nonzero', [vinst], resulttype=Bool)

    def ll_str(self, i): # doesn't work for non-gc classes!
        from pypy.rpython.lltypesystem import rstr
        if not i:
            return rstr.null_str
        instance = cast_pointer(OBJECTPTR, i)
        nameLen = len(instance.typeptr.name)
        nameString = rstr.mallocstr(nameLen-1)
        i = 0
        while i < nameLen - 1:
            nameString.chars[i] = instance.typeptr.name[i]
            i += 1
        return rstr.ll_strconcat(rstr.instance_str_prefix,
                                 rstr.ll_strconcat(nameString,
                                                   rstr.instance_str_suffix))

    def rtype_isinstance(self, hop):
        class_repr = get_type_repr(hop.rtyper)
        instance_repr = self.common_repr()

        v_obj, v_cls = hop.inputargs(instance_repr, class_repr)
        if isinstance(v_cls, Constant):
            cls = v_cls.value
            # XXX re-implement the following optimization
            #if cls.subclassrange_max == cls.subclassrange_min:
            #    # a class with no subclass
            #    return hop.gendirectcall(rclass.ll_isinstance_exact, v_obj, v_cls)
            #else:
            minid = hop.inputconst(Signed, cls.subclassrange_min)
            maxid = hop.inputconst(Signed, cls.subclassrange_max)
            return hop.gendirectcall(ll_isinstance_const, v_obj, minid, maxid)
        else:
            return hop.gendirectcall(ll_isinstance, v_obj, v_cls)


def buildinstancerepr(rtyper, classdef, gcflavor='gc'):
    if classdef is None:
        unboxed = []
        virtualizable = False
    else:
        unboxed = [subdef for subdef in classdef.getallsubdefs()
                          if subdef.classdesc.pyobj is not None and
                             issubclass(subdef.classdesc.pyobj, UnboxedValue)]
        virtualizable = classdef.classdesc.read_attribute('_virtualizable_',
                                                          Constant(False)).value
    if virtualizable:
        assert len(unboxed) == 0
        assert gcflavor == 'gc'
        from pypy.rpython.lltypesystem import rvirtualizable
        return rvirtualizable.VirtualizableInstanceRepr(rtyper, classdef)
    elif len(unboxed) == 0:
        return InstanceRepr(rtyper, classdef, gcflavor)
    else:
        # the UnboxedValue class and its parent classes need a
        # special repr for their instances
        if len(unboxed) != 1:
            raise TyperError("%r has several UnboxedValue subclasses" % (
                classdef,))
        assert gcflavor == 'gc'
        from pypy.rpython.lltypesystem import rtagged
        return rtagged.TaggedInstanceRepr(rtyper, classdef, unboxed[0])


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

    def rtype_is_((r_ins1, r_ins2), hop):
        if r_ins1.gcflavor != r_ins2.gcflavor:
            # obscure logic, the is can be true only if both are None
            v_ins1, v_ins2 = hop.inputargs(r_ins1.common_repr(), r_ins2.common_repr())
            return hop.gendirectcall(ll_both_none, v_ins1, v_ins2)
        if r_ins1.classdef is None or r_ins2.classdef is None:
            basedef = None
        else:
            basedef = r_ins1.classdef.commonbase(r_ins2.classdef)
        r_ins = getinstancerepr(r_ins1.rtyper, basedef, r_ins1.gcflavor)
        return pairtype(Repr, Repr).rtype_is_(pair(r_ins, r_ins), hop)

    rtype_eq = rtype_is_

    def rtype_ne(rpair, hop):
        v = rpair.rtype_eq(hop)
        return hop.genop("bool_not", [v], resulttype=Bool)

#
# _________________________ Conversions for CPython _________________________

# part I: wrapping, destructor, preserving object identity

def call_destructor(thing, repr):
    ll_call_destructor(thing, repr)

def ll_call_destructor(thang, repr):
    return 42 # will be mapped

class Entry(ExtRegistryEntry):
    _about_ = ll_call_destructor
    s_result_annotation = None

    def specialize_call(self, hop):
        v_inst, c_spec = hop.inputargs(*hop.args_r)
        repr = c_spec.value
        if repr.has_wrapper:
            null = hop.inputconst(Ptr(PyObject), nullptr(PyObject))
            # XXX this bare_setfield is needed because we cannot do refcount operations
            # XXX on a dead object. Actually this is an abuse. Instead,
            # XXX we should consider a different operation for 'uninitialized fields'
            repr.setfield(v_inst, '_wrapper_', null, hop.llops,
                          opname='bare_setfield')
        hop.genop('gc_unprotect', [v_inst])


def create_pywrapper(thing, repr):
    return ll_create_pywrapper(thing, repr)

def ll_create_pywrapper(thing, repr):
    return 42

def into_cobject(v_inst, repr, llops):
    llops.genop('gc_protect', [v_inst])
    ARG = repr.lowleveltype
    reprPBC = llops.rtyper.annotator.bookkeeper.immutablevalue(repr)
    fp_dtor = llops.rtyper.annotate_helper_fn(call_destructor, [ARG, reprPBC])
    FUNC = FuncType([ARG, Void], Void)
    c_dtor = inputconst(Ptr(FUNC), fp_dtor)
    return llops.gencapicall('PyCObject_FromVoidPtr', [v_inst, c_dtor], resulttype=pyobj_repr)

def outof_cobject(v_obj, repr, llops):
    v_inst = llops.gencapicall('PyCObject_AsVoidPtr', [v_obj], resulttype=repr)
    llops.genop('gc_protect', [v_inst])
    return v_inst

class Entry(ExtRegistryEntry):
    _about_ = ll_create_pywrapper
    s_result_annotation = annmodel.SomePtr(Ptr(PyObject))

    def specialize_call(self, hop):
        v_inst, c_spec = hop.inputargs(*hop.args_r)
        repr = c_spec.value
        v_res = into_cobject(v_inst, repr, hop.llops)
        v_cobj = v_res
        c_cls = hop.inputconst(pyobj_repr, repr.classdef.classdesc.pyobj)
        c_0 = hop.inputconst(Signed, 0)
        v_res = hop.llops.gencapicall('PyType_GenericAlloc', [c_cls, c_0],
                                      resulttype=pyobj_repr)
        c_self = hop.inputconst(pyobj_repr, '__self__')
        hop.genop('setattr', [v_res, c_self, v_cobj], resulttype=pyobj_repr)
        if repr.has_wrapper:
            repr.setfield(v_inst, '_wrapper_', v_res, hop.llops)
            hop.genop('gc_unprotect', [v_res]) # yes a weak ref
        return v_res


def fetch_pywrapper(thing, repr):
    return ll_fetch_pywrapper(thing, repr)

def ll_fetch_pywrapper(thing, repr):
    return 42

class Entry(ExtRegistryEntry):
    _about_ = ll_fetch_pywrapper
    s_result_annotation = annmodel.SomePtr(Ptr(PyObject))

    def specialize_call(self, hop):
        v_inst, c_spec = hop.inputargs(*hop.args_r)
        repr = c_spec.value
        if repr.has_wrapper:
            return repr.getfield(v_inst, '_wrapper_', hop.llops)
        else:
            null = hop.inputconst(Ptr(PyObject), nullptr(PyObject))
            return null


def ll_wrap_object(obj, repr):
    ret = fetch_pywrapper(obj, repr)
    if not ret:
        ret = create_pywrapper(obj, repr)
    return ret

class __extend__(pairtype(InstanceRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        c_repr = inputconst(Void, r_from)
        if r_from.has_wrapper:
            return llops.gendirectcall(ll_wrap_object, v, c_repr)
        else:
            return llops.gendirectcall(create_pywrapper, v, c_repr)

# part II: unwrapping, creating the instance

class __extend__(pairtype(PyObjRepr, InstanceRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_to.has_wrapper:
            init, context = llops.rtyper.get_wrapping_hint(r_to.classdef)
            if context is init:
                # saving an extra __new__ method, we create the instance on __init__
                v_inst = r_to.new_instance(llops)
                v_cobj = into_cobject(v_inst, r_to, llops)
                c_self = inputconst(pyobj_repr, '__self__')
                llops.genop('setattr', [v, c_self, v_cobj], resulttype=pyobj_repr)
                r_to.setfield(v_inst, '_wrapper_', v, llops)
                llops.genop('gc_unprotect', [v])
                return v_inst
        # if we don't have a wrapper field, we just don't support __init__
        c_self = inputconst(pyobj_repr, '__self__')
        v = llops.genop('getattr', [v, c_self], resulttype=r_from)
        return outof_cobject(v, r_to, llops)

# ____________________________________________________________
#
#  Low-level implementation of operations on classes and instances

# doesn't work for non-gc stuff!
def ll_cast_to_object(obj):
    return cast_pointer(OBJECTPTR, obj)

# doesn't work for non-gc stuff!
def ll_type(obj):
    return cast_pointer(OBJECTPTR, obj).typeptr

def ll_issubclass(subcls, cls):
    return cls.subclassrange_min <= subcls.subclassrange_min <= cls.subclassrange_max

def ll_issubclass_const(subcls, minid, maxid):
    return minid <= subcls.subclassrange_min <= maxid


def ll_isinstance(obj, cls): # obj should be cast to OBJECT or NONGCOBJECT
    if not obj:
        return False
    obj_cls = obj.typeptr
    return ll_issubclass(obj_cls, cls)

def ll_isinstance_const(obj, minid, maxid):
    if not obj:
        return False
    return ll_issubclass_const(obj.typeptr, minid, maxid)

def ll_isinstance_exact(obj, cls):
    if not obj:
        return False
    obj_cls = obj.typeptr
    return obj_cls == cls

def ll_runtime_type_info(obj):
    return obj.typeptr.rtti

def ll_inst_hash(ins):
    if not ins:
        return 0    # for None
    cached = ins.hash_cache
    if cached == 0:
       cached = ins.hash_cache = intmask(id(ins))
    return cached

def ll_inst_type(obj):
    if obj:
        return obj.typeptr
    else:
        # type(None) -> NULL  (for now)
        return nullptr(typeOf(obj).TO.typeptr.TO)

def ll_both_none(ins1, ins2):
    return not ins1 and not ins2

# ____________________________________________________________

_missing = object()

def fishllattr(inst, name, default=_missing):
    p = widest = lltype.normalizeptr(inst)
    while True:
        try:
            return getattr(p, 'inst_' + name)
        except AttributeError:
            pass
        try:
            p = p.super
        except AttributeError:
            break
    if default is _missing:
        raise AttributeError("%s has no field %s" % (lltype.typeOf(widest),
                                                     name))
    return default

def feedllattr(inst, name, llvalue):
    p = widest = lltype.normalizeptr(inst)
    while True:
        try:
            return setattr(p, 'inst_' + name, llvalue)
        except AttributeError:
            pass
        try:
            p = p.super
        except AttributeError:
            break
    raise AttributeError("%s has no field %s" % (lltype.typeOf(widest),
                                                 name))
