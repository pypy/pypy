from pypy.objspace.std.register_all import register_all
from pypy.interpreter.baseobjspace import *
from pypy.interpreter.typedef import get_unique_interplevel_subclass
from pypy.interpreter.typedef import instantiate
from pypy.objspace.std.multimethod import *
from pypy.objspace.descroperation import DescrOperation
from pypy.objspace.std import stdtypedef
import types


class W_Object(W_Root, object):
    "Parent base class for wrapped objects."
    typedef = None

    def __init__(w_self, space):
        w_self.space = space     # XXX not sure this is ever used any more

    def __repr__(self):
        s = '%s(%s)' % (
            self.__class__.__name__,
           #', '.join(['%s=%r' % keyvalue for keyvalue in self.__dict__.items()])
            getattr(self, 'name', '')
            )
        if hasattr(self, 'w__class__'):
            s += ' instance of %s' % self.w__class__
        return '<%s>' % s

# delegation priorities
PRIORITY_SAME_TYPE    = 2  # converting between several impls of the same type
PRIORITY_PARENT_TYPE  = 1  # converting to a base type (e.g. bool -> int)
PRIORITY_PARENT_IMPL  = 0  # hard-wired in multimethod.py (W_IntObject->W_Object)
PRIORITY_CHANGE_TYPE  = -1 # changing type altogether (e.g. int -> float)
PRIORITY_ANY          = -999 # hard-wired in multimethod.py (... -> W_ANY)

def registerimplementation(implcls):
    # this function should ultimately register the implementation class somewhere
    # it may be modified to take 'typedef' instead of requiring it to be
    # stored in 'implcls' itself
    assert issubclass(implcls, W_Object)


##################################################################

