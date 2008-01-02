import py
from pypy.rlib.parsing.regexparse import parse_regex, make_runner
from pypy.rlib.parsing.lexer import Lexer

# attempts at writing a Python-lexer

def group(*choices):
    return '(' + '|'.join(choices) + ')'
def any(*choices):
    return group(*choices) + '*'
def maybe(*choices):
    return group(*choices) + '?'

#____________________________________________________________
# Numbers

Hexnumber = r'0[xX][0-9a-fA-F]*[lL]?'
Octnumber = r'0[0-7]*[lL]?'
Decnumber = r'[1-9][0-9]*[lL]?'
Intnumber = group(Hexnumber, Octnumber, Decnumber)
Exponent = r'[eE][\-\+]?[0-9]+'
Pointfloat = group(r'[0-9]+\.[0-9]*', r'\.[0-9]+') + maybe(Exponent)
Expfloat = r'[0-9]+' + Exponent
Floatnumber = group(Pointfloat, Expfloat)
Imagnumber = group(r'(0|[1-9][0-9]*)[jJ]', Floatnumber + r'[jJ]')
Number = group(Imagnumber, Floatnumber, Intnumber)

#____________________________________________________________
# Strings

_stringheader = r"[uU]?[rR]?"

# ' or " string.
def make_single_string(delim):
    normal_chars = r"[^\n\%s]*" % (delim, )
    return "".join([_stringheader, delim, normal_chars,
                    any(r"\\." + normal_chars), delim])

# triple-quoted-strings
def make_triple_string(delim):
    harmless = r"[^\%s]" % (delim, )
    anyharmless = harmless + "*"
    atleastoneharmless = harmless + "+"
    normal_chars = anyharmless + any(group(delim, 2 * delim) +
                                     atleastoneharmless)
    triple = delim * 3
    return "".join([_stringheader, triple, normal_chars,
                    any(r"\\." + normal_chars), triple])

def test_triple_regex():
    delim = '"'
    harmless = r"[^\%s]" % (delim, )
    anyharmless = harmless + "*"
    atleastoneharmless = harmless + "+"
    normal_chars = anyharmless + any(group(delim, 2 * delim) +
                                     atleastoneharmless)
    runner = make_runner(normal_chars)
    assert runner.recognize('""a""a""a""a')
    assert not runner.recognize('""a""a"""a""a')

SingleString = group(make_single_string("'"),
                     make_single_string('"'))

TripleString = group(make_triple_string("'"),
                     make_triple_string('"'))

String = group(SingleString, TripleString)

#____________________________________________________________
# Ignored

Whitespace = r'[ \f\t]*'
Newline = r'\r?\n'
Linecontinue = r'\\' + Newline + any(Whitespace)
Comment = r'#[^\r\n]*'
Indent = Newline + any(Whitespace)
Simpleignore = Whitespace + any(Whitespace) + maybe(group(Comment, Linecontinue))
Ignore = group(Linecontinue, Comment, Simpleignore)

#____________________________________________________________

Special = r'[\:\;\.\,\`\@]'
Name = r'[a-zA-Z_][a-zA-Z0-9_]*'

Operator = group(r"\*\*=?", r">>=?", r"<<=?", r"<>", r"!=",
                 r"//=?",
                 r"[\+\-\*\/\%\&\|\^\=\<\>]=?",
                 r"~")

OpenBracket = r'[\[\(\{]'
CloseBracket = r'[\]\)\}]'

#____________________________________________________________
# all tokens

tokens = ["Number", "String", "Name", "Ignore", "Special", "Indent", 
          "OpenBracket", "CloseBracket", "Operator"]

def make_lexer():
    return Lexer([parse_regex(globals()[r]) for r in tokens], tokens[:])
    
pythonlexer = make_lexer()

