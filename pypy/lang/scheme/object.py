import autopath

class SchemeException(Exception):
    pass

class UnboundVariable(SchemeException):
    def __str__(self):
        return "Unbound variable %s" % self.args[0]

class SchemeQuit(SchemeException):
    """raised on (quit) evaluation"""
    pass

class W_Root(object):
    def to_string(self):
        return ''

    def to_boolean(self):
        return True

    def __repr__(self):
        return "<W_Root " + self.to_string() + ">"

    def eval(self, ctx):
        return self

class W_Symbol(W_Root):
    def __init__(self, val):
        self.name = val

    def to_string(self):
        return self.name

    def __repr__(self):
        return "<W_symbol " + self.name + ">"

class W_Identifier(W_Symbol):
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
            raise UnboundVariable(self.name)

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
        assert isinstance(oper, W_Callable)
        return oper.call(ctx, self.cdr)

class W_Nil(W_Root):
    def to_string(self):
        return "()"

class W_Callable(W_Root):
    def call(self, ctx, lst):
        raise NotImplementedError

class W_Procedure(W_Callable):
    def __init__(self, pname=""):
        self.pname = pname

    def to_string(self):
        return "#<primitive-procedure %s>" % (self.pname,)

    def call(self, ctx, lst):
        #evaluate all arguments into list
        arg_lst = []
        arg = lst
        while not isinstance(arg, W_Nil):
            arg_lst.append(arg.car.eval(ctx))
            arg = arg.cdr

        return self.procedure(ctx, arg_lst)

    def procedure(self, ctx, lst):
        raise NotImplementedError

class W_Macro(W_Callable):
    def __init__(self, pname=""):
        self.pname = pname

    def to_string(self):
        return "#<primitive-macro %s>" % (self.pname,)

    def call(self, ctx, lst=None):
        raise NotImplementedError

class W_Lambda(W_Procedure):
    def __init__(self, args, body, closure, pname="#f"):
        self.args = []
        arg = args
        while not isinstance(arg, W_Nil):
            if isinstance(arg, W_Identifier):
                self.args.append([arg.to_string()])
                break
            else:
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
        #ctx is a caller context, which is joyfully ignored

        local_ctx = self.closure.copy()

        #set lambda arguments
        for idx in range(len(self.args)):
            name = self.args[idx]
            if isinstance(name, list):
                local_ctx.put(name[0], plst2lst(lst[idx:]))
            else:
                local_ctx.put(name, lst[idx])

        body_expression = self.body
        body_result = None
        while not isinstance(body_expression, W_Nil):
            body_result = body_expression.car.eval(local_ctx)
            body_expression = body_expression.cdr

        return body_result # self.body.eval(local_ctx)

def plst2lst(plst):
    """coverts python list() of W_Root into W_Pair scheme list"""
    w_cdr = W_Nil()
    plst.reverse()
    for w_obj in plst:
        w_cdr = W_Pair(w_obj, w_cdr)

    return w_cdr

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

class List(W_Procedure):
    def procedure(self, ctx, lst):
        return plst2lst(lst)

class Define(W_Macro):
    def call(self, ctx, lst):
        w_identifier = lst.car
        assert isinstance(w_identifier, W_Identifier)

        w_val = lst.cdr.car.eval(ctx)
        ctx.set(w_identifier.name, w_val)
        return w_val

class Sete(W_Macro):
    def call(self, ctx, lst):
        w_identifier = lst.car
        assert isinstance(w_identifier, W_Identifier)

        w_val = lst.cdr.car.eval(ctx)
        ctx.sete(w_identifier.name, w_val)
        return w_val

class MacroIf(W_Macro):
    def call(self, ctx, lst):
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

class Quit(W_Procedure):
    def procedure(self, ctx, lst):
        raise SchemeQuit

class Lambda(W_Macro):
    def call(self, ctx, lst):
        w_args = lst.car
        w_body = lst.cdr #.car
        return W_Lambda(w_args, w_body, ctx.copy())

