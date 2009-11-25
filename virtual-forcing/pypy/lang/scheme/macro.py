import py
from pypy.lang.scheme.object import W_Root, W_Pair, W_List, W_Symbol, \
        W_Macro, W_Procedure, \
        Body, SchemeException, SchemeSyntaxError, UnboundVariable, \
        w_nil, w_ellipsis, plst2lst

##
# DerivedMacros
##
class SyntaxRules(W_Macro):
    _symbol_name = "syntax-rules"

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

            #XXX locations here
            literal_name = w_literals.car.to_string()
            w_temp = ctx.get_location(literal_name)

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

class Ellipsis(W_Root):
    def __init__(self, mdict_lst):
        self.mdict_lst = mdict_lst

    def __repr__(self):
        return "#<e: " + str(self.mdict_lst) + ">"

class EllipsisException(SchemeException):
    def __init__(self, length):
        self.length = length

class EllipsisTemplate(SchemeException):
    pass

class EllipsisPattern(SchemeException):
    pass

class MatchError(SchemeException):
    pass

class SyntaxRule(object):
    def __init__(self, pattern, template, literals):
        assert isinstance(pattern, W_Pair)
        self.pattern = pattern
        self.template = template
        self.literals = literals

    def __str__(self):
        return self.pattern.to_string() + " -> " + self.template.to_string()

    def match(self, ctx, w_expr):
        #we use .cdr here, because keyword should not be a macro variable
        assert isinstance(w_expr, W_Pair)
        return self.matchr(ctx, self.pattern.cdr, w_expr.cdr)

    def matchr(self, ctx, w_patt, w_expr):
        #print "  >", w_patt.to_string(), w_expr.to_string()
        if isinstance(w_patt, W_Pair):
            w_pattcar = w_patt.car
            w_pattcdr = w_patt.cdr
            if isinstance(w_expr, W_Pair):
                mdict_car = self.matchr(ctx, w_pattcar, w_expr.car)
                try:
                    #we catch EllipsisPattern here because in car
                    # we dont know how to deal with it
                    mdict_cdr = self.matchr(ctx, w_pattcdr, w_expr.cdr)
                except EllipsisPattern:
                    #print "ellipsis matched", w_patt, w_expr

                    mdict_lst = []
                    w_pair = w_expr
                    while isinstance(w_pair, W_Pair):
                        mdict = self.matchr(ctx, w_pattcar, w_pair.car)
                        mdict_lst.append(mdict)
                        w_pair = w_pair.cdr

                    mdict_cdr = {}
                    ellipsis = Ellipsis(mdict_lst)
                    for name in mdict_lst[0].keys():
                        mdict_cdr[name] = ellipsis

                    return mdict_cdr

                mdict_car.update(mdict_cdr)
                return mdict_car

            if w_expr is w_nil:
                #one matched to ellipsis, previous (up) w_expr.car
                if w_pattcar is w_ellipsis:
                    raise EllipsisPattern

                #zero matched to ellipsis
                if isinstance(w_pattcdr, W_Pair) and \
                        w_pattcdr.car is w_ellipsis:
                    #all symbols from w_pattcar match zero length Ellipsis
                    return self.dict_traverse_expr(w_pattcar, Ellipsis([]))

        if w_patt is w_ellipsis:
            raise EllipsisPattern

        if isinstance(w_patt, W_Symbol):
            try:
                w_literal = self.literals[w_patt.name]
                if not isinstance(w_expr, W_Symbol):
                    raise MatchError

                if w_patt.name != w_expr.name:
                    raise MatchError

                w_form = ctx.get_location(w_expr.name)

                if w_form is not w_literal:
                    raise MatchError

            except KeyError:
                pass

            return {w_patt.name: w_expr}

        if w_patt is w_nil and w_expr is w_nil:
            return {}

        #w_patt is w_nil, but w_expr is not
        # or w_patt is W_Pair but w_expr is not
        raise MatchError

    def dict_traverse_expr(self, expr, val=None):
        if isinstance(expr, W_Pair):
            dict_car = self.dict_traverse_expr(expr.car, val)
            dict_cdr = self.dict_traverse_expr(expr.cdr, val)
            dict_car.update(dict_cdr)
            return dict_car

        if isinstance(expr, W_Symbol) and not expr is w_ellipsis:
            return {expr.name: val}

        return {}

