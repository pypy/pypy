from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.rlib.nonconst import NonConstant
from pypy.rlib.rarithmetic import r_uint

class W_Type(W_Root):
    pass

class W_Object(W_Root):
    def __init__(self, value):
        self.value = value
W_Object.typedef = W_Type()

def make_dummy(a=W_Object(None), b=W_Object(None)):
    def fn(*args):
        if NonConstant(True):
            return a
        else:
            return b
    return fn

int_dummy   = make_dummy(42, 43)
float_dummy = make_dummy(42.0, 42.1)
uint_dummy  = make_dummy(r_uint(42), r_uint(43))
str_dummy   = make_dummy('foo', 'bar')
bool_dummy  = make_dummy(True, False)

class FakeObjSpace(ObjSpace):
    w_None           = W_Object(None)
    w_False          = W_Object(None)
    w_True           = W_Object(None)
    w_Ellipsis       = W_Object(None)
    w_NotImplemented = W_Object(None)
    w_int            = W_Object(None)
    w_dict           = W_Object(None)
    w_float          = W_Object(None)
    w_long           = W_Object(None)
    w_tuple          = W_Object(None)
    w_str            = W_Object(None)
    w_unicode        = W_Object(None)
    w_type           = W_Object(None)
    w_instance       = W_Object(None)
    w_slice          = W_Object(None)
    w_hex            = W_Object(None)
    w_oct            = W_Object(None)
    
    def initialize(self):
        self.config.objspace.geninterp = False
        self.wrap_cache = {}
        self.make_builtins()

    def _freeze_(self):
        return True

    def wrap(self, x):
        if isinstance(x, Wrappable):
            w_result = x.__spacebind__(self)
            return w_result
        return W_Object(x)
    wrap._annspecialcase_ = "specialize:argtype(1)"

    def unwrap(self, w_obj):
        assert isinstance(w_obj, W_Object)
        return w_obj.value

    lookup            = make_dummy()
    allocate_instance = make_dummy()
    getattr           = make_dummy()
    setattr           = make_dummy()
    getitem           = make_dummy()
    setitem           = make_dummy()
    delitem           = make_dummy()
    int_w             = int_dummy
    uint_w            = uint_dummy
    float_w           = float_dummy
    iter              = make_dummy()
    type              = make_dummy()
    str               = make_dummy()
    repr              = make_dummy()
    id                = make_dummy()
    len               = make_dummy()
    str_w             = str_dummy
    call_args         = make_dummy()
    new_interned_str  = make_dummy()
    newstring         = make_dummy()
    newunicode        = make_dummy()
    newint            = make_dummy()
    newlong           = make_dummy()
    newfloat          = make_dummy()
    def newdict(self, track_builtin_shadowing=False):
        return self.newfloat()
    newlist           = make_dummy()
    emptylist         = make_dummy()
    newtuple          = make_dummy()
    newslice          = make_dummy()
    lt                = make_dummy()
    le                = make_dummy()
    eq                = make_dummy()
    ne                = make_dummy()
    gt                = make_dummy()
    ge                = make_dummy()
    lt_w              = bool_dummy
    le_w              = bool_dummy
    eq_w              = bool_dummy
    ne_w              = bool_dummy
    gt_w              = bool_dummy
    ge_w              = bool_dummy
    is_w              = bool_dummy
    is_               = make_dummy()
    next              = make_dummy()
    is_true           = bool_dummy
    nonzero           = make_dummy()
    issubtype         = make_dummy()
    ord               = make_dummy()
    hash              = make_dummy()
    delattr           = make_dummy() # should return None?
    contains          = make_dummy()
    hex               = make_dummy()
    oct               = make_dummy()
    pow               = make_dummy()
    inplace_pow       = make_dummy()
    cmp               = make_dummy()

    # XXsX missing operations
    def coerce(self, *args):   raise NotImplementedError("space.coerce()")
    def get(self, *args):      raise NotImplementedError("space.get()")
    def set(self, *args):      raise NotImplementedError("space.set()")
    def delete(self, *args):   raise NotImplementedError("space.delete()")
    def userdel(self, *args):  raise NotImplementedError("space.userdel()")
    def marshal_w(self, *args):raise NotImplementedError("space.marshal_w()")
    def log(self, *args):      raise NotImplementedError("space.log()")

    def exec_(self, statement, w_globals, w_locals, hidden_applevel=False):
        "NOT_RPYTHON"
        raise NotImplementedError("space.exec_")

    gettypefor     = make_dummy()
    gettypeobject  = make_dummy()
    unpackiterable = make_dummy([W_Object(None)], [W_Object(None)])


## Register all exceptions
import exceptions
for name in ObjSpace.ExceptionTable:
    exc = getattr(exceptions, name)
    setattr(FakeObjSpace, 'w_' + name, W_Object(None))
