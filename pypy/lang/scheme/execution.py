from pypy.lang.scheme.object import *

class Location(object):
    def __init__(self, w_obj=None):
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
        '/': Div,
            #list operations
        'cons': Cons,
        'car': Car,
        'cdr': Cdr,
        'set-car!': SetCar,
        'set-cdr!': SetCdr,
        'list': List,
        'quit': Quit,
            #comparisons
        '=': Equal,
            #predicates
        'integer?': IntegerP,
        'rational?': RealP,
        'real?': RealP,
        'complex?': NumberP,
        'number?': NumberP,
        'exact?': ExactP,
        'inexact?': InexactP,
        'zero?': ZeroP,
        'odd?': OddP,
        'even?': EvenP,
            #delayed evaluation
        'force': Force,
        'delay': Delay, #macro
            #macros
        'define': Define,
        'set!': Sete,
        'if': MacroIf,
        'lambda': Lambda,
        'begin': Begin,
        'let': Let,
        'let*': LetStar,
        'letrec': Letrec,
        'quote': Quote,
        'quasiquote': QuasiQuote,
        'syntax-rules': SyntaxRules,
    }

OPERATION_MAP = {}
for name, cls in OMAP.items():
    OPERATION_MAP[name] = cls(name)

class ExecutionContext(object):
    """Execution context implemented as a dict.

    { "IDENTIFIER": Location(W_Root()) }
    """
    def __init__(self, globalscope=None, scope=None, closure=False, macro=False):
        if globalscope is None:
            self.globalscope = {}
            for name, oper in OPERATION_MAP.items():
                self.globalscope[name] = Location(oper)

        else:
            self.globalscope = globalscope

        if scope is None:
            self.scope = {}
        else:
            self.scope = scope

        self.closure = closure

    def _dispatch(self, symb):
        if isinstance(symb, W_Symbol):
            return (self, symb.name)
        elif isinstance(symb, SyntacticClosure) and \
                isinstance(symb.sexpr, W_Symbol):
            return (symb.closure, symb.sexpr.name)

        raise SchemeSyntaxError

    def copy(self):
        return ExecutionContext(self.globalscope, self.scope.copy(), True)

    def get(self, name):
        loc = self.scope.get(name, None)
        if loc is not None:
            if loc.obj is None:
                raise UnboundVariable(name)
            return loc.obj

        loc = self.globalscope.get(name, None)
        if loc is not None:
            if loc.obj is None:
                raise UnboundVariable(name)
            return loc.obj

        raise UnboundVariable(name)

    def sete(self, name, obj):
        """update existing location or raise
        directly used by (set! <var> <expr>) macro
        """
        assert isinstance(obj, W_Root)
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
        assert isinstance(obj, W_Root)
        if self.closure:
            loc = self.scope.get(name, None)
        else:
            loc = self.globalscope.get(name, None)

        if loc is not None:
            loc.obj = obj
        else:
            self.put(name, obj)

    def sput(self, symb, obj):
        (ctx, name) = self._dispatch(symb)
        ctx.put(name, obj)

    def put(self, name, obj):
        """create new location"""
        assert isinstance(obj, W_Root)
        if self.closure:
            self.scope[name] = Location(obj)
        else:
            self.globalscope[name] = Location(obj)

    def bind(self, name):
        """create new empty binding (location)"""
        if self.closure:
            self.scope[name] = Location(None)
        else:
            self.globalscope[name] = Location(None)

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
