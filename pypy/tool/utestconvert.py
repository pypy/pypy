import re
import unittest
import parser
import os

d={}

#  d is the dictionary of unittest changes, keyed to the old name
#  used by unittest.  d['new'] is the new replacement function.
#  arg_nums is the possible number of arguments to the unittest
#  function.  The last argument to the arg_nums list is the position the
#  optional 'message' to print when the unittest fails should occur.
#  assertRaises and failUnlessRaises, unlike all the other functions
#  cannot have an special message to print, and can be passed any
#  number of arguments, so their arg_nums is [None] (in the absense of
# [Any].

#  'op' is the operator you will substitute, if applicable.


d['assertRaises'] = {'new': 'raises', 'op': '', 'arg_nums':[None]}
d['failUnlessRaises'] = d['assertRaises']

d['fail'] = {'new': 'raise AssertionError', 'op': '', 'arg_nums':[0,1]}

d['assert_'] = {'new': 'assert', 'op': '', 'arg_nums':[1,2]}
d['failIf'] = {'new': 'assert not','op': '', 'arg_nums':[1,2]}
d['failUnless'] = d['assert_']

d['assertEqual'] = {'new': 'assert', 'op': ' ==', 'arg_nums':[2,3]}
d['assertEquals'] = d['assertEqual']

d['assertNotEqual'] = {'new': 'assert', 'op': ' !=', 'arg_nums':[2,3]}
d['assertNotEquals'] = d['assertNotEqual']

d['failUnlessEqual'] = {'new': 'assert not', 'op': ' !=', 'arg_nums':[2,3]}

d['failIfEqual'] =  {'new': 'assert not', 'op': ' ==', 'arg_nums':[2,3]}

d['assertAlmostEqual'] = {'new': 'assert round', 'op':' ==','arg_nums':[2,3,4]}
d['assertAlmostEquals'] = d['assertAlmostEqual']

d['assertNotAlmostEqual'] = {'new':'assert round','op': ' !=',
                             'arg_nums':[2,3,4]}
d['assertNotAlmostEquals'] = d['assertNotAlmostEqual']

d['failIfAlmostEqual'] = {'new': 'assert not round', 'op': ' ==',
                          'arg_nums':[2,3,4]}

d['failUnlessAlmostEquals'] = {'new': 'assert not round', 'op': ' !=',
                               'arg_nums':[2,3,4]}

leading_spaces = re.compile(r'^(\s*)') # this never fails

pat = ''
for k in d.keys():  # this complicated pattern to match all unittests
    pat += '|' + r'^(\s*)' + 'self.' + k + r'\(' # \tself.whatever(

old_names = re.compile(pat[1:])
linesep=os.linesep

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
    utest = old_names.match(block)
    if utest:
        old = utest.group(0).lstrip()[5:-1]  # '\tself.blah(' -> 'blah'
        new = d[old]['new']
        op = d[old]['op']
        possible_args = d[old]['arg_nums']
        message_position = possible_args[-1]

        if not message_position: # just rename assertRaises
            return re.sub('self.'+old, new, block)

        indent, args, message, trailer = decompose_unittest(
            old, block, message_position)
   
        key = len(args)
        if message:
            key += 1
        
        if key is 0:  # fail()
            return indent + new + trailer

        elif key is 1 and key is message_position: # fail('unhappy message')
            return new + ', ' + message + trailer

        elif message_position is 4:  #assertAlmostEqual and freinds
            try:
                pos = args[2].lstrip()
            except IndexError:
                pos = 7
            string = '(' + args[0] + ' -' + args[1] + ', ' + pos + ')'
            string += op + ' 0'
            if message:
                string = string + ',' + message
            return indent + new + string + trailer
                
        else:
            string = op.join(args)
            if message:
                string = string + ',' + message

        return indent + new + ' ' + string + trailer
    else: # just copy uninteresting lines
        return block

