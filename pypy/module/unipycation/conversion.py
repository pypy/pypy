import prolog.interpreter.term as pterm

def int_p_of_int_w(space, int_w):
    int_val = space.int_w(int_w)
    int_p = pterm.Number(int_val)
    return int_p

def float_p_of_float_w(space, float_w):
    float_val = space.float_w(float_w)
    float_p = pterm.Float(float_val)
    return float_p

def float_p_of_float_w(space, float_w):
    float_val = space.float_w(float_w)
    float_p = pterm.Float(float_val)
    return float_p

def bigint_p_of_long_w(space, long_w):
    bigint_val = space.bigint_w(long_w)
    bigint_p = pterm.BigInt(bigint_val)
    return bigint_p

def atom_p_of_str_w(space, str_w):
    str_val = space.str_w(str_w)
    atom_p = pterm.Atom(str_val)
    return atom_p

