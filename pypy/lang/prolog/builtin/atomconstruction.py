import py
from pypy.lang.prolog.interpreter import engine, helper, term, error
from pypy.lang.prolog.builtin.register import expose_builtin

# ___________________________________________________________________
# analysing and construction atoms

def impl_atom_concat(engine, a1, a2, result, continuation):
    if isinstance(a1, term.Var):
        if isinstance(a2, term.Var):
            # nondeterministic splitting of result
            r = helper.convert_to_str(result)
            for i in range(len(r) + 1):
                oldstate = engine.heap.branch()
                try:
                    a1.unify(term.Atom(r[:i]), engine.heap)
                    a2.unify(term.Atom(r[i:]), engine.heap)
                    return continuation.call(engine, choice_point=True)
                except error.UnificationFailed:
                    engine.heap.revert(oldstate)
            raise error.UnificationFailed()
        else:
            s2 = helper.convert_to_str(a2)
            r = helper.convert_to_str(result)
            if r.endswith(s2):
                stop = len(r) - len(s2)
                assert stop > 0
                a1.unify(term.Atom(r[:stop]), engine.heap)
            else:
                raise error.UnificationFailed()
    else:
        s1 = helper.convert_to_str(a1)
        if isinstance(a2, term.Var):
            r = helper.convert_to_str(result)
            if r.startswith(s1):
                a2.unify(term.Atom(r[len(s1):]), engine.heap)
            else:
                raise error.UnificationFailed()
        else:
            s2 = helper.convert_to_str(a2)
            result.unify(term.Atom(s1 + s2), engine.heap)
    return continuation.call(engine, choice_point=False)
expose_builtin(impl_atom_concat, "atom_concat",
               unwrap_spec=["obj", "obj", "obj"],
               handles_continuation=True)

def impl_atom_length(engine, s, length):
    if not (isinstance(length, term.Var) or isinstance(length, term.Number)):
        error.throw_type_error("integer", length)
    term.Number(len(s)).unify(length, engine.heap)
expose_builtin(impl_atom_length, "atom_length", unwrap_spec = ["atom", "obj"])

def impl_sub_atom(engine, s, before, length, after, sub, continuation):
    # XXX can possibly be optimized
    if isinstance(length, term.Var):
        startlength = 0
        stoplength = len(s) + 1
    else:
        startlength = helper.unwrap_int(length)
        stoplength = startlength + 1
        if startlength < 0:
            startlength = 0
            stoplength = len(s) + 1
    if isinstance(before, term.Var):
        startbefore = 0
        stopbefore = len(s) + 1
    else:
        startbefore = helper.unwrap_int(before)
        stopbefore = startbefore + 1
        if startbefore < 0:
            startbefore = 0
            stopbefore = len(s) + 1
    oldstate = engine.heap.branch()
    if not isinstance(sub, term.Var):
        s1 = helper.unwrap_atom(sub)
        if len(s1) >= stoplength or len(s1) < startlength:
            raise error.UnificationFailed()
        start = startbefore
        while True:
            try:
                try:
                    b = s.find(s1, start, stopbefore + len(s1)) # XXX -1?
                    if b < 0:
                        break
                    start = b + 1
                    before.unify(term.Number(b), engine.heap)
                    after.unify(term.Number(len(s) - len(s1) - b), engine.heap)
                    length.unify(term.Number(len(s1)), engine.heap)
                    return continuation.call(engine, choice_point=True)
                except:
                    engine.heap.revert(oldstate)
                    raise
            except error.UnificationFailed:
                pass
        raise error.UnificationFailed()
    if isinstance(after, term.Var):
        for b in range(startbefore, stopbefore):
            for l in range(startlength, stoplength):
                if l + b > len(s):
                    continue
                try:
                    try:
                        before.unify(term.Number(b), engine.heap)
                        after.unify(term.Number(len(s) - l - b), engine.heap)
                        length.unify(term.Number(l), engine.heap)
                        sub.unify(term.Atom(s[b:b + l]), engine.heap)
                        return continuation.call(engine, choice_point=True)
                    except:
                        engine.heap.revert(oldstate)
                        raise
                except error.UnificationFailed:
                    pass
    else:
        a = helper.unwrap_int(after)
        for l in range(startlength, stoplength):
            b = len(s) - l - a
            assert b >= 0
            if l + b > len(s):
                continue
            try:
                try:
                    before.unify(term.Number(b), engine.heap)
                    after.unify(term.Number(a), engine.heap)
                    length.unify(term.Number(l), engine.heap)
                    sub.unify(term.Atom(s[b:b + l]), engine.heap)
                    return continuation.call(engine, choice_point=True)
                    return None
                except:
                    engine.heap.revert(oldstate)
                    raise
            except error.UnificationFailed:
                pass
    raise error.UnificationFailed()
expose_builtin(impl_sub_atom, "sub_atom",
               unwrap_spec=["atom", "obj", "obj", "obj", "obj"],
               handles_continuation=True)

