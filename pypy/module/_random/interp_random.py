from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, interp2app
from pypy.interpreter.baseobjspace import Wrappable
from pypy.rpython.rarithmetic import r_uint

from math import log as _log, exp as _exp, pi as _pi, e as _e
from math import sqrt as _sqrt, acos as _acos, cos as _cos, sin as _sin
from math import floor as _floor

def _verify(w_name, w_computed, w_expected):
    if abs(w_computed - w_expected) > 1e-7:
        raise OperationError(
            space.w_ValueError,
            space.wrap(
            "computed value for %s deviates too much "
            "(computed %g, expected %g)" % (w_name, w_computed, w_expected)))


NV_MAGICCONST = 4 * _exp(-0.5)/_sqrt(2.0)
_verify('NV_MAGICCONST', NV_MAGICCONST, 1.71552776992141)

TWOPI = 2.0*_pi
_verify('TWOPI', TWOPI, 6.28318530718)

LOG4 = _log(4.0)
_verify('LOG4', LOG4, 1.38629436111989)

SG_MAGICCONST = 1.0 + _log(4.5)
_verify('SG_MAGICCONST', SG_MAGICCONST, 2.50407739677627)

#del _verify

def descr_new__(space, w_subtype, w_anything=NoneNotWrapped):
    x = space.allocate_instance(W_Random, w_subtype)
    W_Random.__init__(x, space, w_anything)
    return space.wrap(x)

