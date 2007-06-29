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
            return w_obj.eval(ctx)
        else:
            #reference to undefined identifier
            #unbound
            raise NotImplementedError

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

class W_Pair(W_Root):
    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def to_string(self):
        return "(" + self.car.to_string() + " . " \
                + self.cdr.to_string() + ")"

    def eval(self, ctx):
        oper = self.car.eval(ctx)
        return oper(ctx, self.cdr)

class W_Nil(W_Root):
    def to_string(self):
        return "()"

############################
# operations
#not sure though any operations should exist here
#it its very similar to operation.add
#############################
class W_Procedure(W_Root):

    def __init__(self, pname=""):
        self.pname = pname

    def to_string(self):
        return "#<procedure:%s>" % (self.pname,)

    def eval(self, ctx, lst=None):
        raise NotImplementedError

def add_lst(ctx, lst):
    def adder(x, y):
        return x + y

    return apply_lst(ctx, adder, lst)

def mul_lst(ctx, lst):
    def multiplier(x, y):
        return x * y

    return apply_lst(ctx, multiplier, lst)

def apply_lst(ctx, fun, lst):
    acc = None

    if not isinstance(lst, W_Pair):
        #raise argument error
        raise

    arg = lst
    while not isinstance(arg, W_Nil):
        if acc is None:
            acc = arg.car.eval(ctx).to_number()
        else:
            acc = fun(acc, arg.car.eval(ctx).to_number())
        arg = arg.cdr

    if isinstance(acc, int):
        return W_Fixnum(acc)
    else:
        return W_Float(acc)

class Add(W_Procedure):
    def eval(self, ctx):
        return add_lst

class Mul(W_Procedure):
    def eval(self, ctx):
        return mul_lst

def define(ctx, lst):
    w_identifier = lst.car
    assert isinstance(w_identifier, W_Identifier)

    w_val = lst.cdr.car.eval(ctx)
    ctx.put(w_identifier.name, w_val)
    return w_val

class Define(W_Procedure):
    def eval(self, ctx):
        return define

def macro_if(ctx, lst):
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

class MacroIf(W_Procedure):
    def eval(self, ctx):
        return macro_if

def cons(ctx, lst):
    w_car = lst.car.eval(ctx)
    w_cdr = lst.cdr.car.eval(ctx)
    return W_Pair(w_car, w_cdr)

class Cons(W_Procedure):
    def eval(self, ctx):
        return cons

def car(ctx, lst):
    w_pair = lst.car.eval(ctx)
    return w_pair.car

class Car(W_Procedure):
    def eval(self, ctx):
        return car

def cdr(ctx, lst):
    w_pair = lst.car.eval(ctx)
    return w_pair.cdr

class Cdr(W_Procedure):
    def eval(self, ctx):
        return cdr

######################################
# dict mapping operations to callables
# callables must have 2 arguments
# - ctx = execution context
# - lst = list of arguments
######################################
OPERATION_MAP = \
    {
        '+': Add("+"),
        '*': Mul("*"),
        'define': Define("define"),
        'if': MacroIf("if"),
        'cons': Cons("cons"),
        'car': Car("car"),
        'cdr': Cdr("cdr"),
    }

class ExecutionContext(object):
    """Execution context implemented as a dict.

    { "IDENTIFIER": W_Root }
    """
    def __init__(self, scope=OPERATION_MAP):
        assert scope is not None
        self.scope = scope

    def get(self, name):
        return self.scope.get(name, None)

    def put(self, name, obj):
        self.scope[name] = obj

