#
# Trivial object space for testing
# Does not perform any wrapping and (more importantly) does not
# correctly wrap the exceptions.
#

from pypy.interpreter import pyframe, gateway
from pypy.interpreter.baseobjspace import *
import operator, types, new, sys, __builtin__

##class nugen(object):
##    def __init__(self, frame):
##        self.space = frame.space
##        self.frame = frame
##        self.running = 0

##    def next(self):
##        if self.running:
##            raise OperationError(self.space.w_ValueError,
##                                 "generator already executing")
##        ec = self.space.getexecutioncontext()

##        self.running = 1
##        try:
##            try:
##                ret = ec.eval_frame(self.frame)
##            except NoValue:
##                raise StopIteration
##        finally:
##            self.running = 0

##        return ret

##    def __iter__(self):
##        return self

##from pypy.interpreter.gateway import InterpretedFunction, InterpretedFunctionFromCode

##class numeth(InterpretedFunction):
##    def __init__(self, ifunc, instance, cls):
##        self.ifunc = ifunc
##        self.instance = instance
##        self.cls = cls

##    def __call__(self, *args, **kws):
##        if self.instance is None and self.cls is not type(None):
##            pass
##        else:
##            args = (self.instance,) + args
##        return self.ifunc(*args, **kws)

##class nufun(InterpretedFunctionFromCode):

##    def __call__(self, *args, **kwargs):
##        if self.cpycode.co_flags & 0x0020:
##            frame = self.create_frame(args, kwargs)
##            return nugen(frame)
##        else:
##            return self.eval_frame(args, kwargs)

##    def __get__(self, ob, cls=None):
##        return numeth(self, ob, cls)


class TrivialObjSpace(ObjSpace):

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
        for n, c in __builtin__.__dict__.iteritems():
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
        if hasattr(type(w), '__unwrap__'):
            w = w.__unwrap__()
        return w

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
    if hasattr(type(x), 'pypy_%(name)s'):
        return x.pypy_%(name)s(*args)
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

    for _name in ('id', 'type', 'iter', 'repr', 'str', 'len',
                  'pow', 'divmod', 'hash', 'setattr', 'delattr', 'hex',
                  'oct', 'ord', 'getattr'):
        _auto(_name, _name, locals())

    for _name in ('pos', 'neg', 'not_', 'abs', 'invert',
                  'mul', 'truediv', 'floordiv', 'div', 'mod',
                  'add', 'sub', 'lshift', 'rshift', 'and_', 'xor', 'or_',
                  'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'contains'):
        _auto(_name, 'operator.' + _name, locals())

    # in-place operators
    def inplace_pow(self, w1, w2):
        w1 **= w2
        return self.wrap(w1)
    def inplace_mul(self, w1, w2):
        w1 *= w2
        return self.wrap(w1)
    def inplace_truediv(self, w1, w2):
        w1 /= w2  # XXX depends on compiler flags
        return self.wrap(w1)
    def inplace_floordiv(self, w1, w2):
        w1 //= w2
        return self.wrap(w1)
    def inplace_div(self, w1, w2):
        w1 /= w2  # XXX depends on compiler flags
        return self.wrap(w1)
    def inplace_mod(self, w1, w2):
        w1 %= w2
        return self.wrap(w1)

    def inplace_add(self, w1, w2):
        w1 += w2
        return self.wrap(w1)
    def inplace_sub(self, w1, w2):
        w1 -= w2
        return self.wrap(w1)
    def inplace_lshift(self, w1, w2):
        w1 <<= w2
        return self.wrap(w1)
    def inplace_rshift(self, w1, w2):
        w1 >>= w2
        return self.wrap(w1)
    def inplace_and(self, w1, w2):
        w1 &= w2
        return self.wrap(w1)
    def inplace_or(self, w1, w2):
        w1 |= w2
        return self.wrap(w1)
    def inplace_xor(self, w1, w2):
        w1 ^= w2
        return self.wrap(w1)


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

    def getitem(self, w_obj, w_index):
        obj = self.unwrap(w_obj)
        index = self.unwrap(w_index)
        sindex = self.old_slice(index)
        try:
            if sindex is None:
                return self.wrap(obj[index])
            else:
                return self.wrap(operator.getslice(obj, sindex[0], sindex[1]))
        except:
            self.reraise()

    def setitem(self, w_obj, w_index, w_value):
        obj = self.unwrap(w_obj)
        index = self.unwrap(w_index)
        value = self.unwrap(w_value)
        sindex = self.old_slice(index)
        try:
            if sindex is None:
                obj[index] = value
            else:
                operator.setslice(obj, sindex[0], sindex[1], value)
        except:
            self.reraise()

    def delitem(self, w_obj, w_index):
        obj = self.unwrap(w_obj)
        index = self.unwrap(w_index)
        sindex = self.old_slice(index)
        try:
            if sindex is None:
                del obj[index]
            else:
                operator.delslice(obj, sindex[0], sindex[1])
        except:
            self.reraise()

    # misc
    def next(self, w):
        if hasattr(w, 'pypy_next'):
            return w.pypy_next()
        try:
            return self.wrap(w.next())
        except StopIteration:
            raise NoValue

    def newstring(self, asciilist):
        try:
            return ''.join([chr(ascii) for ascii in asciilist])
        except:
            self.reraise()            

    def call(self, callable, args, kwds):
        if isinstance(callable, types.ClassType):
            import new
            try:
                r = new.instance(callable)
            except:
                self.reraise()
            if hasattr(r, '__init__'):
                self.call(r.__init__, args, kwds)
            return self.wrap(r)
        #if (isinstance(callable, types.MethodType)
        #    and callable.im_self is not None):
        #    args = (callable.im_self,) + args
        #    callable = callable.im_func
        assert not isinstance(callable, gateway.Gateway), (
            "trivial object space is detecting an object that has not "
            "been wrapped")
        if hasattr(callable, 'pypy_call'):
            return callable.pypy_call(args, kwds)
        try:
            return self.wrap(callable(*args, **(kwds or {})))
        except OperationError:
            raise
        except:
            #print "got exception in", callable.__name__
            #print "len args", len(args)
            #print "kwds", kwds
            self.reraise()
                
    def get(self, descr, ob, cls):
        try:
            return self.wrap(descr.__get__(ob, cls))
        except:
            self.reraise()

    def new(self, type, args, kw):
        return self.wrap(type(args, kw))

    def init(self, type, args, kw):
        pass

    def set(self, descr, ob, val):
        descr.__set__(ob, val)

    def delete(self, descr, ob):
        descr.__delete__(ob)

    def nonzero(self, ob):
        return not not ob

    def float(self, ob):
        return float(ob)

    def int(self, ob):
        return int(ob)

    def round(self, *args):
        return round(*args)

for m in ObjSpace.MethodTable:
    if not hasattr(TrivialObjSpace, m[0]):
        print m[0] # this should raise something

Space = TrivialObjSpace
