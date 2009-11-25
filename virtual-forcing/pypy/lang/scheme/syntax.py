import py
from pypy.lang.scheme.object import W_Root, W_Boolean, W_Pair, W_Symbol, \
        Body, W_Promise, W_Lambda, W_Macro, w_nil, \
        ContinuationFrame, ContinuationReturn, \
        SchemeSyntaxError

##
# Macro
##
class Define(W_Macro):
    _symbol_name = "define"

    def continue_tr(self, ctx, lst, elst, cnt=True):
        w_first = lst
        w_val = elst[0]
        if isinstance(w_first, W_Symbol):
            ctx.set(w_first.name, w_val)
            if len(ctx.cont_stack) == 0:
                raise ContinuationReturn(w_val)

            cont = ctx.cont_stack.pop()
            return cont.run(ctx, w_val)

        raise SchemeSyntaxError

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        w_first = lst.car
        w_second = lst.get_cdr_as_pair()
        if isinstance(w_first, W_Symbol):
            w_val = w_second.car.eval_cf(ctx, self, w_first)
            ctx.set(w_first.name, w_val)
            return w_val #undefined
        elif isinstance(w_first, W_Pair):
            #we have lambda definition here!
            w_name = w_first.car
            if not isinstance(w_name, W_Symbol):
                raise SchemeSyntaxError

            formals = w_first.cdr #isinstance of W_List
            body = w_second
            #remember this! ContinuationFrame creation
            ctx.cont_stack.append(ContinuationFrame(self, w_first))
            w_lambda = W_Lambda(formals, body, ctx, pname=w_name.name)
            ctx.cont_stack.pop()
            ctx.set(w_name.name, w_lambda)
            return w_lambda #undefined

        raise SchemeSyntaxError

class Sete(W_Macro):
    _symbol_name = "set!"

    def continue_tr(self, ctx, lst, elst, cnt=True):
        assert cnt == True
        w_symbol = lst
        w_val = elst[0]
        ctx.ssete(w_symbol, w_val)
        if len(ctx.cont_stack) == 0:
            raise ContinuationReturn(w_val)

        cont = ctx.cont_stack.pop()
        return cont.run(ctx, w_val)

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        w_symbol = lst.car

        w_val = lst.get_cdr_as_pair().car.eval_cf(ctx, self, w_symbol)
        ctx.ssete(w_symbol, w_val)
        return w_val #undefined

class MacroIf(W_Macro):
    _symbol_name = "if"

    def call_tr(self, ctx, lst):
        #if needs to be tail-recursive aware
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
    _symbol_name = "lambda"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError(lst, "Pair")
        w_args = lst.car
        w_body = lst.cdr
        return W_Lambda(w_args, w_body, ctx)

class Begin(W_Macro):
    _symbol_name = "begin"

    def call_tr(self, ctx, lst):
        #begin uses eval_body, so it is tail-recursive aware
        return Body(lst).eval_tr(ctx)

class Let(W_Macro):
    _symbol_name = "let"

    def call_tr(self, ctx, lst):
        #let uses eval_body, so it is tail-recursive aware
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        body = Body(lst.cdr)
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            #evaluate the values in caller ctx
            w_val = w_def.get_cdr_as_pair().car.eval(ctx)
            local_ctx.sput(w_def.car, w_val)
            w_formal = w_formal.cdr

        return body.eval_tr(local_ctx)

class LetStar(W_Macro):
    _symbol_name = "let*"

    def continue_tr(self, ctx, lst, elst, cnt=True):
        ctx = ctx.copy()
        (body, w_def, w_val) = elst
        ctx.sput(w_def, w_val)
        w_formal = lst
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            w_val = w_def.get_cdr_as_pair().car.eval_cf(ctx, \
                    self, w_formal.cdr, [elst[0], w_def.car], 2)
            ctx.sput(w_def.car, w_val)
            w_formal = w_formal.cdr

        w_result = body.eval(ctx)

        if len(ctx.cont_stack) == 0:
            raise ContinuationReturn(w_result)

        cont = ctx.cont_stack.pop()
        return cont.run(ctx, w_result)

    def call_tr(self, ctx, lst):
        #let* uses eval_body, so it is tail-recursive aware
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        body = Body(lst.cdr)
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            #evaluate the values in local ctx
            w_val = w_def.get_cdr_as_pair().car.eval_cf(local_ctx, \
                    self, w_formal.cdr, [body, w_def.car], 2)
            local_ctx.sput(w_def.car, w_val)
            w_formal = w_formal.cdr

        return body.eval_tr(local_ctx)

class DictWrapper(W_Root):
    def __init__(self, w_dict):
        self.d = w_dict

class Letrec(W_Macro):
    _symbol_name = "letrec"

    def continue_tr(self, ctx, lst, elst, cnt=True):
        ctx = ctx.copy()
        (body, name_symb, name_val, cont_val) = elst
        assert isinstance(name_symb, DictWrapper)
        assert isinstance(name_val, DictWrapper)
        assert isinstance(lst, W_Symbol)

        cont_name = lst.name
        for (name, w_val) in name_val.d.items():
            if name == cont_name:
                ctx.ssete(lst, cont_val)
            else:
                ctx.ssete(name_symb.d[name], w_val)

        w_result = body.eval(ctx)

        if len(ctx.cont_stack) == 0:
            raise ContinuationReturn(w_result)

        cont = ctx.cont_stack.pop()
        return cont.run(ctx, w_result)

    def call_tr(self, ctx, lst):
        """let uses eval_body, so it is tail-recursive aware"""
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        body = Body(lst.cdr)
        map_name_expr = {}
        map_name_symb = {}
        w_name_symb = DictWrapper(map_name_symb)
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            name = w_def.car.to_string()
            map_name_expr[name] = w_def.get_cdr_as_pair().car
            map_name_symb[name] = w_def.car
            local_ctx.sbind(w_def.car)
            w_formal = w_formal.cdr

        map_name_val = {}
        w_name_val = DictWrapper(map_name_val)
        for (name, expr) in map_name_expr.items():
            map_name_val[name] = expr.eval_cf(local_ctx, self,
                    map_name_symb[name],
                    [body, w_name_symb, w_name_val], 3)

        for (name, w_val) in map_name_val.items():
            local_ctx.ssete(map_name_symb[name], w_val)

        return body.eval_tr(local_ctx)

class Quote(W_Macro):
    _symbol_name = "quote"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        return lst.car

class QuasiQuote(W_Macro):
    _symbol_name = "quasiquote"

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
    _symbol_name = "delay"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        return W_Promise(lst.car, ctx)

