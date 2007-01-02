
""" External objects registry,
"""

from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Variable, Constant
from pypy.rpython.ootypesystem import ootype
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.rpython.lltypesystem.lltype import frozendict, isCompatibleType
from types import MethodType
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.ootypesystem.extdesc import MethodDesc, ArgDesc

class CallableEntry(ExtRegistryEntry):
    _type_ = MethodDesc
    
    def compute_annotation(self):
        # because we have no good annotation
        # let's cheat a little bit for a while...
        bookkeeper = getbookkeeper()
        # hack, hack, hack, hack, hack, hack, hack, hack, hack, hack, hack,
        values = ["v%d"%i for i in xrange(len(self.instance.args))]
        lb = eval("lambda %s: None" % ",".join(values))
        return annmodel.SomePBC([bookkeeper.getdesc(lb)])

class BasicMetaExternal(type):
    def _is_compatible(type2):
        return type(type2) is BasicMetaExternal
    
    def __new__(self, _name, _type, _vars):
        retval = type.__new__(self, _name, _type, _vars)
        if not retval._methods:
            retval._methods = {}
        for name, var in _vars.iteritems():
            if hasattr(var, '_method'):
                meth_name, desc = var._method
                retval._methods[meth_name] = desc
        return retval
    
    _is_compatible = staticmethod(_is_compatible)

class BasicExternal(object):
    __metaclass__ = BasicMetaExternal
    __self__ = None
    
    _fields = {}
    _methods = {}
    
    def described(retval=None, args={}):
        def decorator(func):
            code = func.func_code
            if not func.func_defaults:
                defs = []
            else:
                defs = func.func_defaults
            
            assert(code.co_argcount < len(defs) + len(args), "Not enough information for describing method")
            
            for arg in xrange(1, code.co_argcount - len(defs)):
                assert code.co_varnames[arg] in args, "Don't have example for arg %s" % code.co_varnames[arg]
            
            arg_pass = []
            start_pos = code.co_argcount - len(defs)
            for arg in xrange(1, code.co_argcount):
                varname = code.co_varnames[arg]
                if varname in args:
                    arg_pass.append((varname, args[varname]))
                else:
                    arg_pass.append((varname, defs[arg - start_pos]))
            func._method = (func.__name__, MethodDesc(arg_pass, retval))
            return func
        return decorator
    
    described = staticmethod(described)

described = BasicExternal.described

class Analyzer(object):
    def __init__(self, name, value, s_retval, s_args):
        self.name = name
        self.args, self.retval = value.args, value.retval
        self.s_retval = s_retval
        self.s_args = s_args
        self.value = value
    
    def __call__(self, *args):
        for i in args:
            if isinstance(i, annmodel.SomePBC):
                bookkeeper = getbookkeeper()
                bookkeeper.pbc_call(i, bookkeeper.build_args("simple_call", (self.s_retval,)))
        return self.s_retval

class ExternalType(ootype.OOType):
    class_dict = {}
    __name__ = "ExternalType"

    def __init__(self, _class):
        self._class_ = _class
        self._name = str(_class)
        self._superclass = None
        self._root = True
        self.updated = False
        self._data = frozendict(_class._fields), frozendict(_class._methods)
    
    def update_fields(self, _fields):
        for i, val in _fields.iteritems():
            self._fields[i] = getbookkeeper().annotation_from_example(val)
    
    def _is_compatible(type2):
        return type(type2) is ExternalType
    
    _is_compatible = staticmethod(_is_compatible)
    
    def update_methods(self, _methods):
        _signs = {}
        self._fields = {}
        for i, val in _methods.iteritems():
            retval = getbookkeeper().annotation_from_example(val.retval.example)
            values = [arg.example for arg in val.args]
            s_args = [getbookkeeper().annotation_from_example(j) for j in values]
            _signs[i] = MethodDesc(tuple(s_args), retval)
            next = annmodel.SomeBuiltin(Analyzer(i, val, retval, s_args), s_self = annmodel.SomeExternalBuiltin(self), methodname = i)
            next.const = True
            self._fields[i] = next
        self._methods = frozendict(_signs)

    def __hash__(self):
        # FIXME: for now
        return hash(self._name)
    
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
    
    def _defl(self):
        return _external_type(self)
        
class _external_type(object):
    
    def __init__(self, et):
        self._TYPE = et

class Entry_basicexternalmeta(ExtRegistryEntry):
    _metatype_ = BasicMetaExternal
    
    def compute_annotation(self):
        return annmodel.SomeExternalBuiltin(self.bookkeeper.getexternaldesc\
            (self.instance.__class__))
        #return annmodel.SomeExternalBuiltin(ExternalType.get(self.instance.__class__))
    
    def get_field_annotation(self, ext_obj, attr):
        return ext_obj.get_field(attr)
    
    def get_arg_annotation(self, ext_obj, attr):
        field = ext_obj._class_._fields[attr]
        assert isinstance(field, MethodDesc)
        return [getbookkeeper().annotation_from_example(arg.example) for arg in field.args]
    
    def set_field_annotation(self, ext_obj, attr, s_val):
        ext_obj.set_field(attr, s_val)

class Entry_basicexternal(ExtRegistryEntry):
    _type_ = BasicExternal.__metaclass__
    
    def compute_result_annotation(self):
        return annmodel.SomeExternalBuiltin(self.bookkeeper.getexternaldesc(self.instance))
    
    def specialize_call(self, hop):
        value = hop.r_result.lowleveltype
        return hop.genop('new', [Constant(value, concretetype=ootype.Void)], \
            resulttype = value)

#def rebuild_basic_external():
#    ExternalType.class_dict = {}
