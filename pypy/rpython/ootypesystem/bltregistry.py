
""" External objects registry, defining two types of object:
1. Those who need to be flown normally, but needs different representation in the backend
2. Those who does not need to be flown
"""

from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Variable, Constant
from pypy.rpython.ootypesystem import ootype
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.rpython.lltypesystem.lltype import frozendict, isCompatibleType
from types import MethodType

class ArgDesc(object):
    def __init__(self, name, ex_value):
        self.name = name
        self.example = ex_value

class MethodDesc(object):
    def __init__(self, args, retval):
        self.num = 0
        self.args = [self.convert_val(arg) for arg in args]
        self.retval = self.convert_val(retval)
    
    def convert_val(self, val):
        if isinstance(val, ArgDesc):
            return val
        elif isinstance(val, tuple):
            return ArgDesc(*val)
        else:
            self.num += 1
            return ArgDesc('v%d' % (self.num-1), val)

class BasicMetaExternal(type):
    def _is_compatible(type2):
        return type(type2) is BasicMetaExternal
    
    _is_compatible = staticmethod(_is_compatible)

class BasicExternal(object):
    __metaclass__ = BasicMetaExternal
    __self__ = None
    
    _fields = {}
    _methods = {}

from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rmodel import Repr

class Analyzer(object):
    def __init__(self, name, value):
        self.name = name
        self.args, self.retval = [i.example for i in value.args], value.retval.example
    
    def __call__(self, *args):
        #for i in xrange(len(args)):
        #    assert getbookkeeper().valueoftype(self.args[i]).contains(args[i])
        #if self.retval is None:
        #    return None
        ann_retval = getbookkeeper().annotation_from_example(self.retval)
        
        for i in args:
            if isinstance(i, annmodel.SomePBC):
                bookkeeper = getbookkeeper()
                bookkeeper.pbc_call(i, bookkeeper.build_args("simple_call", (ann_retval,)))
        return ann_retval

class ExternalType(ootype.OOType):
    class_dict = {}
    __name__ = "ExternalType"

    def __init__(self, _class):
        # FIXME: We want to support inheritance at some point
        self._class_ = _class
        self._name = str(_class)
        self._superclass = None
        self._root = True
        self._fields = {}
        self.updated = False
        self._data = _class._fields, _class._methods
        #self._methods = _class._methods
        #_methods = dict([(i,ootype._meth(ootype.Meth(*val))) for i,val in _class._methods.iteritems()])
        #ootype.Instance.__init__(self, str(_class), None, _class._fields, _methods, True)
        #self.attr = {}
    
    def update_fields(self, _fields):
        for i, val in _fields.iteritems():
            self._fields[i] = getbookkeeper().annotation_from_example(val)
    
    def _is_compatible(type2):
        return type(type2) is ExternalType
    
    _is_compatible = staticmethod(_is_compatible)
    
    def update_methods(self, _methods):
        _signs = {}
        for i, val in _methods.iteritems():
            retval = getbookkeeper().annotation_from_example(val.retval.example)
            values = [arg.example for arg in val.args]
            _signs[i] = MethodDesc(tuple([getbookkeeper().annotation_from_example(j) for j in values]), retval)
            next = annmodel.SomeBuiltin(Analyzer(i, val), s_self = annmodel.SomeExternalBuiltin(self), methodname = i)
            next.const = True
            self._fields[i] = next
        self._methods = frozendict(_signs)
    
    def get(class_):
        try:
            return ExternalType.class_dict[class_]
        except KeyError:
            next = ExternalType(class_)
            ExternalType.class_dict[class_] = next
            return next
    
    def set_field(self, attr, knowntype):
        self.check_update()
        self._fields[attr] = knowntype
        
    def check_update(self):
        if not self.updated:
            _fields, _methods = self._data
            self.update_methods(_methods)
            self.update_fields(_fields)
            self.updated = True
            self._fields = frozendict(self._fields)
            del self._data
    
    def get_field(self, attr):
        self.check_update()
        return self._fields[attr]
    
    def find_method(self, meth):
        raise NotImplementedError()
    
    def __repr__(self):
        return "%s %s" % (self.__name__, self._name)
        
##    def _defl(self):
##        raise AttributeError()
##        return self._null
##
##    def _example(self):
##        raise AttributeError()return new(self)
##    
    get = staticmethod(get)
    
class _external_type(object):
    
    def __init__(self, et):
        self._TYPE = et

class Entry_basicexternalmeta(ExtRegistryEntry):
    _metatype_ = BasicMetaExternal
    
    def compute_annotation(self):
        return annmodel.SomeExternalBuiltin(ExternalType.get(self.instance.__class__))
    
    def get_field_annotation(self, ext_obj, attr):
        return ext_obj.get_field(attr)
    
    def set_field_annotation(self, ext_obj, attr, s_val):
        ext_obj.set_field(attr, s_val)

class Entry_basicexternal(ExtRegistryEntry):
    _type_ = BasicExternal.__metaclass__
    
    #def compute_annotation(self, *args):
    #    return annmodel.SomeOOInstance(ootype=BasicExternal)
    
    def compute_result_annotation(self):
        return annmodel.SomeExternalBuiltin(ExternalType.get(self.instance))
        #Ereturn annmodel.SomeOOInstance(ExternalType.get(self.instance))
    
    def specialize_call(self, hop):
        #assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)\
        #       and hop.args_s[0].ootype is Externaltype
        _class = hop.r_result.lowleveltype._class_
        return hop.genop('new', [Constant(ExternalType.get(_class), concretetype=ootype.Void)], \
            resulttype = ExternalType.get(_class))