class W_Random(Wrappable):
    """A wrappable box around an interp level md5 object."""   
    VERSION = 1     # used by getstate/setstate
    
    def __init__(self, space, anything=NoneNotWrapped):
        """Initialize an instance.

        Optional argument x controls seeding, as for Random.seed().
        """
        self.seed(space, anything)
        
    
    def seed(self, space, w_a=NoneNotWrapped):
        """Initialize internal state from hashable object.

        None or no argument seeds from current time.

        If a is not None or an int or long, hash(a) is used instead.

        If a is an int or long, a is used directly.  Distinct values between
        0 and 27814431486575L inclusive are guaranteed to yield distinct
        internal states (this guarantee is specific to the default
        Wichmann-Hill generator).
        """
        if w_a is None:
            # Initialize from current time
            import time
            a = int(time.time() * 256)
        else:
            a = space.int_w(space.hash(w_a))

        a, x = divmod(a, 30268)
        a, y = divmod(a, 30306)
        a, z = divmod(a, 30322)
        self._seed = int(x)+1, int(y)+1, int(z)+1

        self.gauss_next = None
    seed.unwrap_spec = ['self', ObjSpace, W_Root]
    

    def random(self, space):
        """Get the next random number in the range [0.0, 1.0)."""

        # Wichman-Hill random number generator.
        #
        # Wichmann, B. A. & Hill, I. D. (1982)
        # Algorithm AS 183:
        # An efficient and portable pseudo-random number generator
        # Applied Statistics 31 (1982) 188-190
        #
        # see also:
        #        Correction to Algorithm AS 183
        #        Applied Statistics 33 (1984) 123
        #
        #        McLeod, A. I. (1985)
        #        A remark on Algorithm AS 183
        #        Applied Statistics 34 (1985),198-200

        # This part is thread-unsafe:
        # BEGIN CRITICAL SECTION
        x, y, z = self._seed
        x = (171 * x) % 30269
        y = (172 * y) % 30307
        z = (170 * z) % 30323
        self._seed = x, y, z
        # END CRITICAL SECTION

        # Note:  on a platform using IEEE-754 double arithmetic, this can
        # never return 0.0 (asserted by Tim; proof too long for a comment).
        randf = (x/30269.0 + y/30307.0 + z/30323.0) % 1.0
        return space.wrap(randf)
    random.unwrap_spec = ['self', ObjSpace]

    def getstate(self, space):
        """Return internal state; can be passed to setstate() later."""
        st = (self.VERSION, self._seed, self.gauss_next)
        return space.wrap(st)
    getstate.unwrap_spec = ['self', ObjSpace]

    def setstate(self, space, w_state):
        """Restore internal state from object returned by getstate()."""
        u_state = space.unwrap(w_state)
        print u_state
        version = u_state[0]
        if version == 1:
            self._seed = u_state[1]
            self.gauss_next = u_state[2]
        else:
            raise OperationError(space.w_ValueError,
                space.wrap("state with version %s passed to "
                             "Random.setstate() of version %s" %
                             (version, self.VERSION)))
    setstate.unwrap_spec = ['self', ObjSpace, W_Root]
    
    def jumpahead(self, space, w_n):
        """Act as if n calls to random() were made, but quickly.

        n is an int, greater than or equal to 0.

        Example use:  If you have 2 threads and know that each will
        consume no more than a million random numbers, create two Random
        objects r1 and r2, then do
            r2.setstate(r1.getstate())
            r2.jumpahead(1000000)
        Then r1 and r2 will use guaranteed-disjoint segments of the full
        period.
        """

        if not space.is_true(space.ge(w_n, space.wrap(0))):
            raise OperationError(space.w_ValueError,
                                 space.wrap("n must be >= 0"))
        x, y, z = self._seed
        x = (x * space.int_w(space.pow(space.wrap(171), w_n, space.wrap(30269)))) % 30269
        y = (y * space.int_w(space.pow(space.wrap(172), w_n, space.wrap(30307)))) % 30307
        z = (z * space.int_w(space.pow(space.wrap(170), w_n, space.wrap(30323)))) % 30323
        self._seed = x, y, z
    jumpahead.unwrap_spec = ['self', ObjSpace, W_Root]


    def _whseed(self, space, x=0, y=0, z=0):
        """Set the Wichmann-Hill seed from (x, y, z).

        These must be integers in the range [0, 256).
        """
        if not (0 <= x < 256 and 0 <= y < 256 and 0 <= z < 256):
            raise OperationError(space.w_ValueError,
                                 space.wrap('seeds must be in range(0, 256)'))
        if 0 == x == y == z:
            # Initialize from current time
            import time
            t = (int(time.time()) &0x7fffff) * 256
            t = (t&0xffffff) ^ (t>>24)
            t, x = divmod(t, 256)
            t, y = divmod(t, 256)
            t, z = divmod(t, 256)
        # Zero is a poor seed, so substitute 1
        self._seed = (x or 1, y or 1, z or 1)

        self.gauss_next = None
    _whseed.unwrap_spec = ['self', ObjSpace, int, int, int]
        
    def whseed(self, space, w_a=NoneNotWrapped):
        """Seed from hashable object's hash code.

        None or no argument seeds from current time.  It is not guaranteed
        that objects with distinct hash codes lead to distinct internal
        states.

        This is obsolete, provided for compatibility with the seed routine
        used prior to Python 2.1.  Use the .seed() method instead.
        """

        if w_a is None:
            self._whseed(ObjSpace)
            return
        else:
            a = space.int_w(space.hash(w_a))
            a, x = divmod(a, 256)
            a, y = divmod(a, 256)
            a, z = divmod(a, 256)
            x = (x + a) % 256 or 1
            y = (y + a) % 256 or 1
            z = (z + a) % 256 or 1
            self._whseed(ObjSpace, x, y, z)
    whseed.unwrap_spec = ['self', ObjSpace, W_Root]
        
