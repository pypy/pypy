import re
import unittest
import parser
import os

d={}

#  d is the dictionary of unittest changes, keyed to the old name
#  used by unittest.  d['new'] is the new replacement function, and
#  d['change'] is one of the following functions
#           namechange_only   e.g.  assertRaises  becomes raises
#           fail_special      e.g.  fail() becomes raise AssertionError
#           strip_parens      e.g.  assert_(expr) becomes assert expr
#           comma_to_op       e.g.  assertEquals(l, r) becomes assert l == r
#           rounding          e.g.  assertAlmostEqual(l, r) becomes
#                                   assert round(l - r, 7) == 0
#  Finally, 'op' is the operator you will substitute, if applicable.
#  Got to define the dispatch functions first ....

def namechange_only(old, new, block, op):
    '''rename a function.  dictionary dispatched.'''
    return re.sub('self.'+old, new, block)

def fail_special(old, new, block, op):
    '''change fail function to raise AssertionError. dictionary dispatched. '''
    indent, expr, trailer = common_setup(old, block)
    
    if expr == '':  # fail()  --> raise AssertionError
         return indent + new + trailer
    else:   # fail('Problem')  --> raise AssertionError, 'Problem'
         return indent + new + ', ' + expr + trailer

def comma_to_op(old, new, block, op):
    '''change comma to appropriate op. dictionary dispatched. '''
    indent, expr, trailer = common_setup(old, block)
    new = new + ' '
    op = ' ' + op
    left, right = get_expr(expr, ',')

    try:
        parser.expr(left.lstrip())  # that paren came off easily
    except SyntaxError:
        left  = re.sub(linesep, '\\'+linesep, left)
        
    right = process_args(right)

    if right.startswith(linesep):
        op = op + '\\'

    return indent + new + left + op + right + trailer
 
def strip_parens(old, new, block, op):
    '''remove one set of parens. dictionary dispatched. '''
    indent, args, trailer = common_setup(old, block)
    new = new + ' '

    args = process_args(args)
    return indent + new + args + trailer

def rounding(old, new, block, op):
    '''special for assertAlmostEqual and freinds. dictionary dispatched. '''
    indent, args, trailer = common_setup(old, block)
    op = ' ' + op + ' '

    first, rest = get_expr(args.lstrip())
    second, rest = find_first_expr(rest.lstrip())
    try:
        places, msg = find_first_expr(rest.lstrip())
        if msg:
            places = places.rstrip()[:-1]
            return indent + new + '(' + first + ' - ' + second + ' ' + \
                   places + ')' + op + '0,' + msg
        else:
            return indent + new + '(' + first + ' - ' + second + ' ' + \
                   places + ')' + op + '0'

    except AttributeError:
        return indent + new + '(' + first + ' - ' + second + ', 7)' + op + '0'
      
# Now the dictionary of unittests.  There sure are enough of them!

d['assertRaises'] = {'new': 'raises', 'change': namechange_only, 'op': None}
d['failUnlessRaises'] = d['assertRaises']

d['fail'] = {'new': 'raise AssertionError', 'change': fail_special, 'op': None}

d['assertEqual'] = {'new': 'assert', 'change': comma_to_op, 'op': '=='}
d['assertEquals'] = d['assertEqual']

d['assertNotEqual'] = {'new': 'assert', 'change':comma_to_op, 'op': '!='}
d['assertNotEquals'] = d['assertNotEqual']

d['failUnlessEqual'] = {'new': 'assert not', 'change': comma_to_op, 'op': '!='}

d['failIfEqual'] = {'new': 'assert not', 'change': comma_to_op, 'op': '=='}

d['assert_'] = {'new': 'assert','change': strip_parens, 'op': None}
d['failUnless'] = d['assert_']

d['failIf'] = {'new': 'assert not', 'change': strip_parens, 'op': None}

d['assertAlmostEqual'] = {'new': 'assert round', 'change': rounding, 'op':'=='}
d['assertAlmostEquals'] = d['assertAlmostEqual']

