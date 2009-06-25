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

    def __getattr__(self, name):
        if name.startswith('getset') and 'getsets' not in self.__dict__:
            try:
                self.prepare_getsets()
            except AttributeError, e:
                raise Exception("AttributeError: %s" % e)
            return getattr(self, name)
        else:
            raise AttributeError("%s object has no attribute %r" % (
                self.__class__.__name__, name))

    def prepare_getsets(self):
        raise NotImplementedError

    def _freeze_(self):
        return True


class AbstractVirtualizable2InstanceRepr(AbstractInstanceRepr):

    VirtualizableAccessor = AbstractVirtualizableAccessor

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

    def _setup_repr_llfields(self):
        raise NotImplementedError

    def set_vable(self, llops, vinst, force_cast=False):
        raise NotImplementedError

    def get_field(self, attr):
        raise NotImplementedError

    def _setup_repr(self):
        if self.top_of_virtualizable_hierarchy:
            hints = {'virtualizable2_accessor': self.accessor}
            llfields = self._setup_repr_llfields()
            if llfields:
                self._super()._setup_repr(llfields, hints = hints)
            else:
                self._super()._setup_repr(hints = hints)
            my_redirected_fields = []
            self.my_redirected_fields = {}
            c_vfields = self.classdef.classdesc.classdict['_virtualizable2_']
            for name in c_vfields.value:
                if name.endswith('[*]'):
                    name = name[:-3]
                    suffix = '[*]'
                else:
                    suffix = ''
                mangled_name, r = self.get_field(name)
                my_redirected_fields.append(mangled_name + suffix)
                self.my_redirected_fields[mangled_name] = True
            self.accessor.initialize(self.object_type, my_redirected_fields)
        else:
            self.my_redirected_fields = {}
            self._super()._setup_repr()

    def new_instance(self, llops, classcallhop=None):
        vptr = self._super().new_instance(llops, classcallhop)
        self.set_vable(llops, vptr)
        return vptr

    def hook_access_field(self, vinst, cname, llops, flags):
        if not flags.get('access_directly'):
            if cname.value in self.my_redirected_fields:
                llops.genop('promote_virtualizable', [vinst, cname])