def postprocess(tokens):
    parenthesis_level = 0
    indentation_levels = [0]
    output_tokens = []
    for token in tokens:
        if token.name == "OpenBracket":
            parenthesis_level += 1
            token.name = "Operator"
            output_tokens.append(token)
        elif token.name == "CloseBracket":
            parenthesis_level -= 1
            if parenthesis_level < 0:
                XXX
            token.name = "Operator"
            output_tokens.append(token)
        elif token.name == "Indent":
            if parenthesis_level == 0:
                s = token.source
                length = len(s)
                pos = 1
                column = 0
                while pos < length:  # measure leading whitespace
                    c = s[pos]
                    if c == ' ':
                        column = column + 1
                    elif c == '\t':
                        column = (column // tabsize + 1) * tabsize
                    elif c == '\f':
                        column = 0
                    else:
                        break
                    pos = pos + 1
                if column > indentation_levels[-1]: # count indents or dedents
                    indentation_levels.append(column)
                    token.name = "Indent"
                while column < indentation_levels[-1]:
                    indentation_levels.pop()
                    token.name = "Dedent"
                output_tokens.append(token)
            else:
                pass # implicit line-continuations within parenthesis
        elif token.name == "Ignore":
            pass
        else:
            output_tokens.append(token)
    return output_tokens

def pythonlex(s):
    return postprocess(pythonlexer.tokenize(s))


def test_number():
    for num in ['1.231e-4', '1j', '0J', '123J'
                ]:
        tokens = pythonlexer.tokenize(num)
        token, = tokens
        assert token.name == 'Number'
    for intnum in ['1', '0', '0xABFfaf1928375']:
        for suffix in ['', 'l', 'L']:
            tokens = pythonlexer.tokenize(intnum + suffix)
            token, = tokens
            assert token.name == 'Number'

def test_single_quoted_string():
    for s in ["""u'abc'""",
              """ur'ab"c'""",
              """UR'ab\\'c'""",
              """'ab\\\nc'"""]:
        tokens = pythonlexer.tokenize(s)
        token, = tokens
        assert token.name == 'String'

def test_triple_quoted_string():
    for s in ["""'''abc'''""",
              """'''a'b'c''d'f'''""",
              """uR'''a\\''''""",
              """'''\na\nk\n\"\"\"'''"""]:
        tokens = pythonlexer.tokenize(s)
        token, = tokens
        assert token.name == 'String'

def test_name():
    for s in ["abc",
              "_",
              "a_0",
              "_0",
              ]:
        tokens = pythonlexer.tokenize(s)
        token, = tokens
        assert token.name == 'Name'

def test_long():
    for s, numtoken in [
            ("if x:\n    print x", 8),
            ("if x:#foo\n    x *= 17", 11),
            ("1 + \\\n 2", 5)]:
        tokens = pythonlexer.tokenize(s)
        assert len(tokens) == numtoken
        print tokens

def test_complex_quoting():
    s = '''"""u'abc'""",
           """ur'ab"c'""",
           """UR'ab\\'c'""",
           """'ab\\\nc'"""'''
    tokens = pythonlexer.tokenize(s)
    assert len(tokens) == 10
    for i in range(4):
        assert tokens[i * 3].name == 'String'

def test_self():
    s = py.magic.autopath().read()
    tokens = pythonlexer.tokenize(s)
    print tokens

def test_indentation():
    s = """a
b
    c
        d
    e"""
    tokens = pythonlex(s)
    assert [t.name for t in tokens] == ["Name", "Indent", "Name", "Indent",
                                        "Name", "Indent", "Name", "Dedent",
                                        "Name"]

def test_linecont():
    s = "a + \\\n     b"
    tokens = pythonlex(s)
    assert [t.name for t in tokens] == ["Name", "Operator", "Name"]

def test_parenthesis():
    s = "(a + \n     b)"
    tokens = pythonlex(s)
    assert [t.name for t in tokens] == ["Operator", "Name", "Operator", "Name",
                                        "Operator"]
