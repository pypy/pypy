

from Numeric import zeros,nzeros,array
from Numeric import  Float



class TestArray:
    def test(self):
        a = zeros( (3,2), Float )
        assert (3,2) == a.shape

        b = zeros( (8,), Float )
        assert 0.==b[1]
        b[1]= 1.
        assert 1.==b[1]

    def testZeros(self):
        pass

TestArray().test()
TestArray().testZeros()
#### Original test above.

a=nzeros((2,7),Float)

assert (2,7)== a.shape
b=nzeros((10,),Float)
assert 0.==b[2]
b[3]=555
assert b[3]==555

def assertRaises(block,exception=Exception,shout='This should raise an exception'):
    try:
        block()
    except exception:
        pass
    else:
        assert False,shout


assertRaises(lambda :array(()),exception=ValueError)   #this should fail

a=array([1])
#assert a[0]==1   last test broken...
