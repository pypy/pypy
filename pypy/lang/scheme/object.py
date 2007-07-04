import autopath

class W_Root(object):
    def to_string(self):
        return ''

    def to_boolean(self):
        return True

    def __str__(self):
        return self.to_string() + "W"

    def __repr__(self):
        return "<W_Root " + self.to_string() + ">"

    def eval(self, ctx):
        return self

class W_Identifier(W_Root):
    def __init__(self, val):
        self.name = val

    def to_string(self):
        return self.name

    def __repr__(self):
        return "<W_Identifier " + self.name + ">"

    def eval(self, ctx):

        if ctx is None:
            ctx = ExecutionContext()

        w_obj = ctx.get(self.name)
        if w_obj is not None:
            return w_obj
        else:
            #reference to undefined identifier
            #unbound
            raise "Unbound variable: %s" % (self.name, )

class W_Symbol(W_Root):
    def __init__(self, val):
        self.name = val

    def to_string(self):
        return self.name

    def __repr__(self):
        return "<W_symbol " + self.name + ">"

class W_Boolean(W_Root):
    def __init__(self, val):
        self.boolval = bool(val)

    def to_string(self):
        if self.boolval:
            return "#t"
        return "#f"

    def to_boolean(self):
        return self.boolval

    def __repr__(self):
        return "<W_Boolean " + str(self.boolval) + " >"

class W_String(W_Root):
    def __init__(self, val):
        self.strval = val

    def to_string(self):
        return self.strval

    def __repr__(self):
        return "<W_String " + self.strval + " >"

class W_Fixnum(W_Root):
    def __init__(self, val):
        self.fixnumval = int(val)

    def to_string(self):
        return str(self.fixnumval)

    def to_number(self):
        return self.to_fixnum()

    def to_fixnum(self):
        return self.fixnumval

    def to_float(self):
        return float(self.fixnumval)

    def equal(self, w_obj):
        return self.fixnumval == w_obj.to_number()

class W_Float(W_Root):
    def __init__(self, val):
        self.floatval = float(val)

    def to_string(self):
        return str(self.floatval)

    def to_number(self):
        return self.to_float()

    def to_fixnum(self):
        return int(self.floatval)

    def to_float(self):
        return self.floatval

    def equal(self, w_obj):
        return self.floatval == w_obj.to_number()

class W_Pair(W_Root):
    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def to_string(self):
        return "(" + self.car.to_string() + " . " \
                + self.cdr.to_string() + ")"

    def eval(self, ctx):
        oper = self.car.eval(ctx)
        return oper.eval(ctx, self.cdr)

class W_Nil(W_Root):
    def to_string(self):
        return "()"

class W_Procedure(W_Root):
    def __init__(self, pname=""):
        self.pname = pname

    def to_string(self):
        return "#<primitive-procedure %s>" % (self.pname,)

    def eval(self, ctx, lst):
        #evaluate all arguments into list
        arg_lst = []
        arg = lst
        while not isinstance(arg, W_Nil):
            arg_lst.append(arg.car.eval(ctx))
            arg = arg.cdr

        return self.procedure(ctx, arg_lst)

    def procedure(self, ctx, lst):
        raise NotImplementedError

class W_Macro(W_Root):
    def __init__(self, pname=""):
        self.pname = pname

    def to_string(self):
        return "#<primitive-macro %s>" % (self.pname,)

    def eval(self, ctx, lst=None):
        raise NotImplementedError

class W_Lambda(W_Procedure):
    def __init__(self, args, body, closure, pname="#f"):
        self.args = []
        arg = args
        while not isinstance(arg, W_Nil):
            assert isinstance(arg.car, W_Identifier)
            #list of argument names, not evaluated
            self.args.append(arg.car.to_string())
            arg = arg.cdr

        self.body = body
        self.pname = pname
        self.closure = closure

    def to_string(self):
        return "#<procedure %s>" % (self.pname,)

    def procedure(self, ctx, lst):
        #ctx is a caller context, which is hoyfully ignored
        if len(lst) != len(self.args):
            raise "Wrong argument count"

        local_ctx = self.closure.copy()

        #set lambda arguments
        vars = zip(self.args, lst)
        for (name, val) in vars:
            local_ctx.put(name, val)

        return self.body.eval(local_ctx)