class Let(W_Macro):
    def call(self, ctx, lst):
        local_ctx = ctx.copy()
        w_formal = lst.car
        while not isinstance(w_formal, W_Nil):
            name = w_formal.car.car.to_string()
            #evaluate the values in caller ctx
            val = w_formal.car.cdr.car.eval(ctx)
            local_ctx.put(name, val)
            w_formal = w_formal.cdr

        body_expression = lst.cdr
        body_result = None
        while not isinstance(body_expression, W_Nil):
            body_result = body_expression.car.eval(local_ctx)
            body_expression = body_expression.cdr

        return body_result

class Letrec(W_Macro):
    def call(self, ctx, lst):
        local_ctx = ctx.copy()

        #bound variables
        w_formal = lst.car
        while not isinstance(w_formal, W_Nil):
            name = w_formal.car.car.to_string()
            local_ctx.put(name, W_Nil())
            w_formal = w_formal.cdr

        #eval in local_ctx and assign values 
        w_formal = lst.car
        while not isinstance(w_formal, W_Nil):
            name = w_formal.car.car.to_string()
            val = w_formal.car.cdr.car.eval(local_ctx)
            local_ctx.set(name, val)
            w_formal = w_formal.cdr

        body_expression = lst.cdr
        body_result = None
        while not isinstance(body_expression, W_Nil):
            body_result = body_expression.car.eval(local_ctx)
            body_expression = body_expression.cdr

        return body_result

def Literal(sexpr):
    return W_Pair(W_Identifier('quote'), W_Pair(sexpr, W_Nil()))

class Quote(W_Macro):
    def call(self, ctx, lst):
        return lst.car

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
        'list': List,
        'quit': Quit,
            #comparisons
        '=': Equal,
            #macros
        'define': Define,
        'set!': Sete,
        'if': MacroIf,
        'lambda': Lambda,
        'let': Let,
        'letrec': Letrec,
        'quote': Quote,
    }

OPERATION_MAP = {}
for name, cls in OMAP.items():
    OPERATION_MAP[name] = Location(cls(name))

class ExecutionContext(object):
    """Execution context implemented as a dict.

    { "IDENTIFIER": Location(W_Root()) }
    """
    def __init__(self, globalscope=None, scope=None, closure=False):
        if globalscope is None:
            self.globalscope = OPERATION_MAP.copy()
        else:
            self.globalscope = globalscope

        if scope is None:
            self.scope = {}
        else:
            self.scope = scope

        self.closure = closure

    def copy(self):
        return ExecutionContext(self.globalscope, self.scope.copy(), True)

    def get(self, name):
        loc = self.scope.get(name, None)
        if loc is not None:
            return loc.obj

        loc = self.globalscope.get(name, None)
        if loc is not None:
            return loc.obj

        return None

    def sete(self, name, obj):
        """update existing location or raise
        directly used by (set! <var> <expr>) macro
        """
        loc = self.scope.get(name, None)
        if loc is not None:
            loc.obj = obj
            return obj

        loc = self.globalscope.get(name, None)
        if loc is not None:
            loc.obj = obj
            return obj

        raise UnboundVariable(name)

    def set(self, name, obj):
        """update existing location or create new location"""
        if self.closure:
            loc = self.scope.get(name, None)
        else:
            loc = self.globalscope.get(name, None)

        if loc is not None:
            loc.obj = obj
        else:
            self.put(name, obj)

    def put(self, name, obj):
        """create new location"""
        if self.closure:
            self.scope[name] = Location(obj)
        else:
            self.globalscope[name] = Location(obj)

    def get_location(self, name):
        """internal/test use only
        returns location bound to variable
        """
        loc = self.scope.get(name, None)
        if loc is not None:
            return loc

        loc = self.globalscope.get(name, None)
        if loc is not None:
            return loc

        return None

