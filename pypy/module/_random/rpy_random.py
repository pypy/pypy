# this code is a version of the mersenne twister random number generator which
# is supposed to be used from RPython without the Python interpreter wrapping
# machinery etc.

# this is stolen from CPython's _randommodule.c

from pypy.rpython.rarithmetic import r_uint

N = 624
M = 397
MATRIX_A = r_uint(0x9908b0df) # constant vector a
UPPER_MASK  = r_uint(0x80000000) # most significant w-r bits
LOWER_MASK = r_uint(0x7fffffff) # least significant r bits

class Random(object):
    def __init__(self, seed=r_uint(0)):
        self.state = [r_uint(0)] * N
        self.index = 0
        if seed:
            self.init_genrand(seed)

    def init_genrand(self, s):
        mt = self.state
        mt[0]= s & r_uint(0xffffffff)
        for mti in range(1, N):
            mt[mti] = (r_uint(1812433253) *
                           (mt[mti - 1] ^ (mt[mti - 1] >> 30)) + mti)
            # See Knuth TAOCP Vol2. 3rd Ed. P.106 for multiplier.
            # In the previous versions, MSBs of the seed affect
            # only MSBs of the array mt[].
            # for >32 bit machines 
            mt[mti] &= r_uint(0xffffffff)
        self.index = mti + 1

    def init_by_array(self, init_key):
        key_length = len(init_key)
        mt = self.state
        self.init_genrand(r_uint(19650218))
        i = 1
        j = 0
        if N > key_length:
            max_k = N
        else:
            max_k = key_length
        for k in range(max_k, 0, -1):
            mt[i] = ((mt[i] ^
                         ((mt[i - 1] ^ (mt[i - 1] >> 30)) * r_uint(1664525)))
                     + init_key[j] + j) # non linear
            mt[i] &= r_uint(0xffffffff) # for WORDSIZE > 32 machines
            i += 1
            j += 1
            if i >= N:
                mt[0] = mt[N - 1]
                i = 1
            if j >= key_length:
                j = 0
        for k in range(N - 1, 0, -1):
            mt[i] = ((mt[i] ^
                        ((mt[i - 1] ^ (mt[i - 1] >> 30)) * r_uint(1566083941)))
                     - i) # non linear
            mt[i] &= r_uint(0xffffffff) # for WORDSIZE > 32 machines
            i += 1
            if (i>=N):
                mt[0] = mt[N - 1]
                i = 1
        mt[0] = r_uint(0x80000000)

    def genrand32(self):
        mag01 = [0, MATRIX_A]
        mt = self.state
        if self.index >= N:
            for kk in range(N - M):
                y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK)
                mt[kk] = mt[kk+M] ^ (y >> 1) ^ mag01[y & r_uint(1)]
            for kk in range(N - M, N - 1):
                y = (mt[kk] & UPPER_MASK) | (mt[kk + 1] & LOWER_MASK)
                mt[kk] = mt[kk + (M - N)] ^ (y >> 1) ^ mag01[y & r_uint(1)]
            y = (mt[N - 1] & UPPER_MASK) | (mt[0] & LOWER_MASK)
            mt[N - 1] = mt[M - 1] ^ (y >> 1) ^ mag01[y & r_uint(1)]
            self.index = 0
        y = mt[self.index]
        self.index += 1
        y ^= y >> 11
        y ^= (y << 7) & r_uint(0x9d2c5680)
        y ^= (y << 15) & r_uint(0xefc60000)
        y ^= (y >> 18)
        return y

    def random(self):
        a = self.genrand32() >> 5
        b = self.genrand32() >> 6
        return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0)

def main():
    import sys
    rnd = Random()
    rnd.init_genrand(1000)
    rnd.init_by_array([1, 2, 3, 4])
    print rnd.index

    for j in range(100):
        print rnd.state[j],
        if j % 7 == 6:
            print
    print "\n"
    for j in range(5):
        print rnd.genrand32(),
        if j % 7 == 6:
            print
    print

main()