##
# operations
##
class ListOper(W_Procedure):
    def procedure(self, ctx, lst):
        acc = None
        for arg in lst:
            if acc is None:
                acc = arg.eval(ctx).to_number()
            else:
                acc = self.oper(acc, arg.eval(ctx).to_number())

        if isinstance(acc, int):
            return W_Fixnum(acc)
        else:
            return W_Float(acc)

class Add(ListOper):
    def oper(self, x, y):
        return x + y

class Sub(ListOper):
    def procedure(self, ctx, lst):
        if len(lst) == 1:
            return ListOper.procedure(self, ctx, [W_Fixnum(0), lst[0]])
        else:
            return ListOper.procedure(self, ctx, lst)

    def oper(self, x, y):
        return x - y

class Mul(ListOper):
    def oper(self, x, y):
        return x * y

class Define(W_Macro):
    def eval(self, ctx, lst):
        w_identifier = lst.car
        assert isinstance(w_identifier, W_Identifier)

        w_val = lst.cdr.car.eval(ctx)
        ctx.gset(w_identifier.name, w_val)
        return w_val

class MacroIf(W_Macro):
    def eval(self, ctx, lst):
        w_condition = lst.car
        w_then = lst.cdr.car
        if isinstance(lst.cdr.cdr, W_Nil):
            w_else = W_Boolean(False)
        else:
            w_else = lst.cdr.cdr.car

        w_cond_val = w_condition.eval(ctx)
        if w_cond_val.to_boolean() is True:
            return w_then.eval(ctx)
        else:
            return w_else.eval(ctx)

class Cons(W_Procedure):
    def procedure(self, ctx, lst):
        w_car = lst[0]
        w_cdr = lst[1]
        #cons is always creating a new pair
        return W_Pair(w_car, w_cdr)

class Car(W_Procedure):
    def procedure(self, ctx, lst):
        w_pair = lst[0]
        return w_pair.car

class Cdr(W_Procedure):
    def procedure(self, ctx, lst):
        w_pair = lst[0]
        return w_pair.cdr

class Equal(W_Procedure):
    def procedure(self, ctx, lst):
        w_first = lst[0]
        w_second = lst[1]
        return W_Boolean(w_first.equal(w_second))

class Lambda(W_Macro):
    def eval(self, ctx, lst):
        w_args = lst.car
        w_body = lst.cdr.car
        return W_Lambda(w_args, w_body, ctx.copy())

##
# Location()
##
class Location(object):
    def __init__(self, w_obj):
        self.obj = w_obj

##
# dict mapping operations to W_Xxx objects
# callables must have 2 arguments
# - ctx = execution context
# - lst = list of arguments
##
OMAP = \
    {
            #arithmetic operations
        '+': Add,
        '-': Sub,
        '*': Mul,
            #list operations
        'cons': Cons,
        'car': Car,
        'cdr': Cdr,
            #comparisons
        '=': Equal,
            #macros
        'define': Define,
        'if': MacroIf,
        'lambda': Lambda,
    }

OPERATION_MAP = {}
for name, cls in OMAP.items():
    OPERATION_MAP[name] = Location(cls(name))

class ExecutionContext(object):
    """Execution context implemented as a dict.

    { "IDENTIFIER": Location(W_Root()) }
    """
    def __init__(self, globalscope=None, scope=None):
        if globalscope is None:
            self.globalscope = dict(OPERATION_MAP)
        else:
            self.globalscope = globalscope

        if scope is None:
            self.scope = {}
        else:
            self.scope = scope

    def copy(self):
        return ExecutionContext(self.globalscope, dict(self.scope))

    def get(self, name):
        loc = self.scope.get(name, None)

        if loc is not None:
            return loc.obj

        loc = self.globalscope.get(name, None)
        if loc is not None:
            return loc.obj

        return None

    def set(self, name, obj):
        """update existing location or create new location new"""
        loc = self.scope.get(name, None)

        if loc is not None:
            loc.obj = obj
        else:
            self.put(name, obj)

    def gset(self, name, obj):
        """update existing location or create new location new"""
        loc = self.globalscope.get(name, None)

        if loc is not None:
            loc.obj = obj
        else:
            self.gput(name, obj)

    def gput(self, name, obj):
        """create new location"""
        self.globalscope[name] = Location(obj)

    def put(self, name, obj):
        """create new location"""
        self.scope[name] = Location(obj)

