
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
from pypy.annotation.signature import annotation
from pypy.annotation.model import unionof

class CallableEntry(ExtRegistryEntry):
    _type_ = MethodDesc
    
    def compute_annotation(self):
        bookkeeper = getbookkeeper()
        args_s = [annotation(i._type) for i in self.instance.args]
        s_result = annotation(self.instance.result._type)
        return annmodel.SomeGenericCallable(args=args_s, result=s_result)

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

def typeof(val):
    """ Small wrapper, which tries to resemble example -> python type
    which can go to annotation path
    """
    if isinstance(val, list):
        return [typeof(val[0])]
    if isinstance(val, dict):
        return {typeof(val.keys()[0]):typeof(val.values()[0])}
    if isinstance(val, tuple):
        return tuple([typeof(i) for i in val])
    return type(val)

def load_dict_args(varnames, defs, args):
    argcount = len(varnames)
    assert(argcount < len(defs) + len(args), "Not enough information for describing method")
           
    for arg in xrange(1, argcount - len(defs)):
        assert varnames[arg] in args, "Don't have type for arg %s" % varnames[arg]

    arg_pass = []
    start_pos = argcount - len(defs)
    for arg in xrange(1, argcount):
        varname = varnames[arg]
        if varname in args:
            arg_pass.append((varname, args[varname]))
        else:
            arg_pass.append((varname, typeof(defs[arg - start_pos])))
    return arg_pass

class BasicExternal(object):
    __metaclass__ = BasicMetaExternal
    __self__ = None
    
    _fields = {}
    _methods = {}
    
    def described(retval=None, args={}):
        def decorator(func):
            if isinstance(args, dict):
                defs = func.func_defaults
                if defs is None:
                    defs = ()
                vars = func.func_code.co_varnames[:func.func_code.co_argcount]
                arg_pass = load_dict_args(vars, defs, args)
            else:
                assert isinstance(args, list)
                arg_pass = args
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
        args = args[1:]
        assert len(self.s_args) == len(args),\
            "Function %s expects %d arguments, got %d instead" % (self.name,
                                              len(self.s_args), len(args))
        for num, (arg, expected) in enumerate(zip(args, self.s_args)):
            res = unionof(arg, expected)
            assert expected.contains(res)
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
            self._fields[i] = annotation(val)
    
    def _is_compatible(type2):
        return type(type2) is ExternalType
    
    _is_compatible = staticmethod(_is_compatible)
    
    def update_methods(self, _methods):
        _signs = {}
        self._fields = {}
        for i, val in _methods.iteritems():
            retval = annotation(val.retval._type)
            values = [annotation(arg._type) for arg in val.args]
            s_args = [j for j in values]
            _signs[i] = MethodDesc(tuple(s_args), retval)
            next = annmodel.SomeBuiltin(Analyzer(i, val, retval, s_args), s_self = annmodel.SomeExternalBuiltin(self), methodname = i)
            next.const = True
            self._fields[i] = next
        self._methods = frozendict(_signs)

    def __hash__(self):
        return hash(self._name)
    
    def set_field(self, attr, knowntype):
        self.check_update()
        assert attr in self._fields
        field_ann = self._fields[attr]
        res = unionof(knowntype, field_ann)
        assert res.contains(knowntype)
    
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
        try:
            return self._fields[attr]
        except KeyError:
            from pypy.tool.error import NoSuchAttrError
            raise NoSuchAttrError("Basic external %s has no attribute %s" %
                                  (self._class_, attr))

    def find_method(self, meth):
        raise NotImplementedError()
    
    def __repr__(self):
        return "%s %s" % (self.__name__, self._name)
    
    def _defl(self):
        return _external_type(self, None)

class _external_type(object):
    
    def __init__(self, et, value):
        self._TYPE = et
        self.value = value

class Entry_basicexternalmeta(ExtRegistryEntry):
    _metatype_ = BasicMetaExternal
    
    def compute_annotation(self):
        return annmodel.SomeExternalBuiltin(self.bookkeeper.getexternaldesc\
            (self.type))
    
    def get_field_annotation(self, ext_obj, attr):
        return ext_obj.get_field(attr)
    
    #def get_arg_annotation(self, ext_obj, attr, s_pbc):
    #    s_field = ext_obj.get_field(attr)
    #    res = unionof(s_field, s_pbc)
    #    assert s_field.contains(res)
    #    return s_field.args_s
    
    def set_field_annotation(self, ext_obj, attr, s_val):
        ext_obj.set_field(attr, s_val)

class Entry_basicexternal(ExtRegistryEntry):
    _type_ = BasicExternal.__metaclass__
    
    def compute_result_annotation(self):
        if self.bookkeeper is None:
            return annmodel.SomeExternalBuiltin(ExternalType(self.instance))
        return annmodel.SomeExternalBuiltin(self.bookkeeper.getexternaldesc(self.instance))
    
    def specialize_call(self, hop):
        value = hop.r_result.lowleveltype
        return hop.genop('new', [Constant(value, concretetype=ootype.Void)], \
            resulttype = value)