d['assertNotAlmostEqual'] = {'new':'assert round','change':rounding, 'op':'!='}
d['assertNotAlmostEquals'] = d['assertNotAlmostEqual']

d['failIfAlmostEqual'] = {'new': 'assert not round',
                          'change': rounding, 'op': '=='}
d['failUnlessAlmostEqual'] = {'new': 'assert not round',
                               'change': rounding, 'op': '!='}

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

def dispatch(s):
    '''do a dictionary dispatch based on the change key in the dict d '''
    f = old_names.match(s)
    if f:
        key = f.group(0).lstrip()[5:-1]  # '\tself.blah(' -> 'blah'
        return d[key]['change'](key, d[key]['new'], s, d[key] ['op'])
    else: # just copy uninteresting lines
        return s

def common_setup(old, block):
    '''split the block into component parts'''
    indent = re.search(r'^(\s*)', block).group()
    pat = re.search('self.' + old + r'\(', block)
    expr, trailer = get_expr(block[pat.end():], ')')
    return indent, expr, trailer

def find_first_expr(args):
    '''find the first expression, return it, and the rest if it exists'''
    sep = ','
    try:
        left, right = get_expr(args, sep)
        left = re.sub(linesep, '\\'+linesep, left)

        # only repair the lhs.  The rhs may be a multiline string that
        # can take care of itself.
            
        if right.startswith(linesep):# that needs a slash too ...
            sep = sep + '\\'
        
        return left + sep, right
    except SyntaxError: # just a regular old multiline expression
        return re.sub(linesep, '\\'+linesep, args), None

def process_args(args):
    '''start the process whereby lines that need backslashes get them'''
    try:
        parser.expr(args.lstrip()) # the parens come off easily
        return args
    except SyntaxError:
        # paste continuation backslashes on our multiline constructs.
        left, right = find_first_expr(args)
        if right:
            return left + right
        else:
            return left

