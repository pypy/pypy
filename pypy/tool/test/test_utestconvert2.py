import autopath
from pypy.tool.utestconvert import rewrite_utest
import unittest

class Testit(unittest.TestCase):
    def test(self):
        self.assertEquals(rewrite_utest("badger badger badger"),
                          "badger badger badger")

        self.assertEquals(rewrite_utest(
            "self.assertRaises(excClass, callableObj, *args, **kwargs)"
            ),
            "raises(excClass, callableObj, *args, **kwargs)"
                          )

        self.assertEquals(rewrite_utest(
            """
            self.failUnlessRaises(TypeError, func, 42, **{'arg1': 23})
            """
            ),
            """
            raises(TypeError, func, 42, **{'arg1': 23})
            """
                          )
        self.assertEquals(rewrite_utest(
            """
            self.assertRaises(TypeError,
                              func,
                              mushroom)
            """
            ),
            """
            raises(TypeError,
                              func,
                              mushroom)
            """
                          )
        self.assertEquals(rewrite_utest("self.fail()"), "raise AssertionError")
        self.assertEquals(rewrite_utest("self.fail('mushroom, mushroom')"),
                          "raise AssertionError, 'mushroom, mushroom'")
        self.assertEquals(rewrite_utest("self.assert_(x)"), "assert x")
        self.assertEquals(rewrite_utest("self.failUnless(func(x)) # XXX"),
                          "assert func(x) # XXX")
        
        self.assertEquals(rewrite_utest(
            """
            self.assert_(1 + f(y)
                         + z) # multiline, keep parentheses
            """
            ),
            """
            assert (1 + f(y)
                         + z) # multiline, keep parentheses
            """
                          )

        self.assertEquals(rewrite_utest("self.assert_(0, 'badger badger')"),
                          "assert 0, 'badger badger'")

        self.assertEquals(rewrite_utest("self.assert_(0, '''badger badger''')"),
                          "assert 0, '''badger badger'''")

        self.assertEquals(rewrite_utest(
            r"""
            self.assert_(0,
                 'Meet the badger.\n')
            """
            ),
            r"""
            assert 0, (
                 'Meet the badger.\n')
            """
                          )
        
        self.assertEquals(rewrite_utest(
            r"""
            self.failIf(0 + 0
                          + len('badger\n')
                          + 0, '''badger badger badger badger
                                 mushroom mushroom
                                 Snake!  Ooh a snake!
                              ''') # multiline, must move the parens
            """
            ),
            r"""
            assert not (0 + 0
                          + len('badger\n')
                          + 0), '''badger badger badger badger
                                 mushroom mushroom
                                 Snake!  Ooh a snake!
                              ''' # multiline, must move the parens
            """
                          )

        self.assertEquals(rewrite_utest("self.assertEquals(0, 0)"),
                          "assert 0 == 0")
        
        self.assertEquals(rewrite_utest(
            r"""
            self.assertEquals(0,
                 'Run away from the snake.\n')
            """
            ),
            r"""
            assert 0 == (
                 'Run away from the snake.\n')
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.assertEquals(badger + 0
                              + mushroom
                              + snake, 0)
            """
            ),
            """
            assert (badger + 0
                              + mushroom
                              + snake) == 0
            """
                          )
                            
        self.assertEquals(rewrite_utest(
            """
            self.assertNotEquals(badger + 0
                              + mushroom
                              + snake,
                              mushroom
                              - badger)
            """
            ),
            """
            assert (badger + 0
                              + mushroom
                              + snake) != (
                              mushroom
                              - badger)
            """
                          )

        self.assertEqual(rewrite_utest(
            """
            self.assertEquals(badger(),
                              mushroom()
                              + snake(mushroom)
                              - badger())
            """
            ),
            """
            assert badger() == (
                              mushroom()
                              + snake(mushroom)
                              - badger())
            """
                         )
        self.assertEquals(rewrite_utest("self.failIfEqual(0, 0)"),
                          "assert not 0 == 0")

        self.assertEquals(rewrite_utest("self.failUnlessEqual(0, 0)"),
                          "assert 0 == 0")

        self.assertEquals(rewrite_utest(
            """
            self.failUnlessEqual(mushroom()
                                 + mushroom()
                                 + mushroom(), '''badger badger badger
                                 badger badger badger badger
                                 badger badger badger badger
                                 ''') # multiline, must move the parens
            """
            ),
            """
            assert (mushroom()
                                 + mushroom()
                                 + mushroom()) == '''badger badger badger
                                 badger badger badger badger
                                 badger badger badger badger
                                 ''' # multiline, must move the parens
            """
                          )

                                   
        self.assertEquals(rewrite_utest(
            """
            self.assertEquals('''snake snake snake
                                 snake snake snake''', mushroom)
            """
            ),
            """
            assert '''snake snake snake
                                 snake snake snake''' == mushroom
            """
                          )
        
        self.assertEquals(rewrite_utest(
            """
            self.assertEquals(badger(),
                              snake(), 'BAD BADGER')
            """
            ),
            """
            assert badger() == (
                              snake()), 'BAD BADGER'
            """
                          )
        
        self.assertEquals(rewrite_utest(
            """
            self.assertNotEquals(badger(),
                              snake()+
                              snake(), 'POISONOUS MUSHROOM!\
                              Ai! I ate a POISONOUS MUSHROOM!!')
            """
            ),
            """
            assert badger() != (
                              snake()+
                              snake()), 'POISONOUS MUSHROOM!\
                              Ai! I ate a POISONOUS MUSHROOM!!'
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.assertEquals(badger(),
                              snake(), '''BAD BADGER
                              BAD BADGER
                              BAD BADGER'''
                              )
            """
            ),
            """
            assert badger() == (
                              snake()), ( '''BAD BADGER
                              BAD BADGER
                              BAD BADGER'''
                              )
            """
                        )

        self.assertEquals(rewrite_utest(
            """
            self.assertEquals('''BAD BADGER
                              BAD BADGER
                              BAD BADGER''', '''BAD BADGER
                              BAD BADGER
                              BAD BADGER''')
            """
            ),
            """
            assert '''BAD BADGER
                              BAD BADGER
                              BAD BADGER''' == '''BAD BADGER
                              BAD BADGER
                              BAD BADGER'''
            """
                        )

        self.assertEquals(rewrite_utest(
            """
            self.assertEquals('''GOOD MUSHROOM
                              GOOD MUSHROOM
                              GOOD MUSHROOM''',
                              '''GOOD MUSHROOM
                              GOOD MUSHROOM
                              GOOD MUSHROOM''',
                              ''' FAILURE
                              FAILURE
                              FAILURE''')
            """
            ),
            """
            assert '''GOOD MUSHROOM
                              GOOD MUSHROOM
                              GOOD MUSHROOM''' == (
                              '''GOOD MUSHROOM
                              GOOD MUSHROOM
                              GOOD MUSHROOM'''), (
                              ''' FAILURE
                              FAILURE
                              FAILURE''')
            """
                        )

        self.assertEquals(rewrite_utest(
            """
            self.assertAlmostEquals(first, second, 5, 'A Snake!')
            """
            ),
            """
            assert round(first - second, 5) == 0, 'A Snake!'
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.assertAlmostEquals(first, second, 120)
            """
            ),
            """
            assert round(first - second, 120) == 0
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.assertAlmostEquals(first, second)
            """
            ),
            """
            assert round(first - second, 7) == 0
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.assertAlmostEqual(first, second, 5, '''A Snake!
            Ohh A Snake!  A Snake!!
            ''')
            """
            ),
            """
            assert round(first - second, 5) == 0, '''A Snake!
            Ohh A Snake!  A Snake!!
            '''
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.assertNotAlmostEqual(first, second, 5, 'A Snake!')
            """
            ),
            """
            assert round(first - second, 5) != 0, 'A Snake!'
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.failIfAlmostEqual(first, second, 5, 'A Snake!')
            """
            ),
            """
            assert not round(first - second, 5) == 0, 'A Snake!'
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.failIfAlmostEqual(first, second, 5, 6, 7, 'Too Many Args')
            """
            ),
            """
            self.failIfAlmostEqual(first, second, 5, 6, 7, 'Too Many Args')
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.failUnlessAlmostEquals(first, second, 5, 'A Snake!')
            """
            ),
            """
            assert round(first - second, 5) == 0, 'A Snake!'
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            self.assertAlmostEquals(now do something reasonable ..()
            oops, I am inside a comment as a ''' string, and the fname was
            mentioned in passing, leaving us with something that isn't an
            expression ... will this blow up?
            """
            ),
            """
            self.assertAlmostEquals(now do something reasonable ..()
            oops, I am inside a comment as a ''' string, and the fname was
            mentioned in passing, leaving us with something that isn't an
            expression ... will this blow up?
            """
                          )

        self.assertEquals(rewrite_utest(
            """
            happily inside a comment I write self.assertEquals(0, badger)
            now will this one get rewritten?
            """
            ),
            """
            happily inside a comment I write self.assertEquals(0, badger)
            now will this one get rewritten?
            """
                          )
        
        self.assertEquals(rewrite_utest(
            """
        self.failUnless('__builtin__' in modules, "An entry for __builtin__ "
                                                    "is not in sys.modules.")
            """
            ),
            """
        assert '__builtin__' in modules, ( "An entry for __builtin__ "
                                                    "is not in sys.modules.")
            """
                           )
        
        # two unittests on the same line separated by a semi-colon is
        # only half-converted.  Just so you know.
        self.assertEquals(rewrite_utest(
            """
            self.assertEquals(0, 0); self.assertEquals(1, 1) #not 2 per line!
            """
            ),
            """
            assert 0 == 0; self.assertEquals(1, 1) #not 2 per line!
            """
                           )
            
                              
if __name__ == '__main__':
    unittest.main()
