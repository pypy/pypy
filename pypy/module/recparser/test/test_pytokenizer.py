from pypy.module.recparser.pythonlexer import PythonSource, py_number, \
     g_symdef, g_string, py_name, py_punct

def parse_source(source):
    """returns list of parsed tokens"""
    lexer = PythonSource(source)
    tokens = []
    last_token = ''
    while last_token != 'ENDMARKER':
        last_token, value = lexer.next()
        tokens.append((last_token, value))
    return tokens

class TestSuite:
    """Tokenizer test suite"""
    PUNCTS = [
        # Here should be listed each existing punctuation
        '>=', '<>', '!=', '<', '>', '<=', '==', '*=',
        '//=', '%=', '^=', '<<=', '**=', '|=',
        '+=', '>>=', '=', '&=', '/=', '-=', ',', '^',
        '>>', '&', '+', '*', '-', '/', '.', '**',
        '%', '<<', '//', '|', ')', '(', ';', ':',
        '@', '[', ']', '`', '{', '}',
        ]

    NUMBERS = [
        # Here should be listed each different form of number
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

    def test_empty_string(self):
        """make sure defined regexps don't match empty string"""
        rgxes = {'numbers' : py_number,
                 'defsym'  : g_symdef,
                 'strings' : g_string,
                 'names'   : py_name,
                 'punct'   : py_punct,
                 }
        for label, rgx in rgxes.items():
            assert rgx.match('') is None, '%s matches empty string' % label

    def test_several_lines_list(self):
        """tests list definition on several lines"""
        s = """['a'
        ]"""
        tokens = parse_source(s)
        assert tokens == [('[', None), ('STRING', "'a'"), (']', None),
                          ('NEWLINE', ''), ('ENDMARKER', None)]

    def test_numbers(self):
        """make sure all kind of numbers are correctly parsed"""
        for number in self.NUMBERS:
            assert parse_source(number)[0] == ('NUMBER', number)
            neg = '-%s' % number
            assert parse_source(neg)[:2] == [('-', None), ('NUMBER', number)]
        for number in self.BAD_NUMBERS:
            assert parse_source(number)[0] != ('NUMBER', number)

    def test_hex_number(self):
        """basic pasrse"""
        tokens = parse_source("a = 0x12L")
        assert tokens == [('NAME', 'a'), ('=', None), ('NUMBER', '0x12L'),
                          ('NEWLINE', ''), ('ENDMARKER', None)]

    def test_punct(self):
        """make sure each punctuation is correctly parsed"""
        for pstr in self.PUNCTS:
            tokens = parse_source(pstr)
            assert tokens[0][0] == pstr