class SymbolClosure(W_Symbol):
    def __init__(self, ctx, symbol):
        assert isinstance(symbol, W_Symbol)
        assert not isinstance(symbol, SymbolClosure)
        self.symbol = symbol
        self.name = symbol.name
        self.closure = ctx

    def eval_tr(self, ctx):
        #this symbol is in Syntactic Closure 
        return self.symbol.eval_tr(self.closure)

    def to_string(self):
        #return "#<closure: " + self.sexpr.to_string() + ">"
        return self.symbol.to_string()

    def __repr__(self):
        return "<sc:W_Symbol " + self.to_string() + ">"

class PairClosure(W_Pair):
    def __init__(self, ctx, pair):
        assert isinstance(pair, W_Pair)
        assert not isinstance(pair, PairClosure)
        self.pair = pair
        self.car = pair.car
        self.cdr = pair.cdr
        self.closure = ctx

    def eval_tr(self, ctx):
        #this pair is in Syntactic Closure 
        return self.pair.eval_tr(self.closure)

    def to_string(self):
        #return "#<closure: " + self.sexpr.to_string() + ">"
        return self.pair.to_string()

    def __repr__(self):
        return "<sc:W_Pair " + self.to_string() + ">"

class W_Transformer(W_Procedure):
    def __init__(self, syntax_lst, ctx, pname=""):
        self.pname = pname
        self.syntax_lst = syntax_lst
        self.closure = ctx

    def match(self, ctx, w_expr):
        for rule in self.syntax_lst:
            try:
                #print "m>", rule.pattern.to_string()
                match_dict = rule.match(ctx, w_expr)
                return (rule.template, match_dict)
            except MatchError:
                pass

        raise MatchError

    def expand(self, ctx, w_expr):
        try:
            #print w_expr.to_string()
            (template, match_dict) = self.match(ctx, w_expr)
        except MatchError:
            raise SchemeSyntaxError

        return self.substitute(ctx, template, match_dict)

    def find_elli(self, expr, mdict):
        #filter mdict, returning only ellipsis which appear in expr
        if isinstance(expr, W_Pair):
            edict_car = self.find_elli(expr.car, mdict)
            edict_cdr = self.find_elli(expr.cdr, mdict)
            edict_car.update(edict_cdr)
            return edict_car

        if isinstance(expr, W_Symbol):
            val = mdict.get(expr.name, None)
            if val is None:
                return {}

            if isinstance(val, Ellipsis):
                return {expr.name: val}

        return {}

    def plst_append(self, plst, w_cdr=None):
        if len(plst) == 0:
            return w_cdr
        first_cons = plst[0]

        last_cons = None
        for lst in plst:
            if last_cons is not None:
                last_cons.cdr = lst

            while isinstance(lst, W_Pair):
                last_cons = lst
                lst = lst.cdr

        if w_cdr is not None:
            assert isinstance(last_cons, W_Pair)
            last_cons.cdr = w_cdr

        return first_cons

    def substituter(self, ctx, sexpr, match_dict, flatten=False):
        if isinstance(sexpr, W_Pair):
            w_car = self.substituter(ctx, sexpr.car, match_dict)
            try:
                w_cdr = self.substituter(ctx, sexpr.cdr, match_dict)
            except EllipsisTemplate:
                #print "ellipsis expand", sexpr
                sexprcdr = sexpr.get_cdr_as_pair()
                try:
                    #we can still have something behind ellipsis
                    w_cdr = self.substituter(ctx, sexprcdr.cdr, match_dict)
                except EllipsisTemplate:
                    #it can also be ellipsis
                    # lets pretend its usual <(obj ...) ...>
                    # instead of <obj ... ...>
                    # we will *flatten* the result later
                    w_inner = W_Pair(sexpr.car, W_Pair(sexprcdr.car, w_nil))
                    w_outer = W_Pair(w_inner, sexprcdr.cdr)
                    return self.substituter(ctx, w_outer, match_dict, True)

                plst = []
                #find_elli gets ellipses from match_dict relevant to sexpr.car
                mdict_elli = self.find_elli(sexpr.car, match_dict)
                elli_len = 0
                for (key, val) in mdict_elli.items():
                    if elli_len == 0 or elli_len == len(val.mdict_lst):
                        elli_len = len(val.mdict_lst)
                    else:
                        #we can treat is as an error if ellipsis has
                        # different match length
                        # # or get the shortest one
                        raise SchemeSyntaxError

                #generate elli_len substitutions for ellipsis
                for i in range(elli_len):
                    #one level of ellipsis nesting lower
                    new_mdict = match_dict.copy()
                    for (key, val) in mdict_elli.items():
                        new_mdict[key] = val.mdict_lst[i][key]

                    sub = self.substituter(ctx, sexpr.car, new_mdict)
                    plst.append(sub)

                if flatten:
                    #we have to flatten these list, it means append them
                    # together, and remember about w_cdr
                    w_lst = self.plst_append(plst, w_cdr)

                else:
                    w_lst = plst2lst(plst, w_cdr)

                return w_lst

            w_pair = W_Pair(w_car, w_cdr)
            if isinstance(w_car, W_Symbol):
                try:
                    w_macro = ctx.get(w_car.name)
                    # recursive macro expansion
                    if isinstance(w_macro, W_DerivedMacro):
                        if w_macro.transformer is self:
                            return w_macro.expand(ctx, w_pair)
                except UnboundVariable:
                    pass

            return w_pair

        if isinstance(sexpr, W_Symbol):
            if sexpr is w_ellipsis:
                raise EllipsisTemplate

            w_sub = match_dict.get(sexpr.name, None)
            if w_sub is not None:
                #Hygenic macros close their input forms in the syntactic
                # enviroment at the point of use

                if isinstance(w_sub, Ellipsis):
                    return w_sub

                #not always needed, because w_sub can have no W_Symbol inside
                if isinstance(w_sub, W_Symbol) and \
                        not isinstance(w_sub, SymbolClosure):
                    return SymbolClosure(ctx, w_sub)

                if isinstance(w_sub, W_Pair) and \
                        not isinstance(w_sub, PairClosure):
                    return PairClosure(ctx, w_sub)

                return w_sub

        return sexpr

    substitute = substituter

    def expand_eval(self, ctx, sexpr):
        #we have lexical scopes:
        # 1. macro was defined - self.closure
        # 2. macro is called   - ctx
        # 3. macro is expanded, can introduce new bindings - expand_ctx
        expanded = self.expand(ctx, sexpr)
        expand_ctx = self.closure.copy()
        return expanded.eval(expand_ctx)

    def procedure(self, ctx, lst):
        return self.expand_eval(ctx, lst[0])

