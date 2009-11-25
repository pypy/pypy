

def app_test_int_vs_long():
    def teq(a, b):
        assert a == b
        assert type(a) is type(b)

    # binary operators
    teq( 5  - 2  , 3  )
    teq( 5  - 2L , 3L )
    teq( 5L - 2  , 3L )
    teq( 5L - 2L , 3L )

    teq( 5  .__sub__(2 ), 3  )
    teq( 5  .__sub__(2L), NotImplemented )
    teq( 5L .__sub__(2 ), 3L )
    teq( 5L .__sub__(2L), 3L )

    teq( 5  .__rsub__(2 ), -3  )
    teq( 5  .__rsub__(2L), NotImplemented )
    teq( 5L .__rsub__(2 ), -3L )
    teq( 5L .__rsub__(2L), -3L )

    teq( 5  ** 2  , 25  )
    teq( 5  ** 2L , 25L )
    teq( 5L ** 2  , 25L )
    teq( 5L ** 2L , 25L )

    # ternary operator
    teq( pow( 5 , 3 , 100 ), 25 )
    teq( pow( 5 , 3 , 100L), 25L)
    teq( pow( 5 , 3L, 100 ), 25L)
    teq( pow( 5 , 3L, 100L), 25L)
    teq( pow( 5L, 3 , 100 ), 25L)
    teq( pow( 5L, 3 , 100L), 25L)
    teq( pow( 5L, 3L, 100 ), 25L)
    teq( pow( 5L, 3L, 100L), 25L)

    # two tests give a different result on PyPy and CPython.
    # however, there is no sane way that PyPy can match CPython here,
    # short of reintroducing three-way coercion...
    teq( 5  .__pow__(3 , 100 ), 25 )
    #teq( 5  .__pow__(3 , 100L), 25L or NotImplemented? )
    teq( 5  .__pow__(3L, 100 ), NotImplemented )
    teq( 5  .__pow__(3L, 100L), NotImplemented )
    teq( 5L .__pow__(3 , 100 ), 25L)
    teq( 5L .__pow__(3 , 100L), 25L)
    teq( 5L .__pow__(3L, 100 ), 25L)
    teq( 5L .__pow__(3L, 100L), 25L)
    
    teq( 5  .__rpow__(3 , 100 ), 43 )
    #teq( 5  .__rpow__(3 , 100L), 43L or NotImplemented? )
    teq( 5  .__rpow__(3L, 100 ), NotImplemented )
    teq( 5  .__rpow__(3L, 100L), NotImplemented )
    teq( 5L .__rpow__(3 , 100 ), 43L)
    teq( 5L .__rpow__(3 , 100L), 43L)
    teq( 5L .__rpow__(3L, 100 ), 43L)
    teq( 5L .__rpow__(3L, 100L), 43L)


def app_test_int_vs_float():
    def teq(a, b):
        assert a == b
        assert type(a) is type(b)

    # binary operators
    teq( 5  - 2    , 3   )
    teq( 5  - 2.0  , 3.0 )
    teq( 5.0 - 2   , 3.0 )
    teq( 5.0 - 2.0 , 3.0 )

    teq( 5   .__sub__(2  ), 3   )
    teq( 5   .__sub__(2.0), NotImplemented )
    teq( 5.0 .__sub__(2  ), 3.0 )
    teq( 5.0 .__sub__(2.0), 3.0 )

    teq( 5   .__rsub__(2  ), -3   )
    teq( 5   .__rsub__(2.0), NotImplemented )
    teq( 5.0 .__rsub__(2  ), -3.0 )
    teq( 5.0 .__rsub__(2.0), -3.0 )

    teq( 5   ** 2   , 25   )
    teq( 5   ** 2.0 , 25.0 )
    teq( 5.0 ** 2   , 25.0 )
    teq( 5.0 ** 2.0 , 25.0 )

    # pow() fails with a float argument anywhere
    raises(TypeError, pow, 5  , 3  , 100.0)
    raises(TypeError, pow, 5  , 3.0, 100  )
    raises(TypeError, pow, 5  , 3.0, 100.0)
    raises(TypeError, pow, 5.0, 3  , 100  )
    raises(TypeError, pow, 5.0, 3  , 100.0)
    raises(TypeError, pow, 5.0, 3.0, 100  )
    raises(TypeError, pow, 5.0, 3.0, 100.0)

    teq( 5 .__pow__(3.0, 100  ), NotImplemented )
    teq( 5 .__pow__(3.0, 100.0), NotImplemented )

    teq( 5 .__rpow__(3.0, 100  ), NotImplemented )
    teq( 5 .__rpow__(3.0, 100.0), NotImplemented )


def app_test_long_vs_float():
    def teq(a, b):
        assert a == b
        assert type(a) is type(b)

    # binary operators
    teq( 5L - 2.0  , 3.0 )
    teq( 5.0 - 2L  , 3.0 )

    teq( 5L  .__sub__(2.0), NotImplemented )
    teq( 5.0 .__sub__(2L ), 3.0 )

    teq( 5L  .__rsub__(2.0), NotImplemented )
    teq( 5.0 .__rsub__(2L ), -3.0 )

    teq( 5L  ** 2.0 , 25.0 )
    teq( 5.0 ** 2L  , 25.0 )

    # pow() fails with a float argument anywhere
    raises(TypeError, pow, 5L , 3L , 100.0)
    raises(TypeError, pow, 5L , 3.0, 100  )
    raises(TypeError, pow, 5L , 3.0, 100.0)
    raises(TypeError, pow, 5.0, 3L , 100  )
    raises(TypeError, pow, 5.0, 3L , 100.0)
    raises(TypeError, pow, 5.0, 3.0, 100  )
    raises(TypeError, pow, 5.0, 3.0, 100.0)

    teq( 5L .__pow__(3.0, 100L ), NotImplemented )
    teq( 5L .__pow__(3.0, 100.0), NotImplemented )

    teq( 5L .__rpow__(3.0, 100L ), NotImplemented )
    teq( 5L .__rpow__(3.0, 100.0), NotImplemented )
