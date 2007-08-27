import pypy.lang.scheme.object as ssobject
import pypy.lang.scheme.syntax as procedure
import pypy.lang.scheme.procedure as syntax
import pypy.lang.scheme.macro as macro
from pypy.lang.scheme.ssparser import parse
import py

class Location(object):
    def __init__(self, w_obj=None):
        self.obj = w_obj

OPERATION_MAP = {}
for mod in (ssobject, syntax, procedure, macro):
    for obj_name in dir(mod):
        obj = getattr(mod, obj_name)
        try:
            issubclass(obj, ssobject.W_Callable)
            OPERATION_MAP[obj._symbol_name] = obj(obj._symbol_name)
        except (TypeError, AttributeError):
            pass

de_file = py.magic.autopath().dirpath().join("r5rs_derived_expr.ss")
de_code = de_file.read()
de_expr_lst = parse(de_code)

class ExecutionContext(object):
    """Execution context implemented as a dict.

    { "IDENTIFIER": Location(W_Root()) }
    """
    def __init__(self, globalscope=None, scope=None, closure=False,
            cont_stack=None):
        if scope is None:
            self.scope = {}
        else:
            self.scope = scope

        self.closure = closure

        if cont_stack is None:
            self.cont_stack = []
        else:
            self.cont_stack = cont_stack

        if globalscope is None:
            self.globalscope = {}
            for name, oper in OPERATION_MAP.items():
                self.globalscope[name] = Location(oper)

            for expr in de_expr_lst:
                expr.eval(self)

        else:
            self.globalscope = globalscope

    def _dispatch(self, symb):
        if isinstance(symb, macro.SymbolClosure):
            return (symb.closure, symb.name)

        elif isinstance(symb, ssobject.W_Symbol):
            return (self, symb.name)

        raise ssobject.SchemeSyntaxError

    def copy(self):
        return ExecutionContext(self.globalscope, self.scope.copy(), True,
                self.cont_stack)

    def get(self, name):
        loc = self.scope.get(name, None)
        if loc is not None:
            if loc.obj is None:
                raise ssobject.UnboundVariable(name)
            return loc.obj

        loc = self.globalscope.get(name, None)
        if loc is not None:
            if loc.obj is None:
                raise ssobject.UnboundVariable(name)
            return loc.obj

        raise ssobject.UnboundVariable(name)

    def ssete(self, symb, obj):
        (ctx, name) = self._dispatch(symb)
        ctx.sete(name, obj)

    def sete(self, name, obj):
        """update existing location or raise
        directly used by (set! <var> <expr>) macro
        """
        assert isinstance(obj, ssobject.W_Root)
        loc = self.scope.get(name, None)
        if loc is not None:
            loc.obj = obj
            return obj

        loc = self.globalscope.get(name, None)
        if loc is not None:
            loc.obj = obj
            return obj

        raise ssobject.UnboundVariable(name)

    def set(self, name, obj):
        """update existing location or create new location"""
        assert isinstance(obj, ssobject.W_Root)
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
        assert isinstance(obj, ssobject.W_Root)
        if self.closure:
            self.scope[name] = Location(obj)
        else:
            self.globalscope[name] = Location(obj)

    def sbind(self, symb):
        (ctx, name) = self._dispatch(symb)
        ctx.bind(name)

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

