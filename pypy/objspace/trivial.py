#
# Trivial object space for testing
# Does not perform any wrapping and (more importantly) does not
# correctly wrap the exceptions.
#

from pypy.interpreter import pyframe, gateway
from pypy.interpreter.baseobjspace import *
from pypy.objspace.descroperation import DescrOperation, Object
import operator, types, new, sys
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
            if k.startswith('_'):
                continue
            if k not in done:
                v = getattr(exceptions, k)
                if isinstance(v, str):
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
            #if n in ['xrange',  # we define this in builtin_app
            #         'staticmethod',
            #         'classmethod',
            #         'property',
            #         ]:
            #    continue
            if isinstance(c, types.TypeType):
                setattr(self, 'w_' + c.__name__, c)
                newstuff[c.__name__] = c
        newstuff.update(self.clone_exception_hierarchy())
        self.make_builtins(newstuff)

    # general stuff
    def wrap(self, x):
        if isinstance(x, Wrappable):
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
            return x

    def unwrap(self, w):
        if isinstance(w, CPyWrapper):
            instancedict = CPyWrapper.__dict__['__dict__'].__get__(w)
            return instancedict['__internalpypyobject__']
        else:
            return w

    unwrap_builtin = unwrap

    def hackwrapperclass(self, typedef):
        try:
            return typedef.trivialwrapperclass
        except AttributeError:
            from pypy.interpreter.gateway import interp2app
            
            # make the base first (assuming single inheritance)
            mro = typedef.mro(self)
            if len(mro) > 1:
                bases = (self.hackwrapperclass(mro[1]),)
            else:
                bases = (CPyWrapper,)
            # make the class dict with descriptors redirecting to the ones
            # in rawdict
            descrdict = {'__internalpypytypedef__': typedef}
            if typedef.name != 'object':
                for descrname, descr in typedef.rawdict.items():
                    if isinstance(descr, interp2app):
                        def make_stuff(descr=descr, descrname=descrname, space=self):
                            def stuff(w_obj, *args, **kwds):
                                fn = descr.get_function(space)
                                try:
                                    return fn.descr_function_call(w_obj, *args, **kwds)
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
                            return space.get(w_descr, w_obj, space.type(w_obj))
                        def fset(w_obj, w_value, descr=descr, space=self):
                            w_descr = space.wrap(descr)
                            return space.set(w_descr, w_obj, w_value)
                        def fdel(w_obj, descr=descr, space=self):
                            w_descr = space.wrap(descr)
                            return space.set(w_descr, w_obj)
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

    def _auto(name, sourcefn, classlocals):
        s = """
def %(name)s(self, x, *args):
    try:
        value = %(sourcefn)s(x, *args)
    except:
        self.reraise()
    return self.wrap(value)
""" % locals()
        exec s in globals(), classlocals

    # from the built-ins
    _auto('issubtype', 'issubclass', locals())
    _auto('newtuple',  'tuple',      locals())
    _auto('newlist',   'list',       locals())
    _auto('newdict',   'dict',       locals())
    _auto('newslice',  'slice',      locals())
    is_true   = operator.truth
    # 'is_true' is not called 'truth' because it returns a *non-wrapped* boolean

    for _name in ('type', 'ord', 'round'):
        _auto(_name, _name, locals())

    def not_(self, w_obj):  # default implementation
        return self.wrap(not self.is_true(w_obj))

    def iter(self, w_obj):
        if isinstance(w_obj, str) and not hasattr(w_obj, '__iter__'):
            return iter(w_obj)   # str.__iter__ is missing in CPython
        else:
            return DescrOperation.iter(self, w_obj)

#    for _name in ('id', 'type', 'iter', 'repr', 'str', 'len',
#                  'pow', 'divmod', 'hash', 'setattr', 'delattr', 'hex',
#                  'oct', 'ord', 'getattr'):
#        _auto(_name, _name, locals())
#
    #for _name in ('pos', 'neg', 'not_', 'abs', 'invert',
    #              'mul', 'truediv', 'floordiv', 'div', 'mod',
    #              'add', 'sub', 'lshift', 'rshift', 'and_', 'xor', 'or_',
    #              'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'contains'):
    #    _auto(_name, 'operator.' + _name, locals())

    # in-place operators
    #def inplace_pow(self, w1, w2):
    #    w1 **= w2
    #    return self.wrap(w1)
    #def inplace_mul(self, w1, w2):
    #    w1 *= w2
    #    return self.wrap(w1)
    #def inplace_truediv(self, w1, w2):
    #    w1 /= w2  # XXX depends on compiler flags
    #    return self.wrap(w1)
    #def inplace_floordiv(self, w1, w2):
    #    w1 //= w2
    #    return self.wrap(w1)
    #def inplace_div(self, w1, w2):
    #    w1 /= w2  # XXX depends on compiler flags
    #    return self.wrap(w1)
    #def inplace_mod(self, w1, w2):
    #    w1 %= w2
    #    return self.wrap(w1)

    #def inplace_add(self, w1, w2):
    #    w1 += w2
    #    return self.wrap(w1)
    #def inplace_sub(self, w1, w2):
    #    w1 -= w2
    #    return self.wrap(w1)
    #def inplace_lshift(self, w1, w2):
    #    w1 <<= w2
    #    return self.wrap(w1)
    #def inplace_rshift(self, w1, w2):
    #    w1 >>= w2
    #    return self.wrap(w1)
    #def inplace_and(self, w1, w2):
    #    w1 &= w2
    #    return self.wrap(w1)
    #def inplace_or(self, w1, w2):
    #    w1 |= w2
    #    return self.wrap(w1)
    #def inplace_xor(self, w1, w2):
    #    w1 ^= w2
    #    return self.wrap(w1)


    # slicing
    def old_slice(self, index):
        # return the (start, stop) indices of the slice, or None
        # if the w_index is not a slice or a slice with a step
        # this is no longer useful in Python 2.3
        if isinstance(index, types.SliceType):
            if index.step is None or index.step == 1:
                start, stop = index.start, index.stop
                if start is None: start = 0
                if stop  is None: stop  = sys.maxint
                return start, stop
        return None

