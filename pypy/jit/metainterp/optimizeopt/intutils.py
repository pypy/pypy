from pypy.rlib.rarithmetic import ovfcheck, ovfcheck_lshift, LONG_BIT

class IntBound(object):
    _attrs_ = ('has_upper', 'has_lower', 'upper', 'lower')
    
    def __init__(self, lower, upper):
        self.has_upper = True
        self.has_lower = True
        self.upper = upper
        self.lower = lower

    # Returns True if the bound was updated
    def make_le(self, other):
        if other.has_upper:
            if not self.has_upper or other.upper < self.upper:
                self.has_upper = True
                self.upper = other.upper
                return True
        return False

    def make_lt(self, other):
        return self.make_le(other.add(-1))
 
    def make_ge(self, other):
        if other.has_lower:
            if not self.has_lower or other.lower > self.lower:
                self.has_lower = True
                self.lower = other.lower
                return True
        return False

    def make_gt(self, other):
        return self.make_ge(other.add(1))

    def make_constant(self, value):
        self.has_lower = True
        self.has_upper = True
        self.lower = value
        self.upper = value

    def make_unbounded(self):
        self.has_lower = False
        self.has_upper = False

    def bounded(self):
        return self.has_lower and self.has_upper

    def known_lt(self, other):
        if self.has_upper and other.has_lower and self.upper < other.lower:
            return True
        return False

    def known_le(self, other):
        if self.has_upper and other.has_lower and self.upper <= other.lower:
            return True
        return False

    def known_gt(self, other):
        return other.known_lt(self)

    def known_ge(self, other):
        return other.known_le(self)

    def intersect(self, other):
        r = False

        if other.has_lower:
            if other.lower > self.lower or not self.has_lower:
                self.lower = other.lower
                self.has_lower = True
                r = True

        if other.has_upper:
            if other.upper < self.upper or not self.has_upper:
                self.upper = other.upper
                self.has_upper = True
                r = True

        return r
    
    def add(self, offset):
        res = self.clone()
        try:
            res.lower = ovfcheck(res.lower + offset)
        except OverflowError:
            res.has_lower = False
        try:
            res.upper = ovfcheck(res.upper + offset)
        except OverflowError:
            res.has_upper = False
        return res

    def mul(self, value):
        return self.mul_bound(IntBound(value, value))
    
    def add_bound(self, other):
        res = self.clone()
        if other.has_upper:
            try:
                res.upper = ovfcheck(res.upper + other.upper)
            except OverflowError:
                res.has_upper = False
        else:
            res.has_upper = False
        if other.has_lower:
            try:
                res.lower = ovfcheck(res.lower + other.lower)
            except OverflowError:
                res.has_lower = False            
        else:
            res.has_lower = False
        return res

    def sub_bound(self, other):
        res = self.clone()
        if other.has_lower:
            try:
                res.upper = ovfcheck(res.upper - other.lower)
            except OverflowError:
                res.has_upper = False
        else:
            res.has_upper = False
        if other.has_upper:
            try:
                res.lower = ovfcheck(res.lower - other.upper)
            except OverflowError:
                res.has_lower = False            
        else:
            res.has_lower = False
        return res

    def mul_bound(self, other):
        if self.has_upper and self.has_lower and \
           other.has_upper and other.has_lower:
            try:
                vals = (ovfcheck(self.upper * other.upper),
                        ovfcheck(self.upper * other.lower),
                        ovfcheck(self.lower * other.upper),
                        ovfcheck(self.lower * other.lower))
                return IntBound(min4(vals), max4(vals))
            except OverflowError:
                return IntUnbounded()
        else:
            return IntUnbounded()

    def div_bound(self, other):
        if self.has_upper and self.has_lower and \
           other.has_upper and other.has_lower and \
           not other.contains(0):
            try:
                vals = (ovfcheck(self.upper / other.upper),
                        ovfcheck(self.upper / other.lower),
                        ovfcheck(self.lower / other.upper),
                        ovfcheck(self.lower / other.lower))
                return IntBound(min4(vals), max4(vals))
            except OverflowError:
                return IntUnbounded()
        else:
            return IntUnbounded()

    def lshift_bound(self, other):
        if self.has_upper and self.has_lower and \
           other.has_upper and other.has_lower and \
           other.known_ge(IntBound(0, 0)) and \
           other.known_lt(IntBound(LONG_BIT, LONG_BIT)):
            try:
                vals = (ovfcheck_lshift(self.upper, other.upper),
                        ovfcheck_lshift(self.upper, other.lower),
                        ovfcheck_lshift(self.lower, other.upper),
                        ovfcheck_lshift(self.lower, other.lower))
                return IntBound(min4(vals), max4(vals))
            except (OverflowError, ValueError):
                return IntUnbounded()
        else:
            return IntUnbounded()

    def rshift_bound(self, other):
        if self.has_upper and self.has_lower and \
           other.has_upper and other.has_lower and \
           other.known_ge(IntBound(0, 0)) and \
           other.known_lt(IntBound(LONG_BIT, LONG_BIT)):
            vals = (self.upper >> other.upper,
                    self.upper >> other.lower,
                    self.lower >> other.upper,
                    self.lower >> other.lower)
            return IntBound(min4(vals), max4(vals))
        else:
            return IntUnbounded()


    def contains(self, val):
        if self.has_lower and val < self.lower:
            return False
        if self.has_upper and val > self.upper:
            return False
        return True

    def contains_bound(self, other):
        if other.has_lower:
            if not self.contains(other.lower):
                return False
        elif self.has_lower:
            return False
        if other.has_upper:
            if not self.contains(other.upper):
                return False
        elif self.has_upper:
            return False
        return True
        
    def __repr__(self):
        if self.has_lower:
            l = '%4d' % self.lower
        else:
            l = '-Inf'
        if self.has_upper:
            u = '%3d' % self.upper
        else:
            u = 'Inf'
        return '%s <= x <= %s' % (l, u)

    def clone(self):
        res = IntBound(self.lower, self.upper)
        res.has_lower = self.has_lower
        res.has_upper = self.has_upper
        return res
    
class IntUpperBound(IntBound):
    def __init__(self, upper):
        self.has_upper = True
        self.has_lower = False
        self.upper = upper
        self.lower = 0

class IntLowerBound(IntBound):
    def __init__(self, lower):
        self.has_upper = False
        self.has_lower = True
        self.upper = 0
        self.lower = lower

class IntUnbounded(IntBound):
    def __init__(self):
        self.has_upper = False
        self.has_lower = False
        self.upper = 0
        self.lower = 0        

def min4(t):
    return min(min(t[0], t[1]), min(t[2], t[3]))

def max4(t):
    return max(max(t[0], t[1]), max(t[2], t[3]))
