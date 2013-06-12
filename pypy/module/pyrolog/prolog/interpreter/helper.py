""" Helper functions for dealing with prolog terms"""

from prolog.interpreter import term
from prolog.interpreter import error
from prolog.interpreter.signature import Signature
from rpython.rlib import jit
from prolog.interpreter.stream import PrologOutputStream, PrologInputStream,\
        PrologStream

conssig = Signature.getsignature(".", 2)
nilsig = Signature.getsignature("[]", 0)

emptylist = term.Callable.build("[]")

def wrap_list(python_list):
    curr = emptylist
    for i in range(len(python_list) - 1, -1, -1):
        curr = term.Callable.build(".", [python_list[i], curr])
    return curr

@jit.unroll_safe
def unwrap_list(prolog_list):
    # Grrr, stupid JIT
    result = [None]
    used = 0
    curr = prolog_list
    while isinstance(curr, term.Callable) and curr.signature().eq(conssig):
        if used == len(result):
            nresult = [None] * (used * 2)
            for i in range(used):
                nresult[i] = result[i]
            result = nresult
        result[used] = curr.argument_at(0)
        used += 1
        curr = curr.argument_at(1)
        curr = curr.dereference(None)
    if isinstance(curr, term.Callable) and curr.signature().eq(nilsig):
        if used != len(result):
            nresult = [None] * used
            for i in range(used):
                nresult[i] = result[i]
            result = nresult
        return result
    error.throw_type_error("list", prolog_list)

def is_callable(var, engine):
    return isinstance(var, term.Callable)

def ensure_callable(var):
    if isinstance(var, term.Var):
        error.throw_instantiation_error()
    elif isinstance(var, term.Callable):
        return var
    else:
        error.throw_type_error("callable", var)

def unwrap_int(obj):
    if isinstance(obj, term.Number):
        return obj.num
    elif isinstance(obj, term.Float):
        f = obj.floatval; i = int(f)
        if f == i:
            return i
    elif isinstance(obj, term.Var):
        error.throw_instantiation_error()
    error.throw_type_error('integer', obj)

def unwrap_atom(obj):
    if isinstance(obj, term.Atom):
        return obj.name()    
    error.throw_type_error('atom', obj)

def unwrap_predicate_indicator(predicate):
    if not isinstance(predicate, term.Callable):
        error.throw_type_error("predicate_indicator", predicate)
        assert 0, "unreachable"
    if not predicate.name()== "/" or predicate.argument_count() != 2:
        error.throw_type_error("predicate_indicator", predicate)
    name = unwrap_atom(predicate.argument_at(0))
    arity = unwrap_int(predicate.argument_at(1))
    return name, arity

def unwrap_stream(engine, obj):
    if isinstance(obj, term.Var):
        error.throw_instantiation_error()
    if isinstance(obj, term.Atom):
        try:
            stream = engine.streamwrapper.aliases[obj.name()]
        except KeyError:
            pass
        else:
            assert isinstance(stream, PrologStream)
            return stream
    error.throw_domain_error("stream", obj)

def unwrap_instream(engine, obj):
    if isinstance(obj, term.Var):
        error.throw_instantiation_error()
    if isinstance(obj, term.Atom):
        try:
            stream = engine.streamwrapper.aliases[obj.name()]
        except KeyError:
            pass
        else:
            if not isinstance(stream, PrologInputStream):
                error.throw_permission_error("input", "stream",
                        term.Atom(stream.alias))
            assert isinstance(stream, PrologInputStream)
            return stream
    error.throw_domain_error("stream", obj)

def unwrap_outstream(engine, obj):
    if isinstance(obj, term.Var):
        error.throw_instantiation_error()
    if isinstance(obj, term.Atom):
        try:
            stream = engine.streamwrapper.aliases[obj.name()]
        except KeyError:
            pass
        else:
            if not isinstance(stream, PrologOutputStream):
                error.throw_permission_error("output", "stream",
                        term.Atom(stream.alias))
            assert isinstance(stream, PrologOutputStream)
            return stream
    error.throw_domain_error("stream", obj)

def ensure_atomic(obj):
    if not is_atomic(obj):
        error.throw_type_error('atomic', obj)
    return obj

def is_atomic(obj):
    return (isinstance(obj, term.Atom) or isinstance(obj, term.Float) or 
            isinstance(obj, term.Number))

def is_term(obj):
    return isinstance(obj, term.Callable) and obj.argument_count() > 0

def convert_to_str(obj):
    if isinstance(obj, term.Var):
        error.throw_instantiation_error()
    if isinstance(obj, term.Atom):
        return obj.name()    
    elif isinstance(obj, term.Number):
        return str(obj.num)
    elif isinstance(obj, term.Float):
        return str(obj.floatval)
    elif isinstance(obj, term.BigInt):
        return obj.value.str()
    error.throw_type_error("atom", obj)

def is_numeric(obj):
    return isinstance(obj, term.Number) or isinstance(obj, term.BigInt)\
            or isinstance(obj, term.Float)
