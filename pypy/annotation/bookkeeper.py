"""
The Bookkeeper class.
"""

from types import FunctionType, ClassType, MethodType
from types import BuiltinMethodType
from pypy.annotation.model import *
from pypy.annotation.classdef import ClassDef
from pypy.interpreter.miscutils import getthreadlocals
from pypy.interpreter.pycode import CO_VARARGS
from pypy.tool.hack import func_with_new_name

class Bookkeeper:
    """The log of choices that have been made while analysing the operations.
    It ensures that the same 'choice objects' will be returned if we ask
    again during reflowing.  Like ExecutionContext, there is an implicit
    Bookkeeper that can be obtained from a thread-local variable.

    Currently used for factories and user-defined classes."""

    def __init__(self, annotator):
        self.annotator = annotator
        self.creationpoints = {} # map position-in-a-block to its Factory
        self.userclasses = {}    # map classes to ClassDefs
        self.userclasseslist = []# userclasses.keys() in creation order
        self.cachespecializations = {}
        self.pbccache = {}
        # import ordering hack
        global BUILTIN_ANALYZERS
        from pypy.annotation.builtin import BUILTIN_ANALYZERS

    def enter(self, position_key):
        """Start of an operation.
        The operation is uniquely identified by the given key."""
        self.position_key = position_key
        getthreadlocals().bookkeeper = self

    def leave(self):
        """End of an operation."""
        del getthreadlocals().bookkeeper
        del self.position_key

    def is_in_an_operation(self):
        return hasattr(self, 'position_key')

    def getfactory(self, factorycls):
        """Get the Factory associated with the current position,
        or build it if it doesn't exist yet."""
        try:
            factory = self.creationpoints[self.position_key]
        except KeyError:
            factory = factorycls()
            factory.bookkeeper = self
            factory.position_key = self.position_key
            self.creationpoints[self.position_key] = factory
        assert isinstance(factory, factorycls)
        return factory

    def getclassdef(self, cls):
        """Get the ClassDef associated with the given user cls."""
        if cls is object:
            return None
        try:
            return self.userclasses[cls]
        except KeyError:
            cdef = ClassDef(cls, self)
            self.userclasses[cls] = cdef
            self.userclasseslist.append(cdef)
            return self.userclasses[cls]


    def immutablevalue(self, x):
        """The most precise SomeValue instance that contains the
        immutable value x."""
        tp = type(x)
        if tp is bool:
            result = SomeBool()
        elif tp is int:
            result = SomeInteger(nonneg = x>=0)
        elif tp is str:
            result = SomeString()
        elif tp is tuple:
            result = SomeTuple(items = [self.immutablevalue(e) for e in x])
        elif tp is list:
            items_s = [self.immutablevalue(e) for e in x]
            result = SomeList({}, unionof(*items_s))
        elif tp is dict:   # exactly a dict
            items = {}
            for key, value in x.items():
                items[key] = self.immutablevalue(value)
            result = SomeDict({}, items)
        elif ishashable(x) and x in BUILTIN_ANALYZERS:
            result = SomeBuiltin(BUILTIN_ANALYZERS[x])
        elif callable(x) or isinstance(x, staticmethod): # XXX
            # maybe 'x' is a method bound to a not-yet-frozen cache?
            # fun fun fun.
            if (hasattr(x, 'im_self') and isinstance(x.im_self, Cache)
                and not x.im_self.frozen):
                x.im_self.freeze()
            if hasattr(x, '__self__') and x.__self__ is not None:
                s_self = self.immutablevalue(x.__self__)
                # stop infinite recursion getattr<->immutablevalue
                del s_self.const
                s_name = self.immutablevalue(x.__name__)
                result = s_self.getattr(s_name)
            else:
                return self.getpbc(x)
        elif hasattr(x, '__class__') \
                 and x.__class__.__module__ != '__builtin__':
            if isinstance(x, Cache) and not x.frozen:
                x.freeze()
            return self.getpbc(x)
        elif x is None:
            return self.getpbc(None)
        else:
            result = SomeObject()
        result.const = x
        return result

    def getpbc(self, x):
        try:
            # this is not just an optimization, but needed to avoid
            # infinitely repeated calls to add_source_for_attribute()
            return self.pbccache[x]
        except KeyError:
            result = SomePBC({x: True}) # pre-built inst
            clsdef = self.getclassdef(new_or_old_class(x))
            for attr in getattr(x, '__dict__', {}):
                clsdef.add_source_for_attribute(attr, x)
            self.pbccache[x] = result
            return result

    def valueoftype(self, t):
        """The most precise SomeValue instance that contains all
        objects of type t."""
        if t is bool:
            return SomeBool()
        elif t is int:
            return SomeInteger()
        elif t is str:
            return SomeString()
        elif t is list:
            return SomeList(factories={})
        # can't do dict, tuple
        elif isinstance(t, (type, ClassType)) and \
                 t.__module__ != '__builtin__':
            classdef = self.getclassdef(t)
            if self.is_in_an_operation():
                # woha! instantiating a "mutable" SomeXxx like
                # SomeInstance is always dangerous, because we need to
                # allow reflowing from the current operation if/when
                # the classdef later changes.
                classdef.instantiation_locations[self.position_key] = True
            return SomeInstance(classdef)
        else:
            o = SomeObject()
            o.knowntype = t
            return o

    def pycall(self, func, *args):
        if isinstance(func, (type, ClassType)) and \
            func.__module__ != '__builtin__':
            cls = func
            x = getattr(cls, "_specialize_", False)
            if x:
                if x == "location":
                    cls = self.specialize_by_key(cls, self.position_key)
                else:
                    raise Exception, \
                          "unsupported specialization type '%s'"%(x,)

            classdef = self.getclassdef(cls)
            classdef.instantiation_locations[self.position_key] = True 
            s_instance = SomeInstance(classdef)
            # flow into __init__() if the class has got one
            init = getattr(cls, '__init__', None)
            if init is not None and init != object.__init__:
                # don't record the access of __init__ on the classdef
                # because it is not a dynamic attribute look-up, but
                # merely a static function call
                if hasattr(init, 'im_func'):
                    init = init.im_func
                else:
                    assert isinstance(init, BuiltinMethodType)
                s_init = self.immutablevalue(init)
                s_init.simple_call(s_instance, *args)
            else:
                assert not args, "no __init__ found in %r" % (cls,)
            return s_instance
        if hasattr(func, '__call__') and \
           isinstance(func.__call__, MethodType):
            func = func.__call__
        if hasattr(func, 'im_func'):
            if func.im_self is not None:
                s_self = self.immutablevalue(func.im_self)
                args = [s_self] + list(args)
            try:
                func.im_func.class_ = func.im_class
            except AttributeError:
                # probably a builtin function, we don't care to preserve
                # class information then
                pass
            func = func.im_func
        assert isinstance(func, FunctionType), "expected function, got %r"%func
        # do we need to specialize this function in several versions?
        x = getattr(func, '_specialize_', False)
        #if not x: 
        #    x = 'argtypes'
        if x:
            if x == 'argtypes':
                key = short_type_name(args)
                func = self.specialize_by_key(func, key,
                                              func.__name__+'__'+key)
            elif x == "location":
                # fully specialize: create one version per call position
                func = self.specialize_by_key(func, self.position_key)
            else:
                raise Exception, "unsupported specialization type '%s'"%(x,)

        elif func.func_code.co_flags & CO_VARARGS:
            # calls to *arg functions: create one version per number of args
            func = self.specialize_by_key(func, len(args),
                                          name='%s__%d' % (func.func_name,
                                                           len(args)))
        return self.annotator.recursivecall(func, self.position_key, *args)

    def specialize_by_key(self, thing, key, name=None):
        key = thing, key
        try:
            thing = self.cachespecializations[key]
        except KeyError:
            if isinstance(thing, FunctionType):
                # XXX XXX XXX HAAAAAAAAAAAACK
                self.annotator.translator.getflowgraph(thing)
                thing = func_with_new_name(thing, name or thing.func_name)
            elif isinstance(thing, (type, ClassType)):
                assert not "not working yet"
                thing = type(thing)(name or thing.__name__, (thing,))
            else:
                raise Exception, "specializing %r?? why??"%thing
            self.cachespecializations[key] = thing
        return thing
        

def getbookkeeper():
    """Get the current Bookkeeper.
    Only works during the analysis of an operation."""
    return getthreadlocals().bookkeeper

def ishashable(x):
    try:
        hash(x)
    except TypeError:
        return False
    else:
        return True

def short_type_name(args):
    l = []
    for x in args:
        if isinstance(x, SomeInstance) and hasattr(x, 'knowntype'):
            name = "SI_" + x.knowntype.__name__
        else:
            name = x.__class__.__name__
        l.append(name)
    return "__".join(l)