class W_DerivedMacro(W_Macro):
    def __init__(self, name, transformer):
        self.name = name
        self.transformer = transformer

    def to_string(self):
        return "#<derived-macro %s>" % (self.name,)

    def call(self, ctx, lst):
        return self.transformer.expand_eval(ctx,
                W_Pair(W_Symbol(self.name), lst))

    def expand(self, ctx, lst):
        return self.transformer.expand(ctx, lst)

class DefineSyntax(W_Macro):
    _symbol_name = "define-syntax"

    def call(self, ctx, lst):
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError

        w_def = lst.car
        if not isinstance(w_def, W_Symbol):
            raise SchemeSyntaxError

        w_syntax_rules = lst.get_cdr_as_pair().car
        w_transformer = w_syntax_rules.eval(ctx)
        if not isinstance(w_transformer, W_Transformer):
            raise SchemeSyntaxError

        w_macro = W_DerivedMacro(w_def.name, w_transformer)
        ctx.set(w_def.name, w_macro)
        return w_macro #undefined
 
class LetSyntax(W_Macro):
    #XXX letrec-syntax missing
    _symbol_name = "let-syntax"

    def call_tr(self, ctx, lst):
        #let uses eval_body, so it is tail-recursive aware
        if not isinstance(lst, W_Pair):
            raise SchemeSyntaxError
        local_ctx = ctx.copy()
        w_formal = lst.car
        while isinstance(w_formal, W_Pair):
            w_def = w_formal.get_car_as_pair()
            w_transformer = w_def.get_cdr_as_pair().car.eval(ctx)
            if not isinstance(w_transformer, W_Transformer):
                raise SchemeSyntaxError

            w_name = w_def.car
            if not isinstance(w_name, W_Symbol):
                raise SchemeSyntaxError

            w_macro = W_DerivedMacro(w_name.name, w_transformer)

            local_ctx.put(w_name.name, w_macro)
            w_formal = w_formal.cdr

        return Body(lst.cdr).eval_tr(local_ctx)

