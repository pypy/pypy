#
# Trivial object space for testing
# Does not perform any wrapping and (more importantly) does not
# correctly wrap the exceptions.
#

from pypy.interpreter import pyframe
from pypy.interpreter.baseobjspace import *
import operator, types, new, sys

class nugen(object):
    def __init__(self, space, frame):
        self.space = space
        self.frame = frame
        self.running = 0
    def next(self):
        if self.running:
            raise OperationError(self.space.w_ValueError,
                                 "generator already executing")
        ec = self.space.getexecutioncontext()

        self.running = 1
        try:
            try:
                ret = ec.eval_frame(self.frame)
            except NoValue:
                raise StopIteration
        finally:
            self.running = 0

        return ret
    def __iter__(self):
        return self

class nufun(object):
    def __init__(self, space, code, globals, defaultarguments, closure):
        self.space = space
        self.__name__ = code.co_name
        self.func_code = self.code = code
        self.globals = globals
        self.defaultarguments = defaultarguments
        self.closure = closure
    def do_call(self, *args, **kwds):
        locals = self.code.build_arguments(self.space, args, kwds,
            w_defaults = self.defaultarguments,
            w_closure = self.closure)
        if self.code.co_flags & 0x0020:
            from pypy.interpreter import pyframe
            frame = pyframe.PyFrame(self.space, self.code,
                                    self.globals, locals)
            return nugen(self.space, frame)
        else:
            return self.code.eval_code(self.space, self.globals, locals)
    def __call__(self, *args, **kwds):
        return self.do_call(*args, **kwds)
    def __get__(self, ob, cls=None):
        import new
        return new.instancemethod(self, ob, cls)


class TrivialObjSpace(ObjSpace):

    def clone_exception_hierarchy(self):
        from pypy.interpreter.pycode import PyByteCode
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
                            newtype = type(k, (base,), {})
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
        import __builtin__, types
        newstuff = {"False": self.w_False,
                    "True" : self.w_True,
                    "NotImplemented" : self.w_NotImplemented,
                    "None" : self.w_None,
                    "Ellipsis" : self.w_Ellipsis,
                    "buffer": buffer,
                    "xrange": xrange,
                    "slice": slice,
                    }
        for n, c in __builtin__.__dict__.iteritems():
            if isinstance(c, types.TypeType):
                setattr(self, 'w_' + c.__name__, c)
                newstuff[c.__name__] = c
        newstuff.update(self.clone_exception_hierarchy())
        self.make_builtins()
        self.make_sys()
        # insert these into the newly-made builtins
        for key, w_value in newstuff.items():
            self.setitem(self.w_builtins, self.wrap(key), w_value)

    # general stuff
    def wrap(self, x):
        return x

    def unwrap(self, w):
        return w

    def reraise(self):
        etype, evalue = sys.exc_info()[:2]
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
        raise OperationError(nt, nv)

    # from the built-ins
    id        = id
    type      = type
    issubtype = issubclass
    newtuple  = tuple
    newlist   = list
    newdict   = dict
    newslice  = slice  # maybe moved away to application-space at some time
    newmodule = new.module
    iter      = iter
    repr      = repr
    str       = str
    len       = len
    pow       = pow
    divmod    = divmod
    hash      = hash
    setattr   = setattr
    delattr   = delattr
    is_true   = operator.truth
    # 'is_true' is not called 'truth' because it returns a *non-wrapped* boolean

    def getattr(self, w_obj, w_name):
        obj = self.unwrap(w_obj)
        name = self.unwrap(w_name)
        try:
            return getattr(obj, name)
        except:
            self.reraise()

    for _name in ('pos', 'neg', 'not_', 'abs', 'invert',
                  'mul', 'truediv', 'floordiv', 'div', 'mod',
                  'add', 'sub', 'lshift', 'rshift', 'and_', 'xor', 'or_',
                  'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'contains'):
        exec """
def %(_name)s(self, *args):
    try:
        return operator.%(_name)s(*args)
    except:
        self.reraise()
""" % locals()

    # in-place operators
    def inplace_pow(self, w1, w2):
        w1 **= w2
        return w1
    def inplace_mul(self, w1, w2):
        w1 *= w2
        return w1
    def inplace_truediv(self, w1, w2):
        w1 /= w2  # XXX depends on compiler flags
        return w1
    def inplace_floordiv(self, w1, w2):
        w1 //= w2
        return w1
    def inplace_div(self, w1, w2):
        w1 /= w2  # XXX depends on compiler flags
        return w1
    def inplace_mod(self, w1, w2):
        w1 %= w2
        return w1

    def inplace_add(self, w1, w2):
        w1 += w2
        return w1
    def inplace_sub(self, w1, w2):
        w1 -= w2
        return w1
    def inplace_lshift(self, w1, w2):
        w1 <<= w2
        return w1
    def inplace_rshift(self, w1, w2):
        w1 >>= w2
        return w1
    def inplace_and(self, w1, w2):
        w1 &= w2
        return w1
    def inplace_or(self, w1, w2):
        w1 |= w2
        return w1
    def inplace_xor(self, w1, w2):
        w1 ^= w2
        return w1


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
                return obj[index]
            else:
                return operator.getslice(obj, sindex[0], sindex[1])
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
                return operator.setslice(obj, sindex[0], sindex[1], value)
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
        try:
            return w.next()
        except StopIteration:
            raise NoValue

    def newfunction(self, code, globals, defaultarguments, closure=None):
        assert hasattr(code, 'co_name')
        assert hasattr(code, 'build_arguments')
        assert hasattr(code, 'eval_code')
        return nufun(self, code, globals, defaultarguments, closure)

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
            return r
        if (isinstance(callable, types.MethodType)
            and callable.im_self is not None):
            args = (callable.im_self,) + args
            callable = callable.im_func
        try:
            return apply(callable, args, kwds or {})
        except OperationError:
            raise
        except:
            self.reraise()
                
    def hex(self, ob):
        try:
            return hex(ob)
        except:
            self.reraise()

    def oct(self, ob):
        try:
            return oct(ob)
        except:
            self.reraise()

    def ord(self, ob):
        try:
            return ord(ob)
        except:
            self.reraise()

    def get(self, descr, ob, cls):
        try:
            return descr.__get__(ob, cls)
        except:
            self.reraise()

    def new(self, type, args, kw):
        return type(args, kw)

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

for m in ObjSpace.MethodTable:
    if not hasattr(TrivialObjSpace, m[0]):
        print m[0]

Space = TrivialObjSpace