class StdObjSpace(ObjSpace, DescrOperation):
    """The standard object space, implementing a general-purpose object
    library in Restricted Python."""

    PACKAGE_PATH = 'objspace.std'

    def standard_types(self):
        class result:
            "Import here the types you want to have appear in __builtin__."

            from pypy.objspace.std.objecttype import object_typedef
            from pypy.objspace.std.booltype   import bool_typedef
            from pypy.objspace.std.inttype    import int_typedef
            from pypy.objspace.std.floattype  import float_typedef
            from pypy.objspace.std.tupletype  import tuple_typedef
            from pypy.objspace.std.listtype   import list_typedef
            from pypy.objspace.std.dicttype   import dict_typedef
            from pypy.objspace.std.stringtype import str_typedef
            from pypy.objspace.std.typetype   import type_typedef
            from pypy.objspace.std.slicetype  import slice_typedef
            from pypy.objspace.std.longtype   import long_typedef
        return [value for key, value in result.__dict__.items()
                      if not key.startswith('_')]   # don't look

    def clone_exception_hierarchy(self):
        from pypy.objspace.std.typeobject import W_TypeObject
        from pypy.interpreter import gateway
        w = self.wrap
        def app___init__(self, *args):
            self.args = args
        w_init = w(gateway.app2interp(app___init__))
        def app___str__(self):
            l = len(self.args)
            if l == 0:
                return ''
            elif l == 1:
                return str(self.args[0])
            else:
                return str(self.args)
        w_str = w(gateway.app2interp(app___str__))
        import exceptions

        # to create types, we should call the standard type object;
        # but being able to do that depends on the existence of some
        # of the exceptions...
        
        self.w_Exception = W_TypeObject(
            self,
            'Exception',
            [self.w_object],
            {'__init__': w_init,
             '__str__': w_str},
            )
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
                            newtype = W_TypeObject(
                                self,
                                next,
                                [base],
                                {},
                                )
                            setattr(self,
                                    'w_' + next,
                                    newtype)
                            done[next] = newtype
                            stack.pop()
                    else:
                        stack.pop()
        return done
                            
    def initialize(self):
        # The object implementations that we want to 'link' into PyPy must be
        # imported here.  This registers them into the multimethod tables,
        # *before* the type objects are built from these multimethod tables.
        from pypy.objspace.std import objectobject
        from pypy.objspace.std import boolobject
        from pypy.objspace.std import intobject
        from pypy.objspace.std import floatobject
        from pypy.objspace.std import tupleobject
        from pypy.objspace.std import listobject
        from pypy.objspace.std import dictobject
        from pypy.objspace.std import stringobject
        from pypy.objspace.std import typeobject
        from pypy.objspace.std import sliceobject
        from pypy.objspace.std import longobject
        from pypy.objspace.std import noneobject
        from pypy.objspace.std import iterobject
        from pypy.objspace.std import cpythonobject
        # hack to avoid imports in the time-critical functions below
        global W_ObjectObject, W_BoolObject, W_IntObject, W_FloatObject
        global W_TupleObject, W_ListObject, W_DictObject, W_StringObject
        global W_TypeObject, W_SliceObject, W_LongObject, W_NoneObject
        global W_SeqIterObject
        global W_CPythonObject, W_BuiltinFunctionObject
        W_ObjectObject = objectobject.W_ObjectObject
        W_BoolObject = boolobject.W_BoolObject
        W_IntObject = intobject.W_IntObject
        W_FloatObject = floatobject.W_FloatObject
        W_TupleObject = tupleobject.W_TupleObject
        W_ListObject = listobject.W_ListObject
        W_DictObject = dictobject.W_DictObject
        W_StringObject = stringobject.W_StringObject
        W_TypeObject = typeobject.W_TypeObject
        W_SliceObject = sliceobject.W_SliceObject
        W_LongObject = longobject.W_LongObject
        W_NoneObject = noneobject.W_NoneObject
        W_SeqIterObject = iterobject.W_SeqIterObject
        W_CPythonObject = cpythonobject.W_CPythonObject
        W_BuiltinFunctionObject = cpythonobject.W_BuiltinFunctionObject
        # end of hacks

        # singletons
        self.w_None  = W_NoneObject(self)
        self.w_False = W_BoolObject(self, False)
        self.w_True  = W_BoolObject(self, True)
        from pypy.interpreter.special import NotImplemented, Ellipsis 
        self.w_NotImplemented = self.wrap(NotImplemented(self))  
        self.w_Ellipsis = self.wrap(Ellipsis(self))  

        for_builtins = {"False": self.w_False,
                        "True" : self.w_True,
                        "None" : self.w_None,
                        "NotImplemented": self.w_NotImplemented,
                        "Ellipsis": self.w_Ellipsis,
#                        "long": self.wrap(long),  # XXX temporary
                        }

        # types
        self.types_w = {}
        for typedef in self.standard_types():
            w_type = self.gettypeobject(typedef)
            setattr(self, 'w_' + typedef.name, w_type)
            for_builtins[typedef.name] = w_type

        # exceptions
        for_builtins.update(self.clone_exception_hierarchy())
        
        self.make_builtins(for_builtins)

    def gettypeobject(self, typedef):
        # types_w maps each StdTypeDef instance to its
        # unique-for-this-space W_TypeObject instance
        return self.loadfromcache(typedef, stdtypedef.buildtypeobject)

    def wrap(self, x):
        "Wraps the Python value 'x' into one of the wrapper classes."
        if x is None:
            return self.w_None
        if isinstance(x, W_Object):
            raise TypeError, "attempt to wrap already wrapped object: %s"%(x,)
        if isinstance(x, OperationError):
            raise TypeError, ("attempt to wrap already wrapped exception: %s"%
                              (x,))
        if isinstance(x, int):
            if isinstance(bool, type) and isinstance(x, bool):
                return self.newbool(x)
            return W_IntObject(self, x)
        if isinstance(x, str):
            return W_StringObject(self, x)
        if isinstance(x, dict):
            items_w = [(self.wrap(k), self.wrap(v)) for (k, v) in x.iteritems()]
            return W_DictObject(self, items_w)
        if isinstance(x, float):
            return W_FloatObject(self, x)
        if isinstance(x, tuple):
            wrappeditems = [self.wrap(item) for item in x]
            return W_TupleObject(self, wrappeditems)
        if isinstance(x, list):
            wrappeditems = [self.wrap(item) for item in x]
            return W_ListObject(self, wrappeditems)
        if isinstance(x, long):
            return W_LongObject(self, x)
        if isinstance(x, BaseWrappable):
            w_result = x.__spacebind__(self)
            #print 'wrapping', x, '->', w_result
            return w_result
        # anything below this line is implicitly XXX'ed
        SlotWrapperType = type(type(None).__repr__)
        if isinstance(x, (types.FunctionType, types.BuiltinFunctionType, SlotWrapperType)):
            return W_BuiltinFunctionObject(self, x)
        if isinstance(x, type(Exception)) and issubclass(x, Exception):
            if hasattr(self, 'w_' + x.__name__):
                return getattr(self, 'w_' + x.__name__)
        print "cpython wrapping %r" % (x,)
        #if hasattr(x, '__bases__'): 
        #    print "cpython wrapping a class %r (%s)" % (x, type(x))
            #raise TypeError, "cannot wrap classes"
        return W_CPythonObject(self, x)

    def newint(self, intval):
        return W_IntObject(self, intval)

    def newfloat(self, floatval):
        return W_FloatObject(self, floatval)

    def newtuple(self, list_w):
        assert isinstance(list_w, list)
        return W_TupleObject(self, list_w)

    def newlist(self, list_w):
        return W_ListObject(self, list_w)

    def newdict(self, list_pairs_w):
        return W_DictObject(self, list_pairs_w)

    def newslice(self, w_start, w_end, w_step):
        # w_step may be a real None
        return W_SliceObject(self, w_start, w_end, w_step)

    def newstring(self, chars_w):
        try:
            chars = [chr(self.unwrap(w_c)) for w_c in chars_w]
        except TypeError:   # chr(not-an-integer)
            raise OperationError(self.w_TypeError,
                                 self.wrap("an integer is required"))
        except ValueError:  # chr(out-of-range)
            raise OperationError(self.w_ValueError,
                                 self.wrap("character code not in range(256)"))
        return W_StringObject(self, ''.join(chars))

    def newseqiter(self, w_obj):
        return W_SeqIterObject(self, w_obj)

    def type(self, w_obj):
        return w_obj.getclass(self)

    def lookup(self, w_obj, name):
        w_type = w_obj.getclass(self)
        return w_type.lookup(name)

    def allocate_instance(self, cls, w_subtype):
        """Allocate the memory needed for an instance of an internal or
        user-defined type, without actually __init__ializing the instance."""
        w_type = self.gettypeobject(cls.typedef)
        if self.is_true(self.is_(w_type, w_subtype)):
            return instantiate(cls)
        else:
            w_type.check_user_subclass(w_subtype)
            subcls = get_unique_interplevel_subclass(cls)
            instance = instantiate(subcls)
            instance.user_setup(self, w_subtype)
            return instance

    def unpacktuple(self, w_tuple, expected_length=None):
        assert isinstance(w_tuple, W_TupleObject)
        t = w_tuple.wrappeditems
        if expected_length is not None and expected_length != len(t):
            raise ValueError, "got a tuple of length %d instead of %d" % (
                len(t), expected_length)
        return t


    class MM:
        "Container for multimethods."
        #is_data_descr = MultiMethod('is_data_descr', 1, []) # returns an unwrapped bool
        #getdict = MultiMethod('getdict', 1, [])  # get '.__dict__' attribute
        next    = MultiMethod('next', 1, ['next'])     # iterator interface
        call    = MultiMethod('call', 1, ['__call__'], varargs=True, keywords=True)
        #getattribute = MultiMethod('getattr', 2, ['__getattribute__'])  # XXX hack
        # special visible multimethods
        delegate = DelegateMultiMethod()          # delegators
        unwrap  = MultiMethod('unwrap', 1, [])    # returns an unwrapped object
        issubtype = MultiMethod('issubtype', 2, [])
        id = MultiMethod('id', 1, [])
        init = MultiMethod('__init__', 1, varargs=True, keywords=True)

    unwrap = MM.unwrap
    delegate = MM.delegate
    #is_true = MM.is_true

    def is_(self, w_one, w_two):
        # XXX a bit of hacking to gain more speed 
        #
        if w_one is w_two:
            return self.w_True
        if isinstance(w_one, W_CPythonObject):
            if isinstance(w_two, W_CPythonObject):
                if w_one.cpyobj is w_two.cpyobj:
                    return self.w_True
                return self.newbool(self.unwrap(w_one) is self.unwrap(w_two))
        return self.w_False

    def is_true(self, w_obj):
        # XXX don't look!
        if isinstance(w_obj, W_DictObject):
            return not not w_obj.used
        else:
            return DescrOperation.is_true(self, w_obj)

    def hash(space, w_obj):
        if isinstance(w_obj, W_CPythonObject):
            try:
                return space.newint(hash(w_obj.cpyobj))
            except:
                from pypy.objspace.std import cpythonobject
                cpythonobject.wrap_exception(space)
        else:
            w = space.wrap
            eq = '__eq__'
            ne = '__ne__'
            hash_s = '__hash__'

            for w_t in space.type(w_obj).mro_w:
                d = w_t.dict_w
                if hash_s in d:
                    w_descr = d[hash_s]
                    return space.get_and_call_function(w_descr, w_obj)
                if eq in d:                
                    raise OperationError(space.w_TypeError, w("unhashable type"))
            return space.id(w_obj)
        
# add all regular multimethods to StdObjSpace
for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    if not hasattr(StdObjSpace.MM, _name):
##         if isinstance(getattr(StdObjSpace, _name, None), MultiMethod):
##             mm = getattr(StdObjSpace, _name)
##         else:
        mm = MultiMethod(_symbol, _arity, _specialnames)
        setattr(StdObjSpace.MM, _name, mm)
    if not hasattr(StdObjSpace, _name):
        setattr(StdObjSpace, _name, getattr(StdObjSpace.MM, _name))

# import the common base W_ObjectObject as well as
# default implementations of some multimethods for all objects
# that don't explicitely override them or that raise FailedToImplement
from pypy.objspace.std.register_all import register_all
import pypy.objspace.std.objectobject
import pypy.objspace.std.default
