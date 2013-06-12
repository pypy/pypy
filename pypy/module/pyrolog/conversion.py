import pypy.module.pyrolog.prolog.interpreter.term as pterm

def hello_world():
    return True

def int_p_of_int_w(space, int_w):
    int_val = space.int_w(int_w)
    int_p = pterm.Number(int_val)
    return int_p