def get_expr(s, char=','):
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
        self.assertEquals(dispatch("badger badger badger"),
                          "badger badger badger")

        self.assertEquals(dispatch(
            "self.assertRaises(excClass, callableObj, *args, **kwargs)"
            ),
            "raises(excClass, callableObj, *args, **kwargs)"
                          )

        self.assertEquals(dispatch(
            """
            self.failUnlessRaises(TypeError, func, 42, **{'arg1': 23})
            """
            ),
            """
            raises(TypeError, func, 42, **{'arg1': 23})
            """
                          )
        self.assertEquals(dispatch(
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
        self.assertEquals(dispatch("self.fail()"), "raise AssertionError")
        self.assertEquals(dispatch("self.fail('mushroom, mushroom')"),
                          "raise AssertionError, 'mushroom, mushroom'")
        self.assertEquals(dispatch("self.assert_(x)"), "assert x")
        self.assertEquals(dispatch("self.failUnless(func(x)) # XXX"),
                          "assert func(x) # XXX")
        
        self.assertEquals(dispatch(
            """
            self.assert_(1 + f(y)
                         + z) # multiline, add continuation backslash
            """
            ),
            r"""
            assert 1 + f(y)\
                         + z # multiline, add continuation backslash
            """
                          )

        self.assertEquals(dispatch("self.assert_(0, 'badger badger')"),
                          "assert 0, 'badger badger'")

        self.assertEquals(dispatch(
            r"""
            self.assert_(0,
                 'Meet the badger.\n')
            """
            ),
            r"""
            assert 0,\
                 'Meet the badger.\n'
            """
                          )
        
        self.assertEquals(dispatch(
            r"""
            self.failIf(0 + 0
                          + len('badger\n')
                          + 0, '''badger badger badger badger
                                 mushroom mushroom
                                 Snake!  Ooh a snake!
                              ''') # multiline, must remove the parens
            """
            ),
            r"""
            assert not 0 + 0\
                          + len('badger\n')\
                          + 0, '''badger badger badger badger
                                 mushroom mushroom
                                 Snake!  Ooh a snake!
                              ''' # multiline, must remove the parens
            """
                          )

        self.assertEquals(dispatch("self.assertEquals(0, 0)"),
                          "assert 0 == 0")
        
        self.assertEquals(dispatch(
            r"""
            self.assertEquals(0,
                 'Run away from the snake.\n')
            """
            ),
            r"""
            assert 0 ==\
                 'Run away from the snake.\n'
            """
                          )

        self.assertEquals(dispatch(
            r"""
            self.assertEquals(badger + 0
                              + mushroom
                              + snake, 0)
            """
            ),
            r"""
            assert badger + 0\
                              + mushroom\
                              + snake == 0
            """
                          )
                            
        self.assertEquals(dispatch(
            r"""
            self.assertNotEquals(badger + 0
                              + mushroom
                              + snake,
                              mushroom
                              - badger)
            """
            ),
            r"""
            assert badger + 0\
                              + mushroom\
                              + snake !=\
                              mushroom\
                              - badger
            """
                          )

        self.assertEqual(dispatch(
            r"""
            self.assertEquals(badger(),
                              mushroom()
                              + snake(mushroom)
                              - badger())
            """
            ),
            r"""
            assert badger() ==\
                              mushroom()\
                              + snake(mushroom)\
                              - badger()
            """
                         )
        self.assertEquals(dispatch("self.failIfEqual(0, 0)"),
                          "assert not 0 == 0")

        self.assertEquals(dispatch("self.failUnlessEqual(0, 0)"),
                          "assert not 0 != 0")

        self.assertEquals(dispatch(
            r"""
            self.failUnlessEqual(mushroom()
                                 + mushroom()
                                 + mushroom(), '''badger badger badger badger
                                 badger badger badger badger
                                 badger badger badger badger
                                 ''') # multiline, must remove the parens
            """
            ),
            r"""
            assert not mushroom()\
                                 + mushroom()\
                                 + mushroom() != '''badger badger badger badger
                                 badger badger badger badger
                                 badger badger badger badger
                                 ''' # multiline, must remove the parens
            """
                          )
                              
        self.assertEquals(dispatch(
            r"""
            self.assertEquals(badger(),
                              snake(), 'BAD BADGER')
            """
            ),
            r"""
            assert badger() ==\
                              snake(), 'BAD BADGER'
            """
                          )
        self.assertEquals(dispatch(
            r"""
            self.assertEquals(badger(),
                              snake(), '''BAD BADGER
                              BAD BADGER
                              BAD BADGER'''
                              )
            """
            ),
            r"""
            assert badger() ==\
                              snake(), '''BAD BADGER
                              BAD BADGER
                              BAD BADGER'''
                              
            """
                          )
        self.assertEquals(dispatch(
            r"""
            self.assertNotEquals(badger(),
                              snake()+
                              snake(), 'POISONOUS MUSHROOM!\
                              Ai! I ate a POISONOUS MUSHROOM!!')
            """
            ),
            r"""
            assert badger() !=\
                              snake()+\
                              snake(), 'POISONOUS MUSHROOM!\
                              Ai! I ate a POISONOUS MUSHROOM!!'
            """
                          )
        self.assertEquals(dispatch("self.assertAlmostEqual(f, s, 4, 'ow')"),
            "assert round(f - s, 4) == 0, 'ow'"
                          )
        self.assertEquals(dispatch("self.assertAlmostEquals(b, m, 200)"),
            "assert round(b - m, 200) == 0"
                          )
        self.assertEquals(dispatch("self.failUnlessAlmostEqual(l, q)"),
            "assert not round(l - q, 7) != 0"
                          )
        self.assertEquals(dispatch(
            r"""
            self.failIfAlmostEqual(badger(),
                                   snake(),
                                   6, 'POISONOUS SNAKE!\
                                   Ai! I was bit by a POISONOUS SNAKE!!')
            """
            ),
            r"""
            assert not round(badger() - snake(),\
                                   6) == 0, 'POISONOUS SNAKE!\
                                   Ai! I was bit by a POISONOUS SNAKE!!'
            """
            )

if __name__ == '__main__':
    unittest.main()
    #for block in  blocksplitter('xxx.py'): print dispatch(block)

