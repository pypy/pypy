

from Numeric import zeros,array,ArrayType
from Numeric import  Float,TOWER_TYPES,TOWER_TYPES_VALUES





def assertRaises(block,exception=Exception,shout='This should raise an exception'):
    try:
        block()
    except exception:
        pass
    else:
        assert False,shout

"""
PyPy issues : >>>> 1=1 produces syntax error, but in script, takes AGES to eventually do this.
this is due to the size of the traceback which is generated in the script.

"""
#first we check the really simple, empty or minimal arrays
print "Checking scalars"
assert (0,)==array(()).shape
assert ()==array((1)).shape
assert isinstance( array(()), ArrayType)  and isinstance( array((1)), ArrayType )

#next we check the typecodes on these small examples
assert 'l'==array(()).typecode()
assert 'l'==array((1)).typecode()
assert 'd'==array((1.0)).typecode()

#we are not supporting complex numbers or any other objects yet
print "checking unsupported types"
assertRaises(lambda :array((1j)),TypeError)
assertRaises(lambda :array((1j,)),TypeError)
assertRaises(lambda :array(('a')),TypeError)

#now check accessing of values on empty array, and a scalar
#assertRaises(lambda :array(())[0],IndexError

print "DONE"






