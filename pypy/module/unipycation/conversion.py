import prolog.interpreter.term as pterm

def _type_check(space, inst, typ):
    # XXX do the right thing with the exception
    if not space.is_true(space.isinstance(inst, typ)):
        raise TypeError("%s is not of type %s" % (inst, typ))

# -----------------------------
# Convert from Python to Prolog
# -----------------------------

def int_p_of_int_w(space, w_int):
    _type_check(space, w_int, space.w_int)

    val = space.int_w(w_int)
    return pterm.Number(val)

def float_p_of_float_w(space, w_float):
    _type_check(space, w_float, space.w_float)

    val = space.float_w(w_float)
    return pterm.Float(val)

def bigint_p_of_long_w(space, w_long):
    _type_check(space, w_long, space.w_long)

    val = space.bigint_w(w_long)
    return pterm.BigInt(val)

def atom_p_of_str_w(space, w_str):
    _type_check(space, w_str, space.w_str)

    val = space.str_w(w_str)
    return pterm.Atom(val)

# -----------------------------
# Convert from Prolog to Python
# -----------------------------

def int_w_of_int_p(space, p_int):
    # XXX type check
    return space.newint(p_int.num)

def float_w_of_float_p(space, p_float):
    # XXX type check
    return space.newfloat(p_float.floatval)

def long_w_of_bigint_p(space, p_bigint):
    # XXX type check
    return space.newlong_from_rbigint(p_bigint.value)

def str_w_of_atom_p(space, p_atom):
    # XXX type check
    return space.wrap(p_atom._signature.name)
