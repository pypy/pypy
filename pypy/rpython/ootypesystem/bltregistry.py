
""" External objects registry, defining two types of object:
1. Those who need to be flown normally, but needs different representation in the backend
2. Those who does not need to be flown
"""

from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Variable, Constant
from pypy.rpython.ootypesystem import ootype

class BasicMetaExternal(type):
    pass

class BasicExternal(object):
    __metaclass__ = BasicMetaExternal
    
    _fields = {}
    _methods = {}

from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rmodel import Repr


class ExternalType(ootype.Instance):
    class_dict = {}
    
    def __init__(self, _class):
        # FIXME: We want to support inheritance at some point
        self._class_ = _class
        _methods = dict([(i,ootype._meth(ootype.Meth(*val))) for i,val in _class._methods.iteritems()])
        ootype.Instance.__init__(self, str(_class), None, _class._fields, _methods, True)
    
##    def _example(self):
##        return ootype._instance(self)

    def get(class_):
        try:
            return ExternalType.class_dict[class_]
        except KeyError:
            next = ExternalType(class_)
            ExternalType.class_dict[class_] = next
            return next

    get = staticmethod(get)
    
##    def _init_instance(self, inst):
##        for i,val in self._fields.iteritems():
##            inst.__dict__[i] = val
##    
##    def _lookup(self, name):
##        return self, None
##    
##    def _lookup_field(self, name):
##        return self, self.fields.get(name)
##    
##    def _has_field(self, name):
##        return self._fields.get(name) is not None
##    
##    def _field_type(self, name):
##        return self._fields[name]
##    
##    def _check_field(self, name):
##        return True
##    
##    def __repr__(self):
##        return "<Externaltype%r>" % self._class
##    
##    def __str__(self):
##        return "ExternalType(%s)" % self._class

##class ExternalInstance(ootype.OOType):
##    pass
##
##ExternalInstanceSingleton = ExternalInstance()

class Entry_basicexternal(ExtRegistryEntry):
    _type_ = BasicExternal.__metaclass__
    
    #def compute_annotation(self, *args):
    #    return annmodel.SomeOOInstance(ootype=BasicExternal)
    def compute_result_annotation(self):
        return annmodel.SomeOOInstance(ootype=ExternalType.get(self.instance))
    
    def specialize_call(self, hop):
        #assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)\
        #       and hop.args_s[0].ootype is Externaltype
        #import pdb; pdb.set_trace()
        _class = hop.r_result.lowleveltype._class_
        return hop.genop('new', [Constant(ExternalType.get(_class), concretetype=ootype.Void)], \
            resulttype = ExternalType.get(_class))
