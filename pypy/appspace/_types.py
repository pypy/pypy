"""
Definition of the standard Python types.
"""

from sys import pypy
import __builtin__
import _types

__all__ = ['BooleanType', 'BufferType', 'BuiltinFunctionType',
           'BuiltinMethodType', 'ClassType', 'CodeType', 'ComplexType',
           'DictProxyType', 'DictType', 'DictionaryType', 'EllipsisType',
           'FileType', 'FloatType', 'FrameType', 'FunctionType',
           'GeneratorType', 'InstanceType', 'IntType', 'LambdaType',
           'ListType', 'LongType', 'MethodType', 'ModuleType', 'NoneType',
           'NotImplementedType', 'ObjectType', 'SliceType', 'StringType',
           'TracebackType', 'TupleType', 'TypeType', 'UnboundMethodType',
           'UnicodeType', 'XRangeType']

def _register(factory, cls, in_builtin=True, synonym=True):
    """
    Register factory as type cls. 
    
    If in_builtin is a true value (which is the default), also
    register the type as a built-in. If the value of in_builtin
    is a string, use this name as the type name in the __builtin__
    module.
    
    If synonym is true (which is the default), also register the
    type in this very module under its synonym. If synonym is a
    string, use this string, else uppercase the class name and
    append the string "Type".
    """
    pypy.registertype(factory, cls)
    if in_builtin:
        if isinstance(in_builtin, str):
            typename = in_builtin
        else:
            typename = cls.__name__
        setattr(__builtin__, typename, cls)
    if synonym:
        if isinstance(synonym, str):
            typename = synonym
        else:
            typename = cls.__name__.title() + 'Type'
        setattr(_types, typename, cls)


class object:

    def __new__(cls):
        if cls is object:
            return pypy.ObjectFactory()
        else:
            return pypy.UserObjectFactory(cls, pypy.ObjectFactory)

    def __repr__(self):
        return '<%s object at 0x%x>' % (type(self).__name__, id(self))

_register(pypy.ObjectFactory, object)


class bool(object):

    def __new__(cls, *args):
        if cls is bool:
            return pypy.BoolObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.BoolObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.BoolObjectFactory, bool, synonym='BooleanType')


class buffer(object):

    def __new__(cls, *args):
        if cls is buffer:
            return pypy.BufferObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.BufferObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.BufferObjectFactory, buffer)


class builtin_function_or_method(object):

    def __new__(cls, *args):
        if cls is builtin_function_or_method:
            return pypy.Builtin_Function_Or_MethodObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls,
                     pypy.Builtin_Function_Or_MethodObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.Builtin_Function_Or_MethodObjectFactory,
          builtin_function_or_method, in_builtin=False,
          synonym='BuiltinFunctionType')

setattr(_types, 'BuiltinMethodType', builtin_function_or_method)


class classobj(object):

    def __new__(cls, *args):
        if cls is classobj:
            return pypy.ClassobjObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.ClassobjObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.ClassobjObjectFactory, classobj, in_builtin=False,
          synonym='ClassType')


class code(object):

    def __new__(cls, *args):
        if cls is code:
            return pypy.CodeObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.CodeObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.CodeObjectFactory, code, in_builtin=False)


class complex(object):

    def __new__(cls, *args):
        if cls is complex:
            return pypy.ComplexObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.ComplexObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.ComplexObjectFactory, complex)


class dictproxy(object):

    def __new__(cls, *args):
        if cls is dictproxy:
            return pypy.DictproxyObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.DictproxyObjectFactory,
                                          args)

    def __repr__(self):
        return str(self)

_register(pypy.DictproxyObjectFactory, dictproxy, in_builtin=False,
          synonym='DictProxyType')


class dict(object):

    def __new__(cls, *args):
        if cls is dict:
            return pypy.DictObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.DictObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.DictObjectFactory, dict)

setattr(_types, 'DictionaryType', dict)


class ellipsis(object):

    def __new__(cls, *args):
        if cls is ellipsis:
            return pypy.EllipsisObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.EllipsisObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.EllipsisObjectFactory, ellipsis, in_builtin=False)


