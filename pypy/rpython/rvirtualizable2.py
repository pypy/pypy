import py
from pypy.rpython.rmodel import inputconst
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rclass import AbstractInstanceRepr


class AbstractVirtualizableAccessor(object):

    def initialize(self, TYPE, redirected_fields):
        self.TYPE = TYPE
        self.redirected_fields = redirected_fields

    def __repr__(self):
        return '<VirtualizableAccessor for %s>' % getattr(self, 'TYPE', '?')

##    def __getattr__(self, name):
##        if name.startswith('getset') and 'getsets' not in self.__dict__:
##            self.prepare_getsets()
##            return getattr(self, name)
##        else:
##            raise AttributeError("%s object has no attribute %r" % (
##                self.__class__.__name__, name))

##    def prepare_getsets(self):
##        raise NotImplementedError

    def _freeze_(self):
        return True


class AbstractVirtualizable2InstanceRepr(AbstractInstanceRepr):

    VirtualizableAccessor = AbstractVirtualizableAccessor
##    op_getfield = None
##    op_setfield = None

    def _super(self):
        return super(AbstractVirtualizable2InstanceRepr, self)

    def __init__(self, rtyper, classdef):
        self._super().__init__(rtyper, classdef)
        classdesc = classdef.classdesc
        if '_virtualizable2_' in classdesc.classdict:
            basedesc = classdesc.basedesc
            assert basedesc is None or basedesc.lookup('_virtualizable2_') is None
            self.top_of_virtualizable_hierarchy = True
            self.accessor = self.VirtualizableAccessor()
        else:
            self.top_of_virtualizable_hierarchy = False

##    def _setup_instance_repr(self):
##        raise NotImplementedError

##    def gencast(self, llops, vinst):
##        raise NotImplementedError

##    def set_vable(self, llops, vinst, force_cast=False):
##        raise NotImplementedError

    def get_field(self, attr):
        raise NotImplementedError

##    def is_in_fields(self, attr):
##        raise NotImplementedError

    def _setup_repr(self):
        if self.top_of_virtualizable_hierarchy:
            hints = {'virtualizable2_accessor': self.accessor}
            self._super()._setup_repr(hints = hints)
            my_redirected_fields = []
            c_vfields = self.classdef.classdesc.classdict['_virtualizable2_']
            for name in c_vfields.value:
                if name.endswith('[*]'):
                    name = name[:-3]
                    suffix = '[*]'
                else:
                    suffix = ''
                mangled_name, r = self.get_field(name)
                my_redirected_fields.append(mangled_name + suffix)
            self.accessor.initialize(self.object_type, my_redirected_fields)
        else:
            self._super()._setup_repr()

##    def new_instance(self, llops, classcallhop=None):
##        vptr = self._super().new_instance(llops, classcallhop)
##        self.set_vable(llops, vptr)
##        return vptr

##    def getfield(self, vinst, attr, llops, force_cast=False, flags={}):
##        """Read the given attribute (or __class__ for the type) of 'vinst'."""
##        if not flags.get('access_directly') and self.is_in_fields(attr):
##            mangled_name, r = self.get_field(attr)
##            if mangled_name in self.my_redirected_fields:
##                if force_cast:
##                    vinst = self.gencast(llops, vinst)
##                c_name = inputconst(lltype.Void, mangled_name)
##                llops.genop('promote_virtualizable', [vinst, c_name])
##                return llops.genop(self.op_getfield, [vinst, c_name],
##                                   resulttype=r)
##        return self._super().getfield(vinst, attr, llops, force_cast)

##    def setfield(self, vinst, attr, vvalue, llops, force_cast=False,
##                 flags={}):
##        """Write the given attribute (or __class__ for the type) of 'vinst'."""
##        if not flags.get('access_directly') and self.is_in_fields(attr):
##            mangled_name, r = self.get_field(attr)
##            if mangled_name in self.my_redirected_fields:
##                if force_cast:
##                    vinst = self.gencast(llops, vinst)
##                c_name = inputconst(lltype.Void, mangled_name)
##                llops.genop('promote_virtualizable', [vinst, c_name])
##                llops.genop(self.op_setfield, [vinst, c_name, vvalue])
##                return
##        self._super().setfield(vinst, attr, vvalue, llops, force_cast)
