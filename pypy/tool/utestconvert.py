import re
import unittest
import parser

d={}

#  d is the dictionary of unittest changes, keyed to the old name
#  used by unittest.
#  d[old][0] is the new replacement function.
#  d[old][1] is the operator you will substitute, or '' if there is none.
#  d[old][2] is the possible number of arguments to the unittest
#  function.

# Old Unittest Name             new name         operator  # of args
d['assertRaises']           = ('raises',               '', ['Any'])
d['fail']                   = ('raise AssertionError', '', [0,1])
d['assert_']                = ('assert',               '', [1,2])
d['failIf']                 = ('assert not',           '', [1,2])
d['assertEqual']            = ('assert',            ' ==', [2,3])
d['failIfEqual']            = ('assert not',        ' ==', [2,3])
d['assertNotEqual']         = ('assert',            ' !=', [2,3])
d['failUnlessEqual']        = ('assert not',        ' !=', [2,3])
d['assertAlmostEqual']      = ('assert round',      ' ==', [2,3,4])
d['failIfAlmostEqual']      = ('assert not round',  ' ==', [2,3,4])
d['assertNotAlmostEqual']   = ('assert round',      ' !=', [2,3,4])
d['failUnlessAlmostEquals'] = ('assert not round',  ' !=', [2,3,4])

#  the list of synonyms
d['failUnlessRaises']      = d['assertRaises']
d['failUnless']            = d['assert_']
d['assertEquals']          = d['assertEqual']
d['assertNotEquals']       = d['assertNotEqual']
d['assertAlmostEquals']    = d['assertAlmostEqual']
d['assertNotAlmostEquals'] = d['assertNotAlmostEqual']

# set up the regular expressions we will need
leading_spaces = re.compile(r'^(\s*)') # this never fails

pat = ''
for k in d.keys():  # this complicated pattern to match all unittests
    pat += '|' + r'^(\s*)' + 'self.' + k + r'\(' # \tself.whatever(

old_names = re.compile(pat[1:])
linesep='\n'        # nobody will really try to convert files not read
                    # in text mode, will they?


def blocksplitter(filename):
    '''split a file into blocks that are headed by functions to rename'''
    fp = file(filename, 'r')
    blocklist = []
    blockstring = ''

    for line in fp:
        interesting = old_names.match(line)
        if interesting :
            if blockstring:
                blocklist.append(blockstring)
                blockstring = line # reset the block
        else:
            blockstring += line
            
    blocklist.append(blockstring)
    return blocklist

def rewrite_utest(block):
    '''rewrite every block to use the new utest functions'''

    '''returns the rewritten unittest, unless it ran into problems,
       in which case it just returns the block unchanged.
    '''
    utest = old_names.match(block)

    if not utest:
        return block

    old = utest.group(0).lstrip()[5:-1] # the name we want to replace
    new = d[old][0] # the name of the replacement function
    op  = d[old][1] # the operator you will use , or '' if there is none.
    possible_args = d[old][2]  # a list of the number of arguments the
                               # unittest function could possibly take.
                
    if new == 'raises': # just rename assertRaises & friends
        return re.sub('self.'+old, new, block)

    message_pos = possible_args[-1]
    # the remaining unittests can have an optional message to print
    # when they fail.  It is always the last argument to the function.

    try:
        indent, args, message, trailer = decompose_unittest(
            old, block, message_pos)
    except SyntaxError: # but we couldn't parse it!
        return block

    argnum = len(args)
    if message:
        argnum += 1

    if argnum not in possible_args:
        # sanity check - this one isn't real either
        return block

    if argnum is 0 or (argnum is 1 and argnum is message_pos): #unittest fail()
        string = ''
        if message:
            message = ' ' + message

    elif message_pos is 4:  # assertAlmostEqual & friends
        try:
            pos = args[2].lstrip()
        except IndexError:
            pos = '7' # default if none is specified
        string = '(%s -%s, %s)%s 0' % (args[0], args[1], pos, op )

    else: # assert_, assertEquals and all the rest
        string = ' ' + op.join(args)

    if message:
        string = string + ',' + message

    return indent + new + string + trailer

def decompose_unittest(old, block, message_pos):
    '''decompose the block into its component parts'''

    ''' returns indent, arglist, message, trailer 
        indent -- the indentation
        arglist -- the arguments to the unittest function
        message -- the optional message to print when it fails, and
        trailer -- any extra junk after the closing paren, such as #commment
    '''
 
    indent = re.search(r'^(\s*)', block).group()
    pat = re.search('self.' + old + r'\(', block)

    args, trailer = get_expr(block[pat.end():], ')')
    arglist = break_args(args, [])

    if arglist == ['']: # there weren't any
        return indent, [], [], trailer

    if len(arglist) != message_pos:
        message = None
    else:
        message = arglist[-1]
        arglist = arglist[:-1]
        if message.lstrip('\t ').startswith(linesep):
            message = '(' + message + ')'
            # In proper input, message is required to be a string.
            # Thus we can assume that however the string handled its
            # line continuations in the original unittest will also work
            # here.  But if the line happens to break  before the quoting
            # begins, you will need another set of parens, (or a backslash).

    if arglist:
        for i in range(len(arglist)):
            try:
                parser.expr(arglist[i].lstrip('\t '))
                # Again we want to enclose things that happen to have
                # a linebreak just before the new arg.
            except SyntaxError:
                if i == 0:
                    arglist[i] = '(' + arglist[i] + ')'
                else:
                    arglist[i] = ' (' + arglist[i] + ')'

    return indent, arglist, message, trailer

def break_args(args, arglist):
    '''recursively break a string into a list of arguments'''
    try:
        first, rest = get_expr(args, ',')
        if not rest:
            return arglist + [first]
        else:
            return [first] + break_args(rest, arglist)
    except SyntaxError:
        return arglist + [args]

def get_expr(s, char):
    '''split a string into an expression, and the rest of the string'''

    pos=[]
    for i in range(len(s)):
        if s[i] == char:
            pos.append(i)
    if pos == []:
        raise SyntaxError # we didn't find the expected char.  Ick.
     
    for p in pos:
        # make the python parser do the hard work of deciding which comma
        # splits the string into two expressions
        try:
            parser.expr('(' + s[:p] + ')')
            return s[:p], s[p+1:]
        except SyntaxError: # It's not an expression yet
            pass
    raise SyntaxError       # We never found anything that worked.

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
            assert 0,(
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
                          "assert not 0 != 0")

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
            assert not (mushroom()
                                 + mushroom()
                                 + mushroom()) != '''badger badger badger
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
                              snake()), '''BAD BADGER
                              BAD BADGER
                              BAD BADGER'''
                              
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
                              GOOD MUSHROOM'''),(
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
            assert not round(first - second, 5) != 0, 'A Snake!'
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
            
                              
if __name__ == '__main__':
    unittest.main()
    '''count = 1
    for block in  blocksplitter('xxx.py'):
        print 'START BLOCK', count
        print rewrite_utest(block)
        print 'END BLOCK', count
        print
        print
        count +=1
    '''
#for block in  blocksplitter('xxx.py'): print rewrite_utest(block)


