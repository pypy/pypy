import py
from pypy.lang.scheme.object import W_Root, W_Boolean, W_Pair, W_Symbol, \
        W_Number, W_Real, W_Integer, W_List, \
        Body, W_Procedure, W_Promise, plst2lst, w_undefined, \
        SchemeSyntaxError, SchemeQuit, WrongArgType, WrongArgsNumber

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
    Op._symbol_name = oper
    return Op

Add = create_op_class('+', '', "Add", 0)
Sub = create_op_class('-', '-', "Sub")
Mul = create_op_class('*', '', "Mul", 1)
Div = create_op_class('/', '1 /', "Div")

class Equal(W_Procedure):
    _symbol_name = "="

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
    _symbol_name = "list"

    def procedure(self, ctx, lst):
        return plst2lst(lst)

class Cons(W_Procedure):
    _symbol_name = "cons"

    def procedure(self, ctx, lst):
        w_car = lst[0]
        w_cdr = lst[1]
        #cons is always creating a new pair
        return W_Pair(w_car, w_cdr)

class Car(W_Procedure):
    _symbol_name = "car"

    def procedure(self, ctx, lst):
        w_pair = lst[0]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")
        return w_pair.car

class Cdr(W_Procedure):
    _symbol_name = "cdr"

    def procedure(self, ctx, lst):
        w_pair = lst[0]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")
        return w_pair.cdr

class SetCar(W_Procedure):
    _symbol_name = "set-car!"

    def procedure(self, ctx, lst):
        w_pair = lst[0]
        w_obj = lst[1]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")

        w_pair.car = w_obj
        return w_undefined

class SetCdr(W_Procedure):
    _symbol_name = "set-cdr!"

    def procedure(self, ctx, lst):
        w_pair = lst[0]
        w_obj = lst[1]
        if not isinstance(w_pair, W_Pair):
            raise WrongArgType(w_pair, "Pair")

        w_pair.cdr = w_obj
        return w_undefined

class Apply(W_Procedure):
    _symbol_name = "apply"

    def procedure_tr(self, ctx, lst):
        if len(lst) != 2:
            raise WrongArgsNumber

        (w_procedure, w_lst) = lst
        if not isinstance(w_procedure, W_Procedure):
            raise WrongArgType(w_procedure, "Procedure")

        if not isinstance(w_lst, W_List):
            raise WrongArgType(w_lst, "List")

        return w_procedure.call_tr(ctx, w_lst)

class Quit(W_Procedure):
    _symbol_name = "quit"

    def procedure(self, ctx, lst):
        raise SchemeQuit

class Force(W_Procedure):
    _symbol_name = "force"

    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        w_promise = lst[0]
        if not isinstance(w_promise, W_Promise):
            raise WrongArgType(w_promise, "Promise")

        return w_promise.force(ctx)

##
# Equivalnece Predicates
##
class EquivalnecePredicate(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) != 2:
            raise WrongArgsNumber
        (a, b) = lst
        return W_Boolean(self.predicate(a, b))

    def predicate(self, a, b):
        raise NotImplementedError

class EqP(EquivalnecePredicate):
    _symbol_name = "eq?"

    def predicate(self, a, b):
        return a.eq(b)

class EqvP(EquivalnecePredicate):
    _symbol_name = "eqv?"

    def predicate(self, a, b):
        return a.eqv(b)

class EqualP(EquivalnecePredicate):
    _symbol_name = "equal?"

    def predicate(self, a, b):
        return a.equal(b)

##
# Number Predicates
##
class PredicateNumber(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        w_obj = lst[0]
        if not isinstance(w_obj, W_Number):
            raise WrongArgType(w_obj, "Number")

        return W_Boolean(self.predicate(w_obj))

    def predicate(self, w_obj):
        raise NotImplementedError

class IntegerP(PredicateNumber):
    _symbol_name = "integer?"

    def predicate(self, w_obj):
        if not w_obj.exact:
            return w_obj.is_integer()

        return True

class RealP(PredicateNumber):
    _symbol_name = "real?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Real)

class RationalP(RealP):
    _symbol_name = "rational?"

class NumberP(PredicateNumber):
    _symbol_name = "number?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Number)

class ComplexP(NumberP):
    _symbol_name = "complex?"

class ExactP(PredicateNumber):
    _symbol_name = "exact?"

    def predicate(self, w_obj):
        return w_obj.exact

class InexactP(PredicateNumber):
    _symbol_name = "inexact?"

    def predicate(self, w_obj):
        return not w_obj.exact

class ZeroP(PredicateNumber):
    _symbol_name = "zero?"

    def predicate(self, w_obj):
        return w_obj.to_number() == 0.0

class OddP(PredicateNumber):
    _symbol_name = "odd?"

    def predicate(self, w_obj):
        if not w_obj.is_integer():
            raise WrongArgType(w_obj, "Integer")

        return w_obj.round() % 2 != 0

class EvenP(PredicateNumber):
    _symbol_name = "even?"

    def predicate(self, w_obj):
        if not w_obj.is_integer():
            raise WrongArgType(w_obj, "Integer")

        return w_obj.round() % 2 == 0

##
# Type Pradicates
##
class TypePredicate(W_Procedure):
    def procedure(self, ctx, lst):
        if len(lst) != 1:
            raise WrongArgsNumber

        return W_Boolean(self.predicate(lst[0]))

    def predicate(self, w_obj):
        raise NotImplementedError

class BooleanP(TypePredicate):
    _symbol_name = "boolean?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Boolean)

class SymbolP(TypePredicate):
    _symbol_name = "symbol?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Symbol)

class PairP(TypePredicate):
    _symbol_name = "pair?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Pair)

class ProcedureP(TypePredicate):
    _symbol_name = "procedure?"

    def predicate(self, w_obj):
        return isinstance(w_obj, W_Procedure)

##
# Input/Output procedures
##
#class Display(W_Procedure):
#    _symbol_name = "display"
#
#    def procedure(self, ctx, lst):
#        if len(lst) == 1:
#            obj = lst[0]
#        elif len(lst) == 2:
#            (obj, port) = lst
#            raise NotImplementedError
#        else:
#            raise WrongArgsNumber
#
#        print obj.to_string()
#        return w_undefined

