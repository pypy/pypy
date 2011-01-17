import math
from pypy.rlib.rarithmetic import isnan, isinf, copysign

# code to deal with special values (infinities, NaNs, ...)
#
# The special types can be:
ST_NINF    = 0         # negative infinity
ST_NEG     = 1         # negative finite number (nonzero)
ST_NZERO   = 2         # -0.
ST_PZERO   = 3         # +0.
ST_POS     = 4         # positive finite number (nonzero)
ST_PINF    = 5         # positive infinity
ST_NAN     = 6         # Not a Number

def special_type(d):
    if isnan(d):
        return ST_NAN
    elif isinf(d):
        if d > 0.0:
            return ST_PINF
        else:
            return ST_NINF
    else:
        if d != 0.0:
            if d > 0.0:
                return ST_POS
            else:
                return ST_NEG
        else:
            if copysign(1., d) == 1.:
                return ST_PZERO
            else:
                return ST_NZERO

def isfinite(d):
    return not isinf(d) and not isnan(d)


P   = math.pi
P14 = 0.25 * math.pi
P12 = 0.5 * math.pi
P34 = 0.75 * math.pi
INF = 1e200 * 1e200
N   = INF / INF
U   = -9.5426319407711027e33   # unlikely value, used as placeholder

def build_table(lst):
    table = []
    assert len(lst) == 49
    it = iter(lst)
    for j in range(7):
        row = []
        for i in range(7):
            (x, y) = it.next()
            row.append((x, y))
        table.append(row)
    return table

acos_special_values = build_table([
    (P34,INF), (P,INF),  (P,INF),  (P,-INF),  (P,-INF),  (P34,-INF), (N,INF),
    (P12,INF), (U,U),    (U,U),    (U,U),     (U,U),     (P12,-INF), (N,N),
    (P12,INF), (U,U),    (P12,0.), (P12,-0.), (U,U),     (P12,-INF), (P12,N),
    (P12,INF), (U,U),    (P12,0.), (P12,-0.), (U,U),     (P12,-INF), (P12,N),
    (P12,INF), (U,U),    (U,U),    (U,U),     (U,U),     (P12,-INF), (N,N),
    (P14,INF), (0.,INF), (0.,INF), (0.,-INF), (0.,-INF), (P14,-INF), (N,INF),
    (N,INF),   (N,N),    (N,N),    (N,N),     (N,N),     (N,-INF),   (N,N),
    ])

acosh_special_values = build_table([
    (INF,-P34), (INF,-P),  (INF,-P),  (INF,P),  (INF,P),  (INF,P34), (INF,N),
    (INF,-P12), (U,U),     (U,U),     (U,U),    (U,U),    (INF,P12), (N,N),
    (INF,-P12), (U,U),     (0.,-P12), (0.,P12), (U,U),    (INF,P12), (N,N),
    (INF,-P12), (U,U),     (0.,-P12), (0.,P12), (U,U),    (INF,P12), (N,N),
    (INF,-P12), (U,U),     (U,U),     (U,U),    (U,U),    (INF,P12), (N,N),
    (INF,-P14), (INF,-0.), (INF,-0.), (INF,0.), (INF,0.), (INF,P14), (INF,N),
    (INF,N),    (N,N),     (N,N),     (N,N),    (N,N),    (INF,N),   (N,N),
    ])

asinh_special_values = build_table([
    (-INF,-P14),(-INF,-0.),(-INF,-0.),(-INF,0.),(-INF,0.),(-INF,P14),(-INF,N),
    (-INF,-P12),(U,U),     (U,U),     (U,U),    (U,U),    (-INF,P12),(N,N),
    (-INF,-P12),(U,U),     (-0.,-0.), (-0.,0.), (U,U),    (-INF,P12),(N,N),
    (INF,-P12), (U,U),     (0.,-0.),  (0.,0.),  (U,U),    (INF,P12), (N,N),
    (INF,-P12), (U,U),     (U,U),     (U,U),    (U,U),    (INF,P12), (N,N),
    (INF,-P14), (INF,-0.), (INF,-0.), (INF,0.), (INF,0.), (INF,P14), (INF,N),
    (INF,N),    (N,N),     (N,-0.),   (N,0.),   (N,N),    (INF,N),   (N,N),
    ])

