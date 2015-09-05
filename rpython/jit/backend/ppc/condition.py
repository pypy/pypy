EQ = 0
NE = 1
LE = 2
GT = 3
LT = 4
GE = 5
SO = 6
NS = 7
cond_none = -1    # invalid

def negate(cond):
    return cond ^ 1

assert negate(EQ) == NE
assert negate(NE) == EQ
assert negate(LE) == GT
assert negate(GT) == LE
assert negate(LT) == GE
assert negate(GE) == LT
assert negate(SO) == NS
assert negate(NS) == SO

encoding = [
    (2, 12),   # EQ
    (2, 4),    # NE
    (1, 4),    # LE
    (1, 12),   # GT
    (0, 12),   # LT
    (0, 4),    # GE
    (3, 12),   # SO
    (3, 4),    # NS
]
