import prolog.interpreter.term as pterm

def int_p_of_int_w(space, int_w):
    int_val = space.int_w(int_w)
    int_p = pterm.Number(int_val)
    return int_p
