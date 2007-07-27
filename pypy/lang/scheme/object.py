import py

class SchemeException(Exception):
    pass

class UnboundVariable(SchemeException):
    def __str__(self):
        return "Unbound variable %s" % (self.args[0], )

class NotCallable(SchemeException):
    def __str__(self):
        return "%s is not a callable" % (self.args[0].to_string(), )

class WrongArgsNumber(SchemeException):
    def __str__(self):
        return "Wrong number of args"

class WrongArgType(SchemeException):
    def __str__(self):
        return "Wrong argument type: %s is not %s" % \
                (self.args[0].to_string(), self.args[1])

class SchemeSyntaxError(SchemeException):
    def __str__(self):
        return "Syntax error"

class SchemeQuit(SchemeException):
    """raised on (quit) evaluation"""
    pass

class W_Root(object):
    __slots__ = []

    def to_string(self):
        return ''

    def to_boolean(self):
        return True

    def __repr__(self):
        return "<W_Root " + self.to_string() + ">"

    def eval(self, ctx):
        w_expr = self
        while ctx is not None:
            (w_expr, ctx) = w_expr.eval_tr(ctx)

        assert isinstance(w_expr, W_Root)
        return w_expr

    def eval_tr(self, ctx):
        return (self, None)

class W_Undefined(W_Root):
    def to_string(self):
        return "#<undefined>"

w_undefined = W_Undefined()

class W_Symbol(W_Root):
    #class dictionary for symbol storage
    obarray = {}

    def __init__(self, val):
        self.name = val

    def to_string(self):
        return self.name

    def __repr__(self):
        return "<W_Symbol " + self.name + ">"

    def eval_tr(self, ctx):
        w_obj = ctx.get(self.name)
        return (w_obj, None)

    def eq_symbol(self, w_symb):
        return w_symb is self

def symbol(name):
    #use this to create new symbols, it stores all symbols
    #in W_Symbol.obarray dict
    #if already in obarray return it 
    name = name.lower()
    w_symb = W_Symbol.obarray.get(name, None)
    if w_symb is None:
        w_symb = W_Symbol(name)
        W_Symbol.obarray[name] = w_symb

    assert isinstance(w_symb, W_Symbol)
    return w_symb

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

class W_Real(W_Root):
    def __init__(self, val):
        self.exact = False
        self.realval = val

    def to_string(self):
        return str(self.realval)

    def to_number(self):
        return self.to_float()

    def to_fixnum(self):
        return int(self.realval)

    def to_float(self):
        return self.realval

    def round(self):
        int_part = int(self.realval)
        if self.realval > 0:
            if self.realval >= (int_part + 0.5):
                return int_part + 1

            return int_part

        else:
            if self.realval <= (int_part - 0.5):
                return int_part - 1

            return int_part

    def is_integer(self):
        return self.realval == self.round()

W_Number = W_Real

class W_Integer(W_Real):
    def __init__(self, val):
        self.intval = val
        self.realval = val
        self.exact = True

    def to_string(self):
        return str(self.intval)

    def to_number(self):
        return self.to_fixnum()

    def to_fixnum(self):
        return self.intval

    def to_float(self):
        return float(self.intval)

class W_List(W_Root):
    pass

class W_Nil(W_List):
    def to_string(self):
        return "()"

w_nil = W_Nil()

