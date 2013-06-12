import prolog.interpreter.term as pterm

def int_p_of_int_w(space, int_w):
    int_val = space.int_w(int_w)
    int_p = pterm.Number(int_val)
    return int_p

def float_p_of_float_w(space, float_w):
    float_val = space.float_w(float_w)
    float_p = pterm.Float(float_val)
    return float_p