## -------------------- pickle support  -------------------

    def __getstate__(self, space): # for pickle
        return self.getstate()

    def __setstate__(self, space, state):  # for pickle
        self.setstate(state)
        
    def randrange(self, space, start, w_stop=NoneNotWrapped, step=1):
        """Choose a random item from range(start, stop[, step]).

        This fixes the problem with randint() which includes the
        endpoint; in Python this is usually not what you want.
        Do not supply the 'int' and 'default' arguments.
        """
        # This code is a bit messy to make it fast for the
        # common case while still doing adequate error checking.
        if w_stop is None:
            if start > 0:
                return space.wrap(int(self.random() * start))
            raise OperationError(space.w_ValueError, 
                                 space.wrap("empty range for randrange()"))

        # stop argument supplied.
        istop = space.int_w(w_stop)
        if step == 1 and start < istop:
            fl = _floor(space.unwrap(self.random(space))*(istop - start))
            return space.wrap(int(start + fl))
        
        if step == 1:
            raise OperationError(space.w_ValueError, 
                                 space.wrap("empty range for randrange()"))

        # Non-unit step argument supplied.
        if step > 0:
            n = ((istop - start) + step - 1) / step
        elif step < 0:
            n = ((istop - start) + step + 1) / step
        else:
            raise OperationError(space.w_ValueError, 
                                 space.wrap("zero step for randrange()"))

        if n <= 0:
            raise OperationError(space.w_ValueError, 
                                 space.wrap("empty range for randrange()"))
        
        res = start + step*int(space.unwrap(self.random(space)) * n)
        return space.wrap(int(res))
    randrange.unwrap_spec = ['self', ObjSpace, int, W_Root, int]

    def randint(self, space, a, b):
        """Return random integer in range [a, b], including both end points.
        """
        return self.randrange(space, a, space.wrap(b+1))
    randint.unwrap_spec = ['self', ObjSpace, int, int]

    def choice(self, space, w_seq):
        """Choose a random element from a non-empty sequence."""
        length = space.int_w(space.len(w_seq))
        ind = int(space.unwrap(self.random(space)) * length)
        return space.getitem(w_seq, space.wrap(ind))
    choice.unwrap_spec = ['self', ObjSpace, W_Root]

    def shuffle(self, space, w_x, w_random=NoneNotWrapped):
        """x, random=random.random -> shuffle list x in place; return None.

        Optional arg random is a 0-argument function returning a random
        float in [0.0, 1.0); by default, the standard random.random.

        Note that for even rather small len(x), the total number of
        permutations of x is larger than the period of most random number
        generators; this implies that "most" permutations of a long
        sequence can never be generated.
        """

        if w_random is None:
            w_random = space.getattr(space.wrap(self), space.wrap('random'))
        length = space.unwrap(space.len(w_x))
            
        for i in xrange(length-1, 0, -1):
            # pick an element in x[:i+1] with which to exchange x[i]
            j = int(space.float_w(space.call_function(w_random)) * (i+1))
            w_i = space.wrap(i)
            w_j = space.wrap(j)
            w_xi = space.getitem(w_x, w_i)
            w_xj = space.getitem(w_x, w_j)
            space.setitem(w_x, w_i, w_xj)
            space.setitem(w_x, w_j, w_xi)
    shuffle.unwrap_spec = ['self', ObjSpace, W_Root, W_Root]
    
    def uniform(self, space, a, b):
        """Get a random number in the range [a, b)."""
        return space.wrap(a + (b-a) * space.unwrap(self.random(space)))    
    uniform.unwrap_spec = ['self', ObjSpace, int, int]

    def normalvariate(self, space, mu, sigma):
        """Normal distribution.

        mu is the mean, and sigma is the standard deviation.

        """
        # mu = mean, sigma = standard deviation

        # Uses Kinderman and Monahan method. Reference: Kinderman,
        # A.J. and Monahan, J.F., "Computer generation of random
        # variables using the ratio of uniform deviates", ACM Trans
        # Math Software, 3, (1977), pp257-260.
        while 1:
            u1 = space.unwrap(self.random(space))
            u2 = 1.0 - space.unwrap(self.random(space))
            z = NV_MAGICCONST*(u1-0.5)/u2
            zz = z*z/4.0
            if zz <= -_log(u2):
                break
        return space.wrap(mu + z*sigma)
    normalvariate.unwrap_spec = ['self', ObjSpace, float, float]
    
    
    def lognormvariate(self, space, mu, sigma):
        """Log normal distribution.

        If you take the natural logarithm of this distribution, you'll get a
        normal distribution with mean mu and standard deviation sigma.
        mu can have any value, and sigma must be greater than zero.

        """
        return space.wrap(_exp(space.unwrap(self.normalvariate(space, mu, sigma))))
    lognormvariate.unwrap_spec = ['self', ObjSpace, float, float]

    def cunifvariate(self, space, mean, arc):
        """Circular uniform distribution.

        mean is the mean angle, and arc is the range of the distribution,
        centered around the mean angle.  Both values must be expressed in
        radians.  Returned values range between mean - arc/2 and
        mean + arc/2 and are normalized to between 0 and pi.

        Deprecated in version 2.3.  Use:
            (mean + arc * (Random.random() - 0.5)) % Math.pi

        """
        # mean: mean angle (in radians between 0 and pi)
        # arc:  range of distribution (in radians between 0 and pi)

        return space.wrap((mean + arc * (space.unwrap(self.random(space)) - 0.5)) % _pi)
    cunifvariate.unwrap_spec = ['self', ObjSpace, float, float]

    def expovariate(self, space, lambd):
        """Exponential distribution.

        lambd is 1.0 divided by the desired mean.  (The parameter would be
        called "lambda", but that is a reserved word in Python.)  Returned
        values range from 0 to positive infinity.

        """
        # lambd: rate lambd = 1/mean
        # ('lambda' is a Python reserved word)

        random = self.random
        u = space.unwrap(random(space))
        while u <= 1e-7:
            u = space.unwrap(random(space))
        return space.wrap(-_log(u)/lambd)
    expovariate.unwrap_spec = ['self', ObjSpace, float]
    
    def vonmisesvariate(self, space, mu, kappa):
        """Circular data distribution.

        mu is the mean angle, expressed in radians between 0 and 2*pi, and
        kappa is the concentration parameter, which must be greater than or
        equal to zero.  If kappa is equal to zero, this distribution reduces
        to a uniform random angle over the range 0 to 2*pi.

        """
        # mu:    mean angle (in radians between 0 and 2*pi)
        # kappa: concentration parameter kappa (>= 0)
        # if kappa = 0 generate uniform random angle

        # Based upon an algorithm published in: Fisher, N.I.,
        # "Statistical Analysis of Circular Data", Cambridge
        # University Press, 1993.

        # Thanks to Magnus Kessler for a correction to the
        # implementation of step 4.

        random = self.random
        if kappa <= 1e-6:
            return TWOPI * space.unwrap(random(space))

        a = 1.0 + _sqrt(1.0 + 4.0 * kappa * kappa)
        b = (a - _sqrt(2.0 * a))/(2.0 * kappa)
        r = (1.0 + b * b)/(2.0 * b)

        while 1:
            u1 = space.unwrap(random(space))

            z = _cos(_pi * u1)
            f = (1.0 + r * z)/(r + z)
            c = kappa * (r - f)

            u2 = space.unwrap(random(space))

            if not (u2 >= c * (2.0 - c) and u2 > c * _exp(1.0 - c)):
                break

        u3 = space.unwrap(random(space))
        if u3 > 0.5:
            theta = (mu % TWOPI) + _acos(f)
        else:
            theta = (mu % TWOPI) - _acos(f)

        return space.wrap(theta)
    vonmisesvariate.unwrap_spec = ['self', ObjSpace, float, float]

    def gammavariate(self, space, alpha, beta):
        """Gamma distribution.  Not the gamma function!

        Conditions on the parameters are alpha > 0 and beta > 0.

        """

        # alpha > 0, beta > 0, mean is alpha*beta, variance is alpha*beta**2

        # Warning: a few older sources define the gamma distribution in terms
        # of alpha > -1.0
        if alpha <= 0.0 or beta <= 0.0:
            raise OperationError(space.w_ValueError, 
                                 space.wrap('gammavariate: alpha and beta must be > 0.0'))

        random = self.random
        if alpha > 1.0:

            # Uses R.C.H. Cheng, "The generation of Gamma
            # variables with non-integral shape parameters",
            # Applied Statistics, (1977), 26, No. 1, p71-74

            ainv = _sqrt(2.0 * alpha - 1.0)
            bbb = alpha - LOG4
            ccc = alpha + ainv

            while 1:
                u1 = space.unwrap(random(space))
                if not 1e-7 < u1 < .9999999:
                    continue
                u2 = 1.0 - space.unwrap(random(space))
                v = _log(u1/(1.0-u1))/ainv
                x = alpha*_exp(v)
                z = u1*u1*u2
                r = bbb+ccc*v-x
                if r + SG_MAGICCONST - 4.5*z >= 0.0 or r >= _log(z):
                    return space.wrap(x * beta)

        elif alpha == 1.0:
            # expovariate(1)
            u = space.unwrap(random(space))
            while u <= 1e-7:
                u = space.unwrap(random(space))
            return space.wrap(-_log(u) * beta)

        else:   # alpha is between 0 and 1 (exclusive)

            # Uses ALGORITHM GS of Statistical Computing - Kennedy & Gentle

            while 1:
                u = space.unwrap(random(space))
                b = (_e + alpha)/_e
                p = b*u
                if p <= 1.0:
                    x = pow(p, 1.0/alpha)
                else:
                    # p > 1
                    x = -_log((b-p)/alpha)
                u1 = space.unwrap(random(space))
                if not (((p <= 1.0) and (u1 > _exp(-x))) or
                          ((p > 1)  and  (u1 > pow(x, alpha - 1.0)))):
                    break
            return space.wrap(x * beta)
    gammavariate.unwrap_spec = ['self', ObjSpace, float, float]

    def stdgamma(self, space, alpha, ainv, bbb, ccc):
        # This method was (and shall remain) undocumented.
        # This method is deprecated
        # for the following reasons:
        # 1. Returns same as .gammavariate(alpha, 1.0)
        # 2. Requires caller to provide 3 extra arguments
        #    that are functions of alpha anyway
        # 3. Can't be used for alpha < 0.5

        # ainv = sqrt(2 * alpha - 1)
        # bbb = alpha - log(4)
        # ccc = alpha + ainv
        
        # XXX there is no warning support in pypy !
        print "The stdgamma function is deprecated; use gammavariate() instead"

        return self.gammavariate(space, alpha, 1.0)
    stdgamma.unwrap_spec = ['self', ObjSpace, float, float, float, float]
        
    def gauss(self, space, mu, sigma):
        """Gaussian distribution.

        mu is the mean, and sigma is the standard deviation.  This is
        slightly faster than the normalvariate() function.

        Not thread-safe without a lock around calls.

        """

        # When x and y are two variables from [0, 1), uniformly
        # distributed, then
        #
        #    cos(2*pi*x)*sqrt(-2*log(1-y))
        #    sin(2*pi*x)*sqrt(-2*log(1-y))
        #
        # are two *independent* variables with normal distribution
        # (mu = 0, sigma = 1).
        # (Lambert Meertens)
        # (corrected version; bug discovered by Mike Miller, fixed by LM)

        # Multithreading note: When two threads call this function
        # simultaneously, it is possible that they will receive the
        # same return value.  The window is very small though.  To
        # avoid this, you have to use a lock around all calls.  (I
        # didn't want to slow this down in the serial case by using a
        # lock here.)

        random = self.random
        z = self.gauss_next
        self.gauss_next = None
        if z is None:
            x2pi = space.unwrap(random(space)) * TWOPI
            g2rad = _sqrt(-2.0 * _log(1.0 - space.unwrap(random(space))))
            z = _cos(x2pi) * g2rad
            self.gauss_next = _sin(x2pi) * g2rad

        return space.wrap(mu + z*sigma)
    gauss.unwrap_spec = ['self', ObjSpace, float, float]