class W_Pair(W_List):
    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def to_string(self):
        car = self.car.to_string()
        cdr = self.cdr
        if isinstance(cdr, W_Pair): #proper list
            return "(" + car + " " + cdr.to_lstring() + ")"
        elif cdr is w_nil: #one element proper list
            return "(" + car + ")"

        #dotted list/pair
        return "(" + car + " . " + cdr.to_string() + ")"

    def to_lstring(self):
        car = self.car.to_string()
        cdr = self.cdr
        if isinstance(cdr, W_Pair): #still proper list
            return car + " " + cdr.to_lstring()
        elif cdr is w_nil: #end of proper list
            return car

        #end proper list with dotted
        return car + " . " + cdr.to_string()

    def eval_tr(self, ctx):
        oper = self.car.eval(ctx)
        if not isinstance(oper, W_Callable):
            raise NotCallable(oper)

        #a proper (oper args ...) call
        # self.cdr has to be a proper list
        cdr = self.cdr
        if isinstance(cdr, W_List):
            return oper.call_tr(ctx, cdr)
        else:
            raise SchemeSyntaxError

    def get_car_as_pair(self):
        res = self.car
        if not isinstance(res, W_Pair):
            raise SchemeSyntaxError
        return res

    def get_cdr_as_pair(self):
        res = self.cdr
        if not isinstance(res, W_Pair):
            raise SchemeSyntaxError
        return res

class W_Callable(W_Root):
    def call_tr(self, ctx, lst):
        #usually tail-recursive call is normal call
        # which returns tuple with no further ExecutionContext
        return (self.call(ctx, lst), None)

    def call(self, ctx, lst):
        raise NotImplementedError

    def eval_body(self, ctx, body):
        body_expression = body
        while True:
            if not isinstance(body_expression, W_Pair):
                raise SchemeSyntaxError
            elif body_expression.cdr is w_nil:
                return (body_expression.car, ctx)
            else:
                body_expression.car.eval(ctx)

            body_expression = body_expression.cdr

class W_Procedure(W_Callable):
    def __init__(self, pname=""):
        self.pname = pname

    def to_string(self):
        return "#<primitive-procedure %s>" % (self.pname,)

    def call_tr(self, ctx, lst):
        #evaluate all arguments into list
        arg_lst = []
        arg = lst
        while not arg is w_nil:
            if not isinstance(arg, W_Pair):
                raise SchemeSyntaxError
            w_obj = arg.car.eval(ctx)
            arg_lst.append(w_obj)
            arg = arg.cdr

        return self.procedure_tr(ctx, arg_lst)

    def procedure(self, ctx, lst):
        raise NotImplementedError

    def procedure_tr(self, ctx, lst):
        #usually tail-recursive procedure is normal procedure
        # which returns tuple with no further ExecutionContext
        return (self.procedure(ctx, lst), None)

class W_Macro(W_Callable):
    def __init__(self, pname=""):
        self.pname = pname

    def to_string(self):
        return "#<primitive-macro %s>" % (self.pname,)

class Formal(object):
    def __init__(self, name, islist=False):
        self.name = name
        self.islist = islist

class W_Lambda(W_Procedure):
    def __init__(self, args, body, closure, pname="#f"):
        self.args = []
        arg = args
        while not arg is w_nil:
            if isinstance(arg, W_Symbol):
                self.args.append(Formal(arg.to_string(), True))
                break
            else:
                if not isinstance(arg, W_Pair):
                    raise SchemeSyntaxError
                if not isinstance(arg.car, W_Symbol):
                    raise WrongArgType(arg.car, "Identifier")
                #list of argument names, not evaluated
                self.args.append(Formal(arg.car.to_string(), False))
                arg = arg.cdr

        self.body = body
        self.pname = pname
        self.closure = closure

    def to_string(self):
        return "#<procedure %s>" % (self.pname,)

    def procedure_tr(self, ctx, lst):
        """must be tail-recursive aware, uses eval_body"""
        #ctx is a caller context, which is joyfully ignored

        local_ctx = self.closure.copy()

        #set lambda arguments
        for idx in range(len(self.args)):
            formal = self.args[idx]
            if formal.islist:
                local_ctx.put(formal.name, plst2lst(lst[idx:]))
            else:
                local_ctx.put(formal.name, lst[idx])

        return self.eval_body(local_ctx, self.body)