##    def getitem(self, w_obj, w_index):
##        obj = self.unwrap(w_obj)
##        index = self.unwrap(w_index)
##        sindex = self.old_slice(index)
##        try:
##            if sindex is None:
##                return self.wrap(obj[index])
##            else:
##                return self.wrap(operator.getslice(obj, sindex[0], sindex[1]))
##        except:
##            self.reraise()

##    def setitem(self, w_obj, w_index, w_value):
##        obj = self.unwrap(w_obj)
##        index = self.unwrap(w_index)
##        value = self.unwrap(w_value)
##        sindex = self.old_slice(index)
##        try:
##            if sindex is None:
##                obj[index] = value
##            else:
##                operator.setslice(obj, sindex[0], sindex[1], value)
##        except:
##            self.reraise()

##    def delitem(self, w_obj, w_index):
##        obj = self.unwrap(w_obj)
##        index = self.unwrap(w_index)
##        sindex = self.old_slice(index)
##        try:
##            if sindex is None:
##                del obj[index]
##            else:
##                operator.delslice(obj, sindex[0], sindex[1])
##        except:
##            self.reraise()

    # misc
    #def next(self, w):
    #    if hasattr(w, 'pypy_next'):
    #        return w.pypy_next()
    #    try:
    #        return self.wrap(w.next())
    #    except StopIteration:
    #        raise NoValue

    def newstring(self, asciilist):
        try:
            return ''.join([chr(ascii) for ascii in asciilist])
        except:
            self.reraise()            

    #def call(self, callable, args, kwds):
    #    if isinstance(callable, types.ClassType):
    #        import new
    #        try:
    #            r = new.instance(callable)
    #        except:
    #            self.reraise()
    #        if hasattr(r, '__init__'):
    #            self.call(r.__init__, args, kwds)
    #        return self.wrap(r)
    #    #if (isinstance(callable, types.MethodType)
        #    and callable.im_self is not None):
        #    args = (callable.im_self,) + args
        #    callable = callable.im_func
    #    assert not isinstance(callable, gateway.Gateway), (
    #        "trivial object space is detecting an object that has not "
    #        "been wrapped")
    #    if hasattr(callable, 'pypy_call'):
    #        return callable.pypy_call(args, kwds)
    #    try:
    #        return self.wrap(callable(*args, **(kwds or {})))
    #    except OperationError:
    #        raise
    #    except:
    #        #print "got exception in", callable.__name__
    #        #print "len args", len(args)
    #        #print "kwds", kwds
    #        self.reraise()
    #            
    #def get(self, descr, ob, cls):
    #    try:
    #        return self.wrap(descr.__get__(ob, cls))
    #    except:
    #        self.reraise()

    def new(self, type, args, kw):
        return self.wrap(type(args, kw))

    def init(self, type, args, kw):
        pass

    #def set(self, descr, ob, val):
    #    descr.__set__(ob, val)

    #def delete(self, descr, ob):
    #    descr.__delete__(ob)

    #def nonzero(self, ob):
    #    return not not ob

    #def float(self, ob):
    #    return float(ob)

    #def int(self, ob):
    #    return int(ob)

    #def round(self, *args):
    #    return round(*args)

    def lookup(space, w_obj, name):
        assert not isinstance(w_obj, Wrappable)
        if isinstance(w_obj, CPyWrapper):
            typedef = type(w_obj).__internalpypytypedef__
            for basedef in typedef.mro(space):
                if name in basedef.rawdict:
                    return space.wrap(basedef.rawdict[name])
            return None 
        else:
            for cls in w_obj.__class__.__mro__:
                if name in cls.__dict__:
                    return cls.__dict__[name]
            return None

    def get_and_call(self, w_descr, w_obj, w_args, w_kwargs):
        if isinstance(w_descr, CPyWrapper):
            return DescrOperation.get_and_call(self, w_descr, w_obj,
                                               w_args, w_kwargs)
        else:
            try:
                obj = self.unwrap(w_obj)
                if hasattr(w_descr, '__get__'):
                    obj = w_descr.__get__(obj, type(obj))
                return obj(*w_args, **w_kwargs)
            except:
                self.reraise()

    def get_and_call_function(self, w_descr, w_obj, *args_w, **kwargs_w):
        if isinstance(w_descr, CPyWrapper):
            return DescrOperation.get_and_call_function(self, w_descr, w_obj,
                                                        *args_w, **kwargs_w)
        else:
            try:
                obj = self.unwrap(w_obj)
                if hasattr(w_descr, '__get__'):
                    obj = w_descr.__get__(obj, type(obj))
                return obj(*args_w, **kwargs_w)
            except:
                #import traceback; traceback.print_exc()
                self.reraise()


for m in ObjSpace.MethodTable:
    if not hasattr(TrivialObjSpace, m[0]):
        print 'XXX there is no', m[0], 'in TrivialObjSpace'

Space = TrivialObjSpace
