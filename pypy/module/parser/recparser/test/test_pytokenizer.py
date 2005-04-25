import unittest
from python.lexer import PythonSource, py_number, g_symdef, g_string, py_name, \
     py_comment, py_ws, py_punct

class TokenValPair(tuple):
    token = 'Override me'
    def __new__(cls, val = None):
        return tuple.__new__(cls, (cls.token, val))

TokenMap = {
    'Equals' : "=",
    'NonePair' : None,
    }
ctx = globals()
for classname in ('Number', 'String', 'EndMarker', 'NewLine', 'Dedent', 'Name',
                  'Equals', 'NonePair', 'SymDef', 'Symbol'):
    classdict = {'token' : TokenMap.get(classname, classname.upper())}
    ctx[classname] = type(classname, (TokenValPair,), classdict)


PUNCTS = [ '>=', '<>', '!=', '<', '>', '<=', '==', '*=',
           '//=', '%=', '^=', '<<=', '**=', '|=',
           '+=', '>>=', '=', '&=', '/=', '-=', ',', '^',
           '>>', '&', '+', '*', '-', '/', '.', '**',
           '%', '<<', '//', '|', ')', '(', ';', ':',
           '@', '[', ']', '`', '{', '}',
           ]


BAD_SYNTAX_STMTS = [
    # "yo yo",
    """for i in range(10):
    print i
  print 'bad dedent here'""",
    """for i in range(10):
  print i
    print 'Bad indentation here'""",
    ]

def parse_source(source):
    lexer = PythonSource(source)
    tokens = []
    last_token = ''
    while last_token != 'ENDMARKER':
        last_token, value = lexer.next()
        tokens.append((last_token, value))
    return tokens


NUMBERS = [
    '1', '1.23', '1.', '0',
    '1L', '1l',
    '0x12L', '0x12l', '0X12', '0x12',
    '1j', '1J',
    '1e2', '1.2e4',
    '0.1', '0.', '0.12', '.2',
    ]

BAD_NUMBERS = [
    'j', '0xg', '0xj', '0xJ',
    ]

class PythonSourceTC(unittest.TestCase):
    """ """
    def setUp(self):
        pass

    def test_empty_string(self):
        """make sure defined regexps don't match empty string"""
        rgxes = {'numbers' : py_number,
                 'defsym'  : g_symdef,
                 'strings' : g_string,
                 'names'   : py_name,
                 'punct'   : py_punct,
                 }
        for label, rgx in rgxes.items():
            self.assert_(rgx.match('') is None, '%s matches empty string' % label)

    def test_several_lines_list(self):
        """tests list definition on several lines"""
        s = """['a'
        ]"""
        tokens = parse_source(s)
        self.assertEquals(tokens, [('[', None), ('STRING', "'a'"), (']', None),
                                   ('NEWLINE', ''), ('ENDMARKER', None)])

    def test_numbers(self):
        """make sure all kind of numbers are correctly parsed"""
        for number in NUMBERS:
            self.assertEquals(parse_source(number)[0], ('NUMBER', number))
            neg = '-%s' % number
            self.assertEquals(parse_source(neg)[:2],
                              [('-', None), ('NUMBER', number)])
        for number in BAD_NUMBERS:
            self.assertNotEquals(parse_source(number)[0], ('NUMBER', number))
    
    def test_hex_number(self):
        tokens = parse_source("a = 0x12L")
        self.assertEquals(tokens, [('NAME', 'a'), ('=', None),
                                   ('NUMBER', '0x12L'), ('NEWLINE', ''),
                                   ('ENDMARKER', None)])
        
    def test_punct(self):
        for pstr in PUNCTS:
            tokens = parse_source( pstr )
            self.assertEqual( tokens[0][0], pstr )


if __name__ == '__main__':
    unittest.main()