## -------------------- beta --------------------
## See
## http://sourceforge.net/bugs/?func=detailbug&bug_id=130030&group_id=5470
## for Ivan Frohne's insightful analysis of why the original implementation:
##
##    def betavariate(self, alpha, beta):
##        # Discrete Event Simulation in C, pp 87-88.
##
##        y = self.expovariate(alpha)
##        z = self.expovariate(1.0/beta)
##        return z/(y+z)
##
## was dead wrong, and how it probably got that way.

    def betavariate(self, space, alpha, beta):
        """Beta distribution.

        Conditions on the parameters are alpha > -1 and beta} > -1.
        Returned values range between 0 and 1.

        """

        # This version due to Janne Sinkkonen, and matches all the std
        # texts (e.g., Knuth Vol 2 Ed 3 pg 134 "the beta distribution").
        y = space.unwrap(self.gammavariate(space, alpha, 1.))
        if y == 0:
            return space.wrap(0.0)
        else:
            return space.wrap(y / (y + space.unwrap(self.gammavariate(space, beta, 1.))))
    betavariate.unwrap_spec = ['self', ObjSpace, float, float]

    def paretovariate(self, space, alpha):
        """Pareto distribution.  alpha is the shape parameter."""
        # Jain, pg. 495

        u = 1.0 - space.unwrap(self.random(space))
        return space.wrap(1.0 / pow(u, 1.0/alpha))
    paretovariate.unwrap_spec = ['self', ObjSpace, float]
    
    def weibullvariate(self, space, alpha, beta):
        """Weibull distribution.

        alpha is the scale parameter and beta is the shape parameter.

        """
        # Jain, pg. 499; bug fix courtesy Bill Arms

        u = 1.0 - space.unwrap(self.random(space))
        return space.wrap(alpha * pow(-_log(u), 1.0/beta))
    weibullvariate.unwrap_spec = ['self', ObjSpace, float, float]
    