def decompose_unittest(old, block, message_position):
    '''decompose the block into its component parts'''

    ''' returns indent, arglist, message, trailer 
        indent -- the indentation
        arglist -- the arguments to the unittest function
        message -- the optional message to print when it fails, and
        trailer -- any extra junk after the closing paren, such as #commment
    '''

    message = None

    indent = re.search(r'^(\s*)', block).group()
    pat = re.search('self.' + old + r'\(', block)
    try:
        args, trailer = get_expr(block[pat.end():], ')')
    except SyntaxError:  # this wasn't an expression.  ick.
        return indent, [block], message, None

    arglist = break_args(args, [])
    if arglist == ['']: # there weren't any
        return indent, [], message, trailer
    else:
        newl = []
        if len(arglist) == message_position:
            message = arglist[-1]
            arglist = arglist[:-1]
            if message.lstrip('\t ').startswith(linesep):
                message = '(' + message + ')'

        if arglist:
            for arg in arglist:
                try:
                    parser.expr(arg.lstrip('\t '))
                    # remove tab and space, but keep newline.
                except SyntaxError:
                    arg = '(' + arg + ')'

                newl.append(arg)
            arglist = newl
         
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
            r"""
            self.assert_(1 + f(y)
                         + z) # multiline, keep parentheses
            """
            ),
            r"""
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
            assert 0 ==(
                 'Run away from the snake.\n')
            """
                          )

        self.assertEquals(rewrite_utest(
            r"""
            self.assertEquals(badger + 0
                              + mushroom
                              + snake, 0)
            """
            ),
            r"""
            assert (badger + 0
                              + mushroom
                              + snake) == 0
            """
                          )
                            
        self.assertEquals(rewrite_utest(
            r"""
            self.assertNotEquals(badger + 0
                              + mushroom
                              + snake,
                              mushroom
                              - badger)
            """
            ),
            r"""
            assert (badger + 0
                              + mushroom
                              + snake) !=(
                              mushroom
                              - badger)
            """
                          )

        self.assertEqual(rewrite_utest(
            r"""
            self.assertEquals(badger(),
                              mushroom()
                              + snake(mushroom)
                              - badger())
            """
            ),
            r"""
            assert badger() ==(
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
            r"""
            self.failUnlessEqual(mushroom()
                                 + mushroom()
                                 + mushroom(), '''badger badger badger
                                 badger badger badger badger
                                 badger badger badger badger
                                 ''') # multiline, must move the parens
            """
            ),
            r"""
            assert not (mushroom()
                                 + mushroom()
                                 + mushroom()) != '''badger badger badger
                                 badger badger badger badger
                                 badger badger badger badger
                                 ''' # multiline, must move the parens
            """
                          )

                                   
        self.assertEquals(rewrite_utest(
            r"""
            self.assertEquals('''snake snake snake
                                 snake snake snake''', mushroom)
            """
            ),
            r"""
            assert '''snake snake snake
                                 snake snake snake''' == mushroom
            """
                          )
        
        self.assertEquals(rewrite_utest(
            r"""
            self.assertEquals(badger(),
                              snake(), 'BAD BADGER')
            """
            ),
            r"""
            assert badger() ==(
                              snake()), 'BAD BADGER'
            """
                          )
        
        self.assertEquals(rewrite_utest(
            r"""
            self.assertNotEquals(badger(),
                              snake()+
                              snake(), 'POISONOUS MUSHROOM!\
                              Ai! I ate a POISONOUS MUSHROOM!!')
            """
            ),
            r"""
            assert badger() !=(
                              snake()+
                              snake()), 'POISONOUS MUSHROOM!\
                              Ai! I ate a POISONOUS MUSHROOM!!'
            """
                          )

        self.assertEquals(rewrite_utest(
            r"""
            self.assertEquals(badger(),
                              snake(), '''BAD BADGER
                              BAD BADGER
                              BAD BADGER'''
                              )
            """
            ),
            r"""
            assert badger() ==(
                              snake()), '''BAD BADGER
                              BAD BADGER
                              BAD BADGER'''
                              
            """
                        )
        self.assertEquals(rewrite_utest(
            r"""
            self.assertAlmostEquals(first, second, 5, 'A Snake!')
            """
            ),
            r"""
            assert round(first - second, 5) == 0, 'A Snake!'
            """
                          )
            
                              
if __name__ == '__main__':
    unittest.main()
    #for block in  blocksplitter('xxx.py'): print rewrite_utest(block)


