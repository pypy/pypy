from pypy.objspace.std.register_all import register_all
from pypy.interpreter.baseobjspace import ObjSpace, BaseWrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import get_unique_interplevel_subclass
from pypy.interpreter.typedef import instantiate
from pypy.tool.cache import Cache 
from pypy.objspace.std.model import W_Object, W_ANY, MultiMethod, StdTypeModel
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.descroperation import DescrOperation
from pypy.objspace.std import stdtypedef
import types


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

    def initialize(self):
        "NOT_RPYTHON: only for initializing the space."
        self._typecache = Cache()

        # Import all the object types and implementations
        self.model = StdTypeModel()

        # install all the MultiMethods into the space instance
        for name, mm in self.MM.__dict__.items():
            if isinstance(mm, MultiMethod) and not hasattr(self, name):
                exprargs, expr, miniglobals, fallback = (
                    mm.install_not_sliced(self.model.typeorder, baked_perform_call=False))

                func = stdtypedef.make_perform_trampoline('__mm_'+name,
                                                          exprargs, expr, miniglobals,
                                                          mm)
                
                                                  # e.g. add(space, w_x, w_y)
                boundmethod = func.__get__(self)  # bind the 'space' argument
                setattr(self, name, boundmethod)  # store into 'space' instance

        # hack to avoid imports in the time-critical functions below
        for cls in self.model.typeorder:
            globals()[cls.__name__] = cls

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
                        }

        # types
        self.types_w = {}
        for typedef in self.model.pythontypes:
            w_type = self.gettypeobject(typedef)
            setattr(self, 'w_' + typedef.name, w_type)
            for_builtins[typedef.name] = w_type

        # dummy old-style classes types
        self.w_classobj = W_TypeObject(self, 'classobj', [self.w_object], {})
        self.w_instance = W_TypeObject(self, 'instance', [self.w_object], {})

        # exceptions
        mod = self.setup_exceptions(for_builtins)

        # install things in the __builtin__ module
        self.make_builtins(for_builtins)

        w_exceptions = self.wrap(mod)
        self.sys.setbuiltinmodule(w_exceptions, 'exceptions')

    def setup_exceptions(self, for_builtins):
        """NOT_RPYTHON"""
        ## hacking things in
        from pypy.module import exceptionsinterp as ex
        def call(w_type, w_args):
            space = self
            # too early for unpackiterable as well :-(
            name  = space.unwrap(space.getitem(w_args, space.wrap(0)))
            bases = space.unpacktuple(space.getitem(w_args, space.wrap(1)))
            dic   = space.unwrap(space.getitem(w_args, space.wrap(2)))
            dic = dict([(key,space.wrap(value)) for (key, value) in dic.items()])
            bases = list(bases)
            if not bases:
                bases = [space.w_object]
            res = W_TypeObject(space, name, bases, dic)
            return res
        w_dic = self.newdict([])
        try:
            # note that we hide the real call method by an instance variable!
            self.call = call
            ex.inittest_exceptions_1(self)
            for name, w_obj in ex.__dict__.items():
                if name.startswith("gcls_"):
                    excname = name[5:]
                    setattr(self, "w_"+excname, w_obj) # into space
                    for_builtins[excname] = w_obj # into builtins
                    self.setitem(w_dic, self.wrap(excname), w_obj) # into exc
            self.setitem(w_dic, self.wrap("__doc__"), ex.__doc__)
        finally:
            del self.call # revert to the class' method
        # XXX refine things, clean up, create a builtin module...
        # but for now, we do a regular one.
        from pypy.interpreter.module import Module
        return Module(self, self.wrap("exceptions"), w_dic)

    def gettypeobject(self, typedef):
        # types_w maps each StdTypeDef instance to its
        # unique-for-this-space W_TypeObject instance
        return self.loadfromcache(typedef, 
                                  stdtypedef.buildtypeobject,
                                  self._typecache)

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
        if isinstance(x, complex):
            # XXX is this right?   YYY no, this is wrong right now  (CT)
            # ZZZ hum, seems necessary for complex literals in co_consts (AR)
            c = self.getitem(self.w_builtins, self.wrap("complex"))
            return self.call_function(c,
                                      self.wrap(x.real), 
                                      self.wrap(x.imag))
        if isinstance(x, BaseWrappable):
            w_result = x.__spacebind__(self)
            #print 'wrapping', x, '->', w_result
            return w_result
        # anything below this line is implicitly XXX'ed
        if isinstance(x, type(Exception)) and issubclass(x, Exception):
            if hasattr(self, 'w_' + x.__name__):
                w_result = getattr(self, 'w_' + x.__name__)
                assert isinstance(w_result, W_TypeObject)
                return w_result
        from fake import fake_type
        if isinstance(x, type):
            ft = fake_type(x)
            return self.gettypeobject(ft.typedef)
        ft = fake_type(type(x))
        return ft(self, x)
    wrap._specialize_ = "argtypes"

    def unwrap(self, w_obj):
        if isinstance(w_obj, BaseWrappable):
            return w_obj
        return w_obj.unwrap()

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
        if w_step is None:
            w_step = self.w_None
        return W_SliceObject(self, w_start, w_end, w_step)

    def newstring(self, chars_w):
        try:
            chars = [chr(self.int_w(w_c)) for w_c in chars_w]
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
            subcls = get_unique_interplevel_subclass(cls, w_subtype.hasdict, w_subtype.nslots != 0)
            instance = instantiate(subcls)
            instance.user_setup(self, w_subtype, w_subtype.nslots)
            return instance

    def unpacktuple(self, w_tuple, expected_length=None):
        assert isinstance(w_tuple, W_TupleObject)
        t = w_tuple.wrappeditems
        if expected_length is not None and expected_length != len(t):
            raise ValueError, "got a tuple of length %d instead of %d" % (
                len(t), expected_length)
        return t

    def is_(self, w_one, w_two):
        # XXX a bit of hacking to gain more speed 
        if w_one is w_two:
            return self.w_True
        return self.w_False

    def is_true(self, w_obj):
        # XXX don't look!
        if isinstance(w_obj, W_DictObject):
            return not not w_obj.used
        else:
            return DescrOperation.is_true(self, w_obj)


    class MM:
        "Container for multimethods."
        call    = MultiMethod('call', 1, ['__call__'], general__args__=True)
        init    = MultiMethod('__init__', 1, general__args__=True)
        # special visible multimethods
        int_w   = MultiMethod('int_w', 1, [])     # returns an unwrapped int
        str_w   = MultiMethod('str_w', 1, [])     # returns an unwrapped string
        float_w = MultiMethod('float_w', 1, [])   # returns an unwrapped float

        # add all regular multimethods here
        for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
            if _name not in locals():
                mm = MultiMethod(_symbol, _arity, _specialnames)
                locals()[_name] = mm
                del mm

        pow.extras['defaults'] = (None,)