W_Random.typedef = TypeDef("W_Random",
    __new__ = interp2app(descr_new__),
    seed = interp2app(W_Random.seed),
    random = interp2app(W_Random.random),
    getstate = interp2app(W_Random.getstate),
    setstate = interp2app(W_Random.setstate),
    jumpahead = interp2app(W_Random.jumpahead),
    _whseed = interp2app(W_Random._whseed),
    whseed = interp2app(W_Random.whseed),
    randrange = interp2app(W_Random.randrange),
    randint = interp2app(W_Random.randint),
    choice = interp2app(W_Random.choice),
    shuffle = interp2app(W_Random.shuffle),
    uniform = interp2app(W_Random.uniform),
    normalvariate = interp2app(W_Random.normalvariate),
    lognormvariate = interp2app(W_Random.lognormvariate),
    cunifvariate = interp2app(W_Random.cunifvariate),
    expovariate = interp2app(W_Random.expovariate),
    vonmisesvariate = interp2app(W_Random.vonmisesvariate),
    gammavariate = interp2app(W_Random.gammavariate),
    gauss = interp2app(W_Random.gauss),
    betavariate = interp2app(W_Random.betavariate),
    paretovariate = interp2app(W_Random.paretovariate),
    weibullvariate = interp2app(W_Random.weibullvariate),
    stdgamma = interp2app(W_Random.stdgamma),
                            )
_inst_map = {}

def get_random_method(space, attrname):
    try:
        w_self = _inst_map[space]
    except KeyError:
        _inst_map[space] = w_self = W_Random(space, None)
    w_method = space.getattr(w_self,space.wrap(attrname))
    return w_method
