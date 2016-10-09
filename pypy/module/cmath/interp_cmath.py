import math
from rpython.rlib.objectmodel import specialize
from rpython.tool.sourcetools import func_with_new_name
from pypy.interpreter.error import oefmt
from pypy.module.cmath import names_and_docstrings
from rpython.rlib import rcomplex

pi = math.pi
e  = math.e


@specialize.arg(0)
def call_c_func(c_func, space, x, y):
    try:
        result = c_func(x, y)
    except ValueError:
        raise oefmt(space.w_ValueError, "math domain error")
    except OverflowError:
        raise oefmt(space.w_OverflowError, "math range error")
    return result


def unaryfn(c_func):
    def wrapper(space, w_z):
        x, y = space.unpackcomplex(w_z)
        resx, resy = call_c_func(c_func, space, x, y)
        return space.newcomplex(resx, resy)
    #
    name = c_func.func_name
    assert name.startswith('c_')
    wrapper.func_doc = names_and_docstrings[name[2:]]
    fnname = 'wrapped_' + name[2:]
    globals()[fnname] = func_with_new_name(wrapper, fnname)
    return c_func


def c_neg(x, y):
    return rcomplex.c_neg(x,y)


@unaryfn
def c_sqrt(x, y):
    return rcomplex.c_sqrt(x,y)

@unaryfn
def c_acos(x, y):
    return rcomplex.c_acos(x,y)

@unaryfn
def c_acosh(x, y):
    return rcomplex.c_acosh(x,y)

@unaryfn
def c_asin(x, y):
    return rcomplex.c_asin(x,y)

@unaryfn
def c_asinh(x, y):
    return rcomplex.c_asinh(x,y)

@unaryfn
def c_atan(x, y):
    return rcomplex.c_atan(x,y)

@unaryfn
def c_atanh(x, y):
    return rcomplex.c_atanh(x,y)

@unaryfn
def c_log(x, y):
    return rcomplex.c_log(x,y)

_inner_wrapped_log = wrapped_log

def wrapped_log(space, w_z, w_base=None):
    w_logz = _inner_wrapped_log(space, w_z)
    if w_base is not None:
        w_logbase = _inner_wrapped_log(space, w_base)
        return space.truediv(w_logz, w_logbase)
    else:
        return w_logz
wrapped_log.func_doc = _inner_wrapped_log.func_doc


@unaryfn
def c_log10(x, y):
    return rcomplex.c_log10(x,y)

@unaryfn
def c_exp(x, y):
    return rcomplex.c_exp(x,y)

@unaryfn
def c_cosh(x, y):
    return rcomplex.c_cosh(x,y)

@unaryfn
def c_sinh(x, y):
    return rcomplex.c_sinh(x,y)

@unaryfn
def c_tanh(x, y):
    return rcomplex.c_tanh(x,y)

@unaryfn
def c_cos(x, y):
    return rcomplex.c_cos(x,y)

@unaryfn
def c_sin(x, y):
    return rcomplex.c_sin(x,y)

@unaryfn
def c_tan(x, y):
    return rcomplex.c_tan(x,y)

def c_rect(r, phi):
    return rcomplex.c_rect(r,phi)

def wrapped_rect(space, w_x, w_y):
    x = space.float_w(w_x)
    y = space.float_w(w_y)
    resx, resy = call_c_func(c_rect, space, x, y)
    return space.newcomplex(resx, resy)
wrapped_rect.func_doc = names_and_docstrings['rect']


def c_phase(x, y):
    return rcomplex.c_phase(x,y)

def wrapped_phase(space, w_z):
    x, y = space.unpackcomplex(w_z)
    result = call_c_func(c_phase, space, x, y)
    return space.newfloat(result)
wrapped_phase.func_doc = names_and_docstrings['phase']


def c_abs(x, y):
    return rcomplex.c_abs(x,y)

def c_polar(x, y):
    return rcomplex.c_polar(x,y)

def wrapped_polar(space, w_z):
    x, y = space.unpackcomplex(w_z)
    resx, resy = call_c_func(c_polar, space, x, y)
    return space.newtuple([space.newfloat(resx), space.newfloat(resy)])
wrapped_polar.func_doc = names_and_docstrings['polar']


def c_isinf(x, y):
    return rcomplex.c_isinf(x,y)

def wrapped_isinf(space, w_z):
    x, y = space.unpackcomplex(w_z)
    res = c_isinf(x, y)
    return space.newbool(res)
wrapped_isinf.func_doc = names_and_docstrings['isinf']


def c_isnan(x, y):
    return rcomplex.c_isnan(x,y)

def wrapped_isnan(space, w_z):
    x, y = space.unpackcomplex(w_z)
    res = c_isnan(x, y)
    return space.newbool(res)
wrapped_isnan.func_doc = names_and_docstrings['isnan']