def plst2lst(plst):
    """coverts python list() of W_Root into W_Pair scheme list"""
    w_cdr = w_nil
    plst.reverse()
    for w_obj in plst:
        w_cdr = W_Pair(w_obj, w_cdr)

    return w_cdr

class W_Promise(W_Root):
    def __init__(self, expr, ctx):
        self.expr = expr
        self.result = None
        self.closure = ctx

    def to_string(self):
        return "#<promise: %s>" % self.expr.to_string()

    def force(self, ctx):
        if self.result is None:
            self.result = self.expr.eval(self.closure.copy())

        return self.result

##
# operations
##
class ListOper(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) == 0:
            if self.default_result is None:
                raise WrongArgsNumber()

            return self.default_result

        if len(lst) == 1:
            if not isinstance(lst[0], W_Number):
                raise WrongArgType(lst[0], "Number")
            return self.unary_oper(lst[0])

        acc = None
        for arg in lst:
            if not isinstance(arg, W_Number):
                raise WrongArgType(arg, "Number")
            if acc is None:
                acc = arg
            else:
                acc = self.oper(acc, arg)

        return acc

    def unary_oper(self, x):
        if isinstance(x, W_Integer):
            return W_Integer(self.do_unary_oper(x.to_fixnum()))
        elif isinstance(x, W_Number):
            return W_Real(self.do_unary_oper(x.to_float()))
        else:
            raise WrongArgType(x, "Number")

    def oper(self, x, y):
        if isinstance(x, W_Integer) and isinstance(y, W_Integer):
            return W_Integer(self.do_oper(x.to_fixnum(), y.to_fixnum()))
        elif isinstance(x, W_Number) or isinstance(y, W_Number):
            return W_Real(self.do_oper(x.to_float(), y.to_float()))
        else:
            raise WrongArgType(x, "Number")

    def do_oper(self, x, y):
        raise NotImplementedError

    def do_unary_oper(self, x):
        raise NotImplementedError

def create_op_class(oper, unary_oper, title, default_result=None):
    class Op(ListOper):
        pass

    local_locals = {}
    attr_name = "do_oper"

    code = py.code.Source("""
    def %s(self, x, y):
        return x %s y
        """ % (attr_name, oper))

    exec code.compile() in local_locals
    local_locals[attr_name]._annspecialcase_ = 'specialize:argtype(1)'
    setattr(Op, attr_name, local_locals[attr_name])

    attr_name = "do_unary_oper"
    code = py.code.Source("""
    def %s(self, x):
        return %s x
        """ % (attr_name, unary_oper))

    exec code.compile() in local_locals
    local_locals[attr_name]._annspecialcase_ = 'specialize:argtype(1)'
    setattr(Op, attr_name, local_locals[attr_name])

    if default_result is None:
        Op.default_result = None
    else:
        Op.default_result = W_Integer(default_result)

    Op.__name__ = "Op" + title
    return Op

Add = create_op_class('+', '', "Add", 0)
Sub = create_op_class('-', '-', "Sub")
Mul = create_op_class('*', '', "Mul", 1)
Div = create_op_class('/', '1 /', "Div")

class Equal(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) < 2:
            return W_Boolean(True)

        prev = lst[0]
        if not isinstance(prev, W_Number):
            raise WrongArgType(prev, "Number")

        for arg in lst[1:]:
            if not isinstance(arg, W_Number):
                raise WrongArgType(arg, "Number")

            if prev.to_number() != arg.to_number():
                return W_Boolean(False)
            prev = arg

        return W_Boolean(True)

class List(W_Procedure):
    def procedure(self, ctx, lst):
        return plst2lst(lst)

class Cons(W_Procedure):
    def procedure(self, ctx, lst):
        w_car = lst[0]
        w_cdr = lst[1]
        #cons is always creating a new pair
        return W_Pair(w_car, w_cdr)

class Car(W_Procedure):
    def procedure(self, ctx, lst):
        w_pair = lst[0]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")
        return w_pair.car

