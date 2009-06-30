from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import TypeDef
from pypy.rlib.nonconst import NonConstant
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.rbigint import rbigint

#class W_Type(W_Root):
#    _attrs_ = ()

class W_Object(W_Root):
    _attrs_ = ()
W_Object.typedef = TypeDef('foobar')

def make_dummy(a=W_Object(), b=W_Object()):
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
unicode_dummy = make_dummy(u'abc', u'cde')
bigint_dummy = make_dummy(rbigint([0]), rbigint([1]))

class FakeObjSpace(ObjSpace):
    w_None           = W_Object()
    w_False          = W_Object()
    w_True           = W_Object()
    w_Ellipsis       = W_Object()
    w_NotImplemented = W_Object()
    w_int            = W_Object()
    w_dict           = W_Object()
    w_float          = W_Object()
    w_long           = W_Object()
    w_tuple          = W_Object()
    w_str            = W_Object()
    w_basestring     = W_Object()
    w_unicode        = W_Object()
    w_type           = W_Object()
    w_instance       = W_Object()
    w_slice          = W_Object()
    w_hex            = W_Object()
    w_oct            = W_Object()
    
    def initialize(self):
        self.config.objspace.geninterp = False
        self.config.objspace.disable_call_speedhacks = True
        self.wrap_cache = {}
        self.make_builtins()

    def _freeze_(self):
        return True

    def wrap(self, x):
        if isinstance(x, Wrappable):
            w_result = x.__spacebind__(self)
            return w_result
        return W_Object()
    wrap._annspecialcase_ = "specialize:argtype(1)"

    def unwrap(self, w_obj):
        assert isinstance(w_obj, W_Object)
        return None

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
    unicode_w         = unicode_dummy
    bigint_w          = bigint_dummy
    iter              = make_dummy()
    type              = make_dummy()
    str               = make_dummy()
    int               = make_dummy()
    float             = make_dummy()
    repr              = make_dummy()
    id                = make_dummy()
    len               = make_dummy()
    str_w             = str_dummy
    call_args         = make_dummy()
    new_interned_str  = make_dummy()
    newint            = make_dummy()
    newlong           = make_dummy()
    newfloat          = make_dummy()
    def newdict(self, module=False):
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

    gettypefor     = make_dummy()
    gettypeobject  = make_dummy()
    unpackiterable = make_dummy([W_Object()], [W_Object()])


## Register all exceptions
import exceptions
for name in ObjSpace.ExceptionTable:
    exc = getattr(exceptions, name)
    setattr(FakeObjSpace, 'w_' + name, W_Object())
