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
                                {'__init__':__init__, '__str__': __str__})
        
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
            __str__ = gateway.interp2app(lambda space, w_x: str(w_x)),
            __repr__ = gateway.interp2app(lambda space, w_x: repr(w_x)),
            __class__ = GetSetProperty(self.__class__.type),
            __init__ = gateway.interp2app(Object.descr__init__.im_func),
            )
 
        self.w_None = None
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
        self.make_builtins()
        # insert these into the newly-made builtins
        for key, w_value in newstuff.items():
            self.w_builtins.setdefault(key, w_value)
            # I'm tired of wrapping correctly here -- armin

    # general stuff
    def wrap(self, x):
        if hasattr(type(x), '__wrap__'):
            return x.__wrap__(self)
        else:
            return x

    def unwrap(self, w):
        #if hasattr(type(w), '__unwrap__'):
        #    w = w.__unwrap__()
        return w

    def is_(self, w_obj1, w_obj2):
        return self.unwrap(w_obj1) is self.unwrap(w_obj2)

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

    for _name in ('id', 'type', 'ord', 'round'):
        _auto(_name, _name, locals())

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
        if isinstance(w_obj, Wrappable):
            for basedef in w_obj.typedef.mro(space):
                if name in basedef.rawdict:
                    return space.wrap(basedef.rawdict[name])
            return None 
        else:
            # hack hack hack: ignore the real 'object' and use our own
            for cls in w_obj.__class__.__mro__[:-1]:
                if name in cls.__dict__:
                    return cls.__dict__[name]
            basedef = space.object_typedef
            if name in basedef.rawdict:
                return space.wrap(basedef.rawdict[name])
            return None

    def get_and_call(self, w_descr, w_obj, w_args, w_kwargs):
        if isinstance(w_descr, Wrappable):
            return DescrOperation.get_and_call(self, w_descr, w_obj,
                                               w_args, w_kwargs)
        else:
            try:
                impl = w_descr.__get__(w_obj, type(w_obj))
                return impl(*w_args, **w_kwargs)
            except:
                self.reraise()

    def get_and_call_function(self, w_descr, w_obj, *args_w, **kwargs_w):
        if isinstance(w_descr, Wrappable):
            return DescrOperation.get_and_call_function(self, w_descr, w_obj,
                                                        *args_w, **kwargs_w)
        else:
            try:
                impl = w_descr.__get__(w_obj, type(w_obj))
                return impl(*args_w, **kwargs_w)
            except:
                #import traceback; traceback.print_exc()
                self.reraise()


for m in ObjSpace.MethodTable:
    if not hasattr(TrivialObjSpace, m[0]):
        print 'XXX there is no', m[0], 'in TrivialObjSpace'

Space = TrivialObjSpace