class Cdr(W_Procedure):
    def procedure(self, ctx, lst):
        w_pair = lst[0]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")
        return w_pair.cdr

class SetCar(W_Procedure):
    def procedure(self, ctx, lst):
        w_pair = lst[0]
        w_obj = lst[1]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")

        w_pair.car = w_obj
        return w_undefined

class SetCdr(W_Procedure):
    def procedure(self, ctx, lst):
        w_pair = lst[0]
        w_obj = lst[1]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")

        w_pair.cdr = w_obj
        return w_undefined

class Quit(W_Procedure):
    def procedure(self, ctx, lst):
        raise SchemeQuit

class Force(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        w_promise = lst[0]
        if not isinstance(w_promise, W_Promise):
            raise WrongArgType(w_promise, "Promise")

        return w_promise.force(ctx)

##
# Predicate
##
class PredicateNumber(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        w_obj = lst[0]
        if not isinstance(w_obj, W_Number):
            raise WrongArgType(w_obj, 'Number')

        return W_Boolean(self.predicate(w_obj))

    def predicate(self, w_obj):
        raise NotImplementedError

class IntegerP(PredicateNumber):
    def predicate(self, w_obj):
        if not w_obj.exact:
            return w_obj.is_integer()

        return True

class RealP(PredicateNumber):
    def predicate(self, w_obj):
        return isinstance(w_obj, W_Real)

class NumberP(PredicateNumber):
    def predicate(self, w_obj):
        return isinstance(w_obj, W_Number)

class ExactP(PredicateNumber):
    def predicate(self, w_obj):
        return w_obj.exact

class InexactP(PredicateNumber):
    def predicate(self, w_obj):
        return not w_obj.exact

class ZeroP(PredicateNumber):
    def predicate(self, w_obj):
        return w_obj.to_number() == 0.0

class OddP(PredicateNumber):
    def predicate(self, w_obj):
        if not w_obj.is_integer():
            raise WrongArgType(w_obj, "Integer")

        return w_obj.round() % 2 != 0

class EvenP(PredicateNumber):
    def predicate(self, w_obj):
        if not w_obj.is_integer():
            raise WrongArgType(w_obj, "Integer")

        return w_obj.round() % 2 == 0

##
# Macro
##
class Define(W_Macro):
    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        w_first = lst.car
        w_second = lst.get_cdr_as_pair()
        if isinstance(w_first, W_Symbol):
            w_val = w_second.car.eval(ctx)
            ctx.set(w_first.name, w_val)
            return w_val #unspec
        elif isinstance(w_first, W_Pair):
            #we have lambda definition here!
            w_name = w_first.car
            if not isinstance(w_name, W_Symbol):
                raise SchemeSyntaxError

            formals = w_first.cdr #isinstance of W_List
            body = w_second
            w_lambda = W_Lambda(formals, body, ctx, pname=w_name.name)
            ctx.set(w_name.name, w_lambda)
            return w_lambda #unspec
        else:
            raise WrongArgType(w_first, "Identifier")

class Sete(W_Macro):
    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        w_identifier = lst.car
        if not isinstance(w_identifier, W_Symbol):
            raise WrongArgType(w_identifier, "Identifier")

        w_val = lst.get_cdr_as_pair().car.eval(ctx)
        ctx.sete(w_identifier.name, w_val)
        return w_val #unspec

class MacroIf(W_Macro):
    def call_tr(self, ctx, lst):
        """if needs to be tail-recursive aware"""
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        w_condition = lst.car
        lst_cdr = lst.get_cdr_as_pair()
        w_then = lst_cdr.car
        if lst_cdr.cdr is w_nil:
            w_else = W_Boolean(False)
        else:
            w_else = lst_cdr.get_cdr_as_pair().car

        w_cond_val = w_condition.eval(ctx)
        if w_cond_val.to_boolean() is True:
            return (w_then, ctx)
        else:
            return (w_else, ctx)

class Lambda(W_Macro):
    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError(lst, "Pair")
        w_args = lst.car
        w_body = lst.cdr
        return W_Lambda(w_args, w_body, ctx)

class Begin(W_Macro):
    def call_tr(self, ctx, lst):
        #begin uses eval_body, so it is tail-recursive aware
        return self.eval_body(ctx, lst)

class Let(W_Macro):
    def call_tr(self, ctx, lst):
        #let uses eval_body, so it is tail-recursive aware
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            #evaluate the values in caller ctx
            w_val = w_def.get_cdr_as_pair().car.eval(ctx)
            local_ctx.sput(w_def.car, w_val)
            w_formal = w_formal.cdr

        return self.eval_body(local_ctx, lst.cdr)

class LetStar(W_Macro):
    def call_tr(self, ctx, lst):
        """let* uses eval_body, so it is tail-recursive aware"""
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            #evaluate the values in local ctx
            w_val = w_def.get_cdr_as_pair().car.eval(local_ctx)
            local_ctx.sput(w_def.car, w_val)
            w_formal = w_formal.cdr

        return self.eval_body(local_ctx, lst.cdr)

class Letrec(W_Macro):
    def call_tr(self, ctx, lst):
        """let uses eval_body, so it is tail-recursive aware"""
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        map_name_expr = {}
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            name = w_def.car.to_string()
            map_name_expr[name] = w_def.get_cdr_as_pair().car
            local_ctx.bind(name)
            w_formal = w_formal.cdr

        map_name_val = {}
        for (name, expr) in map_name_expr.items():
            map_name_val[name] = expr.eval(local_ctx)

        for (name, w_val) in map_name_val.items():
            local_ctx.sete(name, w_val)

        return self.eval_body(local_ctx, lst.cdr)

def quote(sexpr):
    return W_Pair(W_Symbol('quote'), W_Pair(sexpr, w_nil))

def qq(sexpr):
    return W_Pair(W_Symbol('quasiquote'), W_Pair(sexpr, w_nil))

def unquote(sexpr):
    return W_Pair(W_Symbol('unquote'), W_Pair(sexpr, w_nil))

def unquote_splicing(sexpr):
    return W_Pair(W_Symbol('unquote-splicing'), W_Pair(sexpr, w_nil))

class Quote(W_Macro):
    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        return lst.car

class QuasiQuote(W_Macro):
    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        w_lst = self.unquote(ctx, lst.car, 1)
        return w_lst

    def unquote(self, ctx, w_lst, deep):
        if deep < 1:
            raise SchemeSyntaxError

        if isinstance(w_lst, W_Pair):
            w_oper = w_lst.car
            if isinstance(w_oper, W_Symbol):
                if w_oper.to_string() == "unquote":
 
                    #simply unquote
                    if deep == 1:
                        return w_lst.get_cdr_as_pair().car.eval(ctx)

                    #not first level, look deeper, with lower nesting level
                    if deep > 1:
                        w_unq = self.unquote(ctx,
                                w_lst.get_cdr_as_pair().car,
                                deep-1)

                        return W_Pair(w_oper, W_Pair(w_unq, w_nil))

                #increment nesting level
                if w_oper.to_string() == "quasiquote":
                    w_unq = self.unquote(ctx,
                            w_lst.get_cdr_as_pair().car,
                            deep+1)
                    return W_Pair(w_oper, W_Pair(w_unq, w_nil))

                #not first level, look deeper, with lower nesting level
                if deep > 1 and w_oper.to_string() == "unquote-splicing":
                    w_unq = self.unquote(ctx,
                            w_lst.get_cdr_as_pair().car,
                            deep-1)

                    return W_Pair(w_oper, W_Pair(w_unq, w_nil))

            #for unquote-splice we need to check one level earlier
            #cond = if we have w_oper = (unquote-splice <sexpr>)
            if deep == 1 and isinstance(w_oper, W_Pair) and \
                    isinstance(w_oper.car, W_Symbol) and \
                    w_oper.car.to_string() == "unquote-splicing":

                #rest of list, needed for "stripping away" closing parens
                w_unq_cdr = self.unquote(ctx, w_lst.cdr, deep)

                #unquote into list
                w_unq = w_oper.get_cdr_as_pair().car.eval(ctx)
                #w_unq must be proper list
                if w_unq is w_nil:
                    #if nil: reeturn only rest of list
                    return w_unq_cdr

                #traverse w_unq to find last cdr and set it to w_cdr
                w_pair = w_unq
                while isinstance(w_pair, W_Pair):
                    if w_pair.cdr is w_nil:
                        w_pair.cdr = w_unq_cdr
                        break

                    w_pair = w_pair.cdr

                return w_unq

            #no special cases, traverse tree
            return W_Pair(self.unquote(ctx, w_oper, deep),
                    self.unquote(ctx, w_lst.cdr, deep))

        #trivial case, just return
        return w_lst

class Delay(W_Macro):
    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        return W_Promise(lst.car, ctx)

##
# DerivedMacros
##
class SyntaxRules(W_Macro):
    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        w_literals = lst.car
        if not isinstance(w_literals, W_List):
            raise SchemeSyntaxError

        literals_map = {}
        while isinstance(w_literals, W_Pair):
            if not isinstance(w_literals.car, W_Symbol):
                raise SchemeSyntaxError

            literal_name = w_literals.car.to_string()
            try:
                w_temp = ctx.get(literal_name)
            except UnboundVariable:
                w_temp = w_literals.car

            literals_map[literal_name] = w_temp

            w_literals = w_literals.cdr

        w_syntax_lst = lst.cdr
        syntax_lst = []
        while isinstance(w_syntax_lst, W_Pair):
            w_syntax = w_syntax_lst.car
            if not isinstance(w_syntax, W_Pair):
                raise SchemeSyntaxError

            w_pattern = w_syntax.car
            w_template = w_syntax.get_cdr_as_pair().car

            #do stuff with w_syntax rules
            syntax_lst.append(SyntaxRule(w_pattern, w_template, literals_map))
            
            w_syntax_lst = w_syntax_lst.cdr

        #closes template in syntactic enviroment at the point of definition
        return W_Transformer(syntax_lst, ctx)

class SyntaxRule(object):
    def __init__(self, pattern, template, literals):
        self.pattern = pattern
        self.template = template
        self.literals = literals

    def __str__(self):
        return self.pattern.to_string() + " -> " + self.template.to_string()

    def match(self, ctx, w_expr, pattern=None):
        if pattern is None:
            w_patt = self.pattern
        else:
            w_patt = pattern

        match_dict = {}
        while isinstance(w_patt, W_Pair) and isinstance(w_expr, W_Pair):
            w_pattcar = w_patt.car
            w_exprcar = w_expr.car

            w_literal = self.literals.get(w_pattcar.to_string(), None)
            if w_literal is not None:
                try:
                    w_form = ctx.get(w_exprcar.to_string())
                except UnboundVariable:
                    w_form = w_exprcar

                if w_form is not w_literal:
                    return (False, {})

            if isinstance(w_pattcar, W_Pair):
                if not isinstance(w_exprcar, W_Pair):
                    return (False, {})

                (matched, match_nested) = self.match(ctx, w_exprcar, w_pattcar)
                if not matched:
                    return (False, {})

                match_dict.update(match_nested)

            match_dict[w_pattcar.to_string()] = w_exprcar
            w_patt = w_patt.cdr
            w_expr = w_expr.cdr

        if w_expr is w_nil and w_patt is w_nil:
            return (True, match_dict)

        return (False, {})

class SyntacticClosure(W_Root):
    def __init__(self, ctx, sexpr):
        self.sexpr = sexpr
        self.closure = ctx

    def eval_tr(self, ctx):
        #this symbol is in Syntactic Closure 
        return self.sexpr.eval_tr(self.closure)

    def to_string(self):
        #return "#<closure: " + self.sexpr.to_string() + ">"
        return self.sexpr.to_string()

class W_Transformer(W_Procedure):
    def __init__(self, syntax_lst, ctx, pname=""):
        self.pname = pname
        self.syntax_lst = syntax_lst
        self.closure = ctx

    def match(self, ctx, w_expr):
        for rule in self.syntax_lst:
            (matched, match_dict) = rule.match(ctx, w_expr)
            if matched:
                return (rule.template, match_dict)

        return (None, {})

    def expand(self, ctx, w_expr):
        (template, match_dict) = self.match(ctx, w_expr)

        if template is None :
            raise SchemeSyntaxError

        return self.substitute(ctx, template, match_dict)

    def substitute(self, ctx, sexpr, match_dict):
        if isinstance(sexpr, W_Symbol):
            w_sub = match_dict.get(sexpr.name, None)
            if w_sub is not None:
                # Hygenic macros close their input forms in the syntactic
                # enviroment at the point of use

                #not always needed, because w_sub can have no W_Symbols inside
                
                #already is a SyntacticClosure
                if isinstance(w_sub, SyntacticClosure):
                    assert w_sub.closure is ctx

                    return w_sub

                return SyntacticClosure(ctx, w_sub)

            return sexpr

        elif isinstance(sexpr, W_Pair):
            w_pair = W_Pair(self.substitute(ctx, sexpr.car, match_dict),
                    self.substitute(ctx, sexpr.cdr, match_dict))

            w_paircar = w_pair.car
            if isinstance(w_paircar, W_Symbol):
                try:
                    w_macro = ctx.get(w_paircar.name)

                    # recursive macro expansion
                    if isinstance(w_macro, W_DerivedMacro):
                        return w_macro.expand(ctx, w_pair)
                except UnboundVariable:
                    pass

            elif isinstance(w_paircar, SyntacticClosure) and \
                    isinstance(w_paircar.sexpr, W_Symbol):
                try:
                    #ops, which context?
                    w_macro = ctx.get(w_paircar.sexpr.name)

                    # recursive macro expansion
                    if isinstance(w_macro, W_DerivedMacro):
                        return w_macro.expand(ctx, w_pair)

                except UnboundVariable:
                    pass

            return w_pair

        return sexpr
            
    def expand_eval(self, ctx, sexpr):
        #we have lexical scopes:
        # 1. in which macro was defined - self.closure
        # 2. in which macro is called   - ctx
        # 3. in which macro is expanded, can introduce new bindings - expand_ctx 
        expanded = self.expand(ctx, sexpr)
        expand_ctx = self.closure.copy()
        return expanded.eval(expand_ctx)

    def procedure(self, ctx, lst):
        return self.expand_eval(ctx, lst[0])

class DefineSyntax(W_Macro):
    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        w_def = lst.car
        if not isinstance(w_def, W_Symbol):
            raise SchemeSyntaxError

        w_syntax_rules = lst.get_cdr_as_pair().car
        w_transformer = w_syntax_rules.eval(ctx)
        assert isinstance(w_transformer, W_Transformer)

        w_macro = W_DerivedMacro(w_def.name, w_transformer)
        ctx.set(w_def.name, w_macro)
        return w_macro
 
class W_DerivedMacro(W_Macro):
    def __init__(self, name, transformer):
        self.name = name
        self.transformer = transformer

    def to_string(self):
        return "#<derived-macro %s>" % (self.name,)

    def call(self, ctx, lst):
        return self.transformer.expand_eval(ctx, W_Pair(W_Symbol(self.name), lst))

    def expand(self, ctx, lst):
        return self.transformer.expand(ctx, lst)

