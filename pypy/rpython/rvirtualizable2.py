import py
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.rclass import InstanceRepr
from pypy.rpython.lltypesystem.rvirtualizable import VABLERTIPTR


class VirtualizableAccessor(object):

    def initialize(self, STRUCT, redirected_fields, PARENT=None):
        self.STRUCT = STRUCT
        self.redirected_fields = redirected_fields
        self.subaccessors = []
        if PARENT is None:
            self.parent = None
        else:
            self.parent = PARENT.access
            self.parent.subaccessors.append(self)

    def __repr__(self):
        return '<VirtualizableAccessor for %s>' % getattr(self, 'STRUCT', '?')

    def __getattr__(self, name):
        if name.startswith('getset') and 'getsets' not in self.__dict__:
            self.prepare_getsets()
            return getattr(self, name)
        else:
            raise AttributeError("%s object has no attribute %r" % (
                self.__class__.__name__, name))

    def prepare_getsets(self):
        self.getsets = {}
        STRUCT = self.STRUCT
        for fieldname in self.redirected_fields:
            FIELDTYPE = getattr(STRUCT, fieldname)
            GETTER = lltype.FuncType([lltype.Ptr(STRUCT)], FIELDTYPE)
            SETTER = lltype.FuncType([lltype.Ptr(STRUCT), FIELDTYPE],
                                     lltype.Void)
            VABLE_GETSET = lltype.Struct('vable_getset',
                                         ('get', lltype.Ptr(GETTER)),
                                         ('set', lltype.Ptr(SETTER)),
                                         hints={'immutable': True})
            getset = lltype.malloc(VABLE_GETSET, flavor='raw', zero=False)
            # as long as no valid pointer has been put in the structure
            # by the JIT, accessing the fields should raise, in order
            # to prevent constant-folding
            py.test.raises(lltype.UninitializedMemoryAccess, "getset.get")
            py.test.raises(lltype.UninitializedMemoryAccess, "getset.set")
            self.getsets[fieldname] = getset
            setattr(self, 'getset_' + fieldname, getset)

    def _freeze_(self):
        return True


class Virtualizable2InstanceRepr(InstanceRepr):

    def __init__(self, rtyper, classdef):
        InstanceRepr.__init__(self, rtyper, classdef)
        classdesc = classdef.classdesc
        if '_virtualizable2_' in classdesc.classdict:
            basedesc = classdesc.basedesc
            assert basedesc is None or basedesc.lookup('_virtualizable2_') is None
            self.top_of_virtualizable_hierarchy = True
        else:
            self.top_of_virtualizable_hierarchy = False
        try:
            self.virtuals = tuple(classdesc.classdict['_always_virtual_'].value)
        except KeyError:
            self.virtuals = ()
        self.accessor = VirtualizableAccessor()

    def _setup_repr(self):
        llfields = []
        if self.top_of_virtualizable_hierarchy:
            llfields.append(('vable_base', llmemory.Address))
            llfields.append(('vable_rti', VABLERTIPTR))
        InstanceRepr._setup_repr(self, llfields,
                                 hints = {'virtualizable2': True,
                                          'virtuals' : self.virtuals},
                                 adtmeths = {'access': self.accessor})
        my_redirected_fields = []
        for _, (mangled_name, _) in self.fields.items():
            my_redirected_fields.append(mangled_name)
        self.my_redirected_fields = dict.fromkeys(my_redirected_fields)    
        if self.top_of_virtualizable_hierarchy:
            self.accessor.initialize(self.object_type, my_redirected_fields)
        else:
            self.accessor.initialize(self.object_type, my_redirected_fields,
                                     self.rbase.lowleveltype.TO)

    def set_vable(self, llops, vinst, force_cast=False):
        if self.top_of_virtualizable_hierarchy:
            if force_cast:
                vinst = llops.genop('cast_pointer', [vinst], resulttype=self)
            cname = inputconst(lltype.Void, 'vable_rti')
            vvalue = inputconst(VABLERTIPTR, lltype.nullptr(VABLERTIPTR.TO))
            llops.genop('setfield', [vinst, cname, vvalue])
        else:
            self.rbase.set_vable(llops, vinst, force_cast=True)

    def new_instance(self, llops, classcallhop=None):
        vptr = InstanceRepr.new_instance(self, llops, classcallhop)
        self.set_vable(llops, vptr)
        return vptr

    def getfield(self, vinst, attr, llops, force_cast=False, flags={}):
        """Read the given attribute (or __class__ for the type) of 'vinst'."""
        if not flags.get('access_directly') and attr in self.fields:
            mangled_name, r = self.fields[attr]
            if mangled_name in self.my_redirected_fields:
                if force_cast:
                    vinst = llops.genop('cast_pointer', [vinst],
                                        resulttype=self)
                c_name = inputconst(lltype.Void, mangled_name)
                llops.genop('promote_virtualizable', [vinst, c_name])
                return llops.genop('getfield', [vinst, c_name], resulttype=r)
        return InstanceRepr.getfield(self, vinst, attr, llops, force_cast)

    def setfield(self, vinst, attr, vvalue, llops, force_cast=False,
                 flags={}):
        """Write the given attribute (or __class__ for the type) of 'vinst'."""
        if not flags.get('access_directly') and attr in self.fields:
            mangled_name, r = self.fields[attr]
            if mangled_name in self.my_redirected_fields:
                if force_cast:
                    vinst = llops.genop('cast_pointer', [vinst],
                                        resulttype=self)
                c_name = inputconst(lltype.Void, mangled_name)
                llops.genop('promote_virtualizable', [vinst, c_name])
                llops.genop('setfield', [vinst, c_name, vvalue])
                return
        InstanceRepr.setfield(self, vinst, attr, vvalue, llops, force_cast)
