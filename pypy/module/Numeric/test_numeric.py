

from Numeric import zeros, Float

a = zeros( (3,2), Float )

print a.shape

assert a.shape == (3,2)

b = zeros( (8,), Float )

print b[1], b[2]
b[1] = 1.
print b[1], b[2]