atanh_special_values = build_table([
    (-0.,-P12),(-0.,-P12),(-0.,-P12),(-0.,P12),(-0.,P12),(-0.,P12),(-0.,N),
    (-0.,-P12),(U,U),     (U,U),     (U,U),    (U,U),    (-0.,P12),(N,N),
    (-0.,-P12),(U,U),     (-0.,-0.), (-0.,0.), (U,U),    (-0.,P12),(-0.,N),
    (0.,-P12), (U,U),     (0.,-0.),  (0.,0.),  (U,U),    (0.,P12), (0.,N),
    (0.,-P12), (U,U),     (U,U),     (U,U),    (U,U),    (0.,P12), (N,N),
    (0.,-P12), (0.,-P12), (0.,-P12), (0.,P12), (0.,P12), (0.,P12), (0.,N),
    (0.,-P12), (N,N),     (N,N),     (N,N),    (N,N),    (0.,P12), (N,N),
    ])

log_special_values = build_table([
    (INF,-P34), (INF,-P),  (INF,-P),   (INF,P),   (INF,P),  (INF,P34), (INF,N),
    (INF,-P12), (U,U),     (U,U),      (U,U),     (U,U),    (INF,P12), (N,N),
    (INF,-P12), (U,U),     (-INF,-P),  (-INF,P),  (U,U),    (INF,P12), (N,N),
    (INF,-P12), (U,U),     (-INF,-0.), (-INF,0.), (U,U),    (INF,P12), (N,N),
    (INF,-P12), (U,U),     (U,U),      (U,U),     (U,U),    (INF,P12), (N,N),
    (INF,-P14), (INF,-0.), (INF,-0.),  (INF,0.),  (INF,0.), (INF,P14), (INF,N),
    (INF,N),    (N,N),     (N,N),      (N,N),     (N,N),    (INF,N),   (N,N),
    ])

sqrt_special_values = build_table([
    (INF,-INF), (0.,-INF), (0.,-INF), (0.,INF), (0.,INF), (INF,INF), (N,INF),
    (INF,-INF), (U,U),     (U,U),     (U,U),    (U,U),    (INF,INF), (N,N),
    (INF,-INF), (U,U),     (0.,-0.),  (0.,0.),  (U,U),    (INF,INF), (N,N),
    (INF,-INF), (U,U),     (0.,-0.),  (0.,0.),  (U,U),    (INF,INF), (N,N),
    (INF,-INF), (U,U),     (U,U),     (U,U),    (U,U),    (INF,INF), (N,N),
    (INF,-INF), (INF,-0.), (INF,-0.), (INF,0.), (INF,0.), (INF,INF), (INF,N),
    (INF,-INF), (N,N),     (N,N),     (N,N),    (N,N),    (INF,INF), (N,N),
    ])

exp_special_values = build_table([
    (0.,0.), (U,U), (0.,-0.),  (0.,0.),  (U,U), (0.,0.), (0.,0.),
    (N,N),   (U,U), (U,U),     (U,U),    (U,U), (N,N),   (N,N),
    (N,N),   (U,U), (1.,-0.),  (1.,0.),  (U,U), (N,N),   (N,N),
    (N,N),   (U,U), (1.,-0.),  (1.,0.),  (U,U), (N,N),   (N,N),
    (N,N),   (U,U), (U,U),     (U,U),    (U,U), (N,N),   (N,N),
    (INF,N), (U,U), (INF,-0.), (INF,0.), (U,U), (INF,N), (INF,N),
    (N,N),   (N,N), (N,-0.),   (N,0.),   (N,N), (N,N),   (N,N),
    ])

cosh_special_values = build_table([
    (INF,N), (U,U), (INF,0.),  (INF,-0.), (U,U), (INF,N), (INF,N),
    (N,N),   (U,U), (U,U),     (U,U),     (U,U), (N,N),   (N,N),
    (N,0.),  (U,U), (1.,0.),   (1.,-0.),  (U,U), (N,0.),  (N,0.),
    (N,0.),  (U,U), (1.,-0.),  (1.,0.),   (U,U), (N,0.),  (N,0.),
    (N,N),   (U,U), (U,U),     (U,U),     (U,U), (N,N),   (N,N),
    (INF,N), (U,U), (INF,-0.), (INF,0.),  (U,U), (INF,N), (INF,N),
    (N,N),   (N,N), (N,0.),    (N,0.),    (N,N), (N,N),   (N,N),
    ])
