#
# Trivial object space for testing
# Does not perform any wrapping and (more importantly) does not
# correctly wrap the exceptions.
#

from pypy.interpreter import gateway
from pypy.interpreter.baseobjspace import *
from pypy.objspace.descroperation import DescrOperation, Object
from pypy.interpreter.argument import Arguments
import types, sys
import __builtin__ as cpy_builtin

class CPyWrapper(object):
    pass

class TrivialObjSpace(ObjSpace, DescrOperation):

    def clone_exception_hierarchy(self):
        def __init__(self, *args):
            self.args = args
        def __str__(self):
            l = len(self.args)
            if l == 0:
                return ''
            elif l == 1:
                return str(self.args[0])
            else:
                return str(self.args)
        import exceptions

        # to create types, we should call the standard type object;
        # but being able to do that depends on the existence of some
        # of the exceptions...
        
        self.w_Exception = type('Exception', (),
                                {'__init__':__init__, '__str__': __str__, 
                                 'originalex': Exception})
        
        done = {'Exception': self.w_Exception}

        # some of the complexity of the following is due to the fact
        # that we need to create the tree root first, but the only
        # connections we have go in the inconvenient direction...
        
        for k in dir(exceptions):
            if k not in done:
                v = getattr(exceptions, k)
                if not isinstance(v, type(Exception)):
                    continue
                if not issubclass(v, Exception):
                    continue
                stack = [k]
                while stack:
                    next = stack[-1]
                    if next not in done:
                        v = getattr(exceptions, next)
                        b = v.__bases__[0]
                        if b.__name__ not in done:
                            stack.append(b.__name__)
                            continue
                        else:
                            base = done[b.__name__]
                            newtype = type(next, (base,), {})
                            setattr(self, 'w_' + next, newtype)
                            newtype.originalex = v
                            done[next] = newtype
                            stack.pop()
                    else:
                        stack.pop()
        return done

    def initialize(self):
        from pypy.interpreter.typedef import TypeDef, GetSetProperty

        self.object_typedef = TypeDef('object', 
            __getattribute__ = gateway.interp2app(Object.descr__getattribute__.im_func),
            __setattr__ = gateway.interp2app(Object.descr__setattr__.im_func),
            __delattr__ = gateway.interp2app(Object.descr__delattr__.im_func),
            __str__ = gateway.interp2app(lambda space, w_x: space.repr(w_x)),
            __repr__ = gateway.interp2app(lambda space, w_x: repr(w_x)),
            __class__ = GetSetProperty(self.__class__.type),
            __init__ = gateway.interp2app(Object.descr__init__.im_func),
            __dict__ = GetSetProperty(self.__class__.getdict_or_complain),
            )
        # make a wrapped None object
        none_typedef = TypeDef('NoneType',
            __nonzero__ = gateway.interp2app(lambda space, w_None:
                                             space.w_False),
            __repr__ = gateway.interp2app(lambda space, w_None:
                                          space.wrap('None')))
        nonewrapperclass = self.hackwrapperclass(none_typedef)
        self.w_None = CPyWrapper.__new__(nonewrapperclass)
        instancedict = CPyWrapper.__dict__['__dict__'].__get__(self.w_None)
        instancedict['__internalpypyobject__'] = None

        self.w_True = True
        self.w_False = False
        self.w_NotImplemented = NotImplemented
        self.w_Ellipsis = Ellipsis
        newstuff = {"False": self.w_False,
                    "True" : self.w_True,
                    "NotImplemented" : self.w_NotImplemented,
                    "None" : self.w_None,
                    "Ellipsis" : self.w_Ellipsis,
                    "buffer": buffer,
                    #"xrange": xrange,
                    "slice": slice,
                    }
        for n, c in cpy_builtin.__dict__.iteritems():
            if n in ['xrange',  # we define this in builtin_app
                     'staticmethod',
                     'classmethod',
                     'property',
                     ]:
                continue
            if isinstance(c, types.TypeType):
                setattr(self, 'w_' + c.__name__, c)
                newstuff[c.__name__] = c
        newstuff.update(self.clone_exception_hierarchy())
        self.make_builtins(newstuff)

    # general stuff
    def wrap(self, x):
        if isinstance(x, BaseWrappable):
            x = x.__spacebind__(self)
            wrapperclass = self.hackwrapperclass(x.typedef)
            instance = CPyWrapper.__new__(wrapperclass)
            instancedict = CPyWrapper.__dict__['__dict__'].__get__(instance)
            instancedict['__internalpypyobject__'] = x
            return instance
        elif x is None:
            return self.w_None
        else:
            # optional check for double-wrapping
            if isinstance(x, CPyWrapper):
                raise TypeError, "wrapping an already-wrapped object"
            # grumble grumble grumble recursive wrapping grumble
            if isinstance(x, tuple):
                return tuple([self.wrap(y) for y in x])
            return x

    def unwrap(self, w):
        if isinstance(w, CPyWrapper):
            instancedict = CPyWrapper.__dict__['__dict__'].__get__(w)
            return instancedict['__internalpypyobject__']
        else:
            return w

    unwrap_builtin = unwrap

    def getdict(self, w_obj):
        if isinstance(w_obj, CPyWrapper):
            obj = self.unwrap(w_obj)
            return obj.getdict()
        else:
            try:
                return w_obj.__dict__
            except:
                self.reraise()

    def getdict_or_complain(self, w_obj):
        result = self.getdict(w_obj)
        if result is None:
            raise OperationError(self.w_AttributeError,
                                 self.wrap('no __dict__'))
        return result

    def allocate_instance(self, cls, w_subtype):
        raise NotImplementedError("cannot manually instantiate built-in types")

    def hackwrapperclass(self, typedef):
        try:
            return typedef.trivialwrapperclass
        except AttributeError:
            from pypy.interpreter.gateway import interp2app
            
            # make the base first
            if typedef.base:
                bases = (self.hackwrapperclass(typedef.base),)
            else:
                bases = (CPyWrapper,)
            # make the class dict with descriptors redirecting to the ones
            # in rawdict
            descrdict = {'__internalpypytypedef__': typedef}
            for descrname, descr in typedef.rawdict.items():
                if isinstance(descr, interp2app):
                    def make_stuff(descr=descr, descrname=descrname, space=self):
                        def stuff(w_obj, *args, **kwds):
                            fn = descr.get_function(space)
                            args = Arguments(space, list(args), kwds)
                            try:
                                return space.call_args(space.wrap(fn),
                                                       args.prepend(w_obj))
                            except OperationError, e:
                                if not hasattr(e.w_type, 'originalex'):
                                    raise # XXX
                                # XXX normalize ...
                                #if isinstance(e.w_value, e.w_type):
                                raise e.w_type.originalex(repr(e.w_value)) # e.w_value) 
                        return stuff
                    descrdict[descrname] = make_stuff()
                else:
                    # more generally, defining a property
                    def fget(w_obj, descr=descr, space=self):
                        w_descr = space.wrap(descr)
                        return space.get(w_descr, w_obj)
                    def fset(w_obj, w_value, descr=descr, space=self):
                        w_descr = space.wrap(descr)
                        return space.set(w_descr, w_obj, w_value)
                    def fdel(w_obj, descr=descr, space=self):
                        w_descr = space.wrap(descr)
                        return space.delete(w_descr, w_obj)
                    descrdict[descrname] = property(fget, fset, fdel)
            cls = type('CPyWrapped '+typedef.name, bases, descrdict)
            typedef.trivialwrapperclass = cls
            return cls

    def is_(self, w_obj1, w_obj2):
        return self.unwrap(w_obj1) is self.unwrap(w_obj2)

    def id(self, w_obj):
        return id(self.unwrap(w_obj))

    def unpacktuple(self, w_tuple, expected_length=None):
        assert isinstance(w_tuple, tuple)
        if expected_length is not None and expected_length != len(w_tuple):
            raise ValueError, "got a tuple of length %d instead of %d" % (
                len(w_tuple), expected_length)
        return list(w_tuple)

    def reraise(self):
        #import traceback
        #traceback.print_exc()
        #ec = self.getexecutioncontext() # .framestack.items[-1]
        #ec.print_detailed_traceback(self)
        etype, evalue, etb = sys.exc_info()
        if etype is OperationError:
            raise etype, evalue, etb   # just re-raise it
        name = etype.__name__
        if hasattr(self, 'w_' + name):
            nt = getattr(self, 'w_' + name)
            nv = object.__new__(nt)
            if isinstance(evalue, etype):
                nv.args = evalue.args
            else:
                print [etype, evalue, nt, nv], 
                print '!!!!!!!!'
                nv.args = (evalue,)
        else:
            nt = etype
            nv = evalue
        raise OperationError, OperationError(nt, nv), etb

    # from the built-ins
    def issubtype(self, w_x, w_y):
        try:
            return issubclass(w_x, w_y)
        except:
            self.reraise()

    def newtuple(self, args_w):
        return tuple(args_w)

    def newlist(self, args_w):
        return list(args_w)

    def newdict(self, items_w):
        try:
            return dict(items_w)
        except:
            self.reraise()

    def newslice(self, *args_w):
        try:
            return slice(*args_w)
        except:
            self.reraise()

    def is_true(self, w_obj):
        return not not w_obj

    def not_(self, w_obj):
        return not w_obj

    def type(self, w_x):
        return type(w_x)

    def ord(self, w_x):
        try:
            return ord(w_x)
        except:
            self.reraise()

    def round(self, w_x):
        try:
            return round(w_x)
        except:
            self.reraise()

    def iter(self, w_obj):
        if isinstance(w_obj, str) and not hasattr(w_obj, '__iter__'):
            return iter(w_obj)   # str.__iter__ is missing in CPython
        else:
            return DescrOperation.iter(self, w_obj)

    def newstring(self, asciilist):
        try:
            return ''.join([chr(ascii) for ascii in asciilist])
        except:
            self.reraise()            

    def newseqiter(self, w_obj):
        try:
            return iter(w_obj)
        except:
            self.reraise()

    def lookup(space, w_obj, name):
        assert not isinstance(w_obj, BaseWrappable)
        if isinstance(w_obj, CPyWrapper):
            typedef = type(w_obj).__internalpypytypedef__
            while typedef is not None:
                if name in typedef.rawdict:
                    return space.wrap(typedef.rawdict[name])
                typedef = typedef.base
            if name in space.object_typedef.rawdict:
                return space.wrap(space.object_typedef.rawdict[name])
            return None 
        else:
            for cls in w_obj.__class__.__mro__:
                if name in cls.__dict__:
                    return cls.__dict__[name]
            return None

    def get_and_call_args(self, w_descr, w_obj, args):
        if isinstance(w_descr, CPyWrapper):
            return DescrOperation.get_and_call_args(self, w_descr, w_obj, args)
        else:
            try:
                obj = self.unwrap(w_obj)
                if hasattr(w_descr, '__get__'):
                    obj = w_descr.__get__(obj, type(obj))
                return obj(*args.args_w, **args.kwds_w)
            except:
                #import traceback; traceback.print_exc()
                self.reraise()


for m in ObjSpace.MethodTable:
    if not hasattr(TrivialObjSpace, m[0]):
        print 'XXX there is no', m[0], 'in TrivialObjSpace'

Space = TrivialObjSpace