class file(object):

    def __new__(cls, *args):
        if cls is file:
            return pypy.FileObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.FileObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.FileObjectFactory, file, in_builtin='open')


class float(object):

    def __new__(cls, *args):
        if cls is float:
            return pypy.FloatObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.FloatObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.FloatObjectFactory, float)


class frame(object):

    def __new__(cls, *args):
        if cls is frame:
            return pypy.FrameObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.FrameObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.FrameObjectFactory, frame, in_builtin=False)


class function(object):

    def __new__(cls, *args):
        if cls is function:
            return pypy.FunctionObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.FunctionObjectFactory, args)

    def __repr__(self):
        return str(self)

    # XXX find out details for builtin properties
    func_code    = pypy.builtin_property('fix')
    func_globals = pypy.builtin_property('me')

_register(pypy.FunctionObjectFactory, function, in_builtin=False)


class generator(object):

    def __new__(cls, *args):
        if cls is generator:
            return pypy.GeneratorObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.GeneratorObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.GeneratorObjectFactory, generator, in_builtin=False)


class instance(object):

    def __new__(cls, *args):
        if cls is instance:
            return pypy.InstanceObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.InstanceObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.InstanceObjectFactory, instance, in_builtin=False)


class int(object):

    def __new__(cls, *args):
        if cls is int:
            return pypy.IntObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.IntObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.IntObjectFactory, int)

setattr(_types, 'LambdaType', function)


class list(object):

    def __new__(cls, *args):
        if cls is list:
            return pypy.ListObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.ListObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.ListObjectFactory, list)


class long(object):

    def __new__(cls, *args):
        if cls is long:
            return pypy.LongObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.LongObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.LongObjectFactory, long)


class instancemethod(object):

    def __new__(cls, *args):
        if cls is instancemethod:
            return pypy.InstancemethodObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls,
                     pypy.InstancemethodObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.InstancemethodObjectFactory, instancemethod, in_builtin=False,
          synonym='MethodType')


class module(object):

    def __new__(cls, *args):
        if cls is module:
            return pypy.ModuleObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.ModuleObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.ModuleObjectFactory, module, in_builtin=False)


class NoneType(object):

    def __new__(cls, *args):
        if cls is NoneType:
            return pypy.NonetypeObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.NonetypeObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.NonetypeObjectFactory, NoneType, in_builtin=False,
          synonym='NoneType')


class NotImplementedType(object):

    def __new__(cls, *args):
        if cls is NotImplementedType:
            return pypy.NotimplementedtypeObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls,
                     pypy.NotimplementedtypeObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.NotimplementedtypeObjectFactory, NotImplementedType,
          in_builtin=False, synonym='NotImplementedType')


class slice(object):

    def __new__(cls, *args):
        if cls is slice:
            return pypy.SliceObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.SliceObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.SliceObjectFactory, slice)


class str(object):

    def __new__(cls, *args):
        if cls is str:
            return pypy.StrObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.StrObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.StrObjectFactory, str, synonym='StringType')


class traceback(object):

    def __new__(cls, *args):
        if cls is traceback:
            return pypy.TracebackObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.TracebackObjectFactory,
                                          args)

    def __repr__(self):
        return str(self)

_register(pypy.TracebackObjectFactory, traceback, in_builtin=False)


class tuple(object):

    def __new__(cls, *args):
        if cls is tuple:
            return pypy.TupleObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.TupleObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.TupleObjectFactory, tuple)


class type(object):

    def __new__(cls, *args):
        if cls is type:
            return pypy.TypeObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.TypeObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.TypeObjectFactory, type)

setattr(_types, 'UnboundMethodType', instancemethod)


class unicode(object):

    def __new__(cls, *args):
        if cls is unicode:
            return pypy.UnicodeObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.UnicodeObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.UnicodeObjectFactory, unicode)


class xrange(object):

    def __new__(cls, *args):
        if cls is xrange:
            return pypy.XrangeObjectFactory(args)
        else:
            return pypy.UserObjectFactory(cls, pypy.XrangeObjectFactory, args)

    def __repr__(self):
        return str(self)

_register(pypy.XrangeObjectFactory, xrange, synonym='XRangeType')



