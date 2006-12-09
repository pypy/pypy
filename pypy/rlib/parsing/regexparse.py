import py
from pypy.rlib.parsing.parsing import PackratParser, Rule
from pypy.rlib.parsing.tree import Nonterminal
from pypy.rlib.parsing.regex import StringExpression, RangeExpression
from pypy.rlib.parsing.lexer import Lexer, DummyLexer
from pypy.rlib.parsing.deterministic import compress_char_set, DFA
import string

ESCAPES = {
    "\\a": "\a",
    "\\b": "\b",
    "\\f": "\f",
    "\\n": "\n",
    "\\r": "\r",
    "\\t": "\t",
    "\\v": "\v",
    "\\":  "\\"
}

for i in range(256):
    # 'x' and numbers are reserved for hexadecimal/octal escapes
    if chr(i) in 'x01234567':
        continue
    escaped = "\\" + chr(i)
    if escaped not in ESCAPES:
        ESCAPES[escaped] = chr(i)
for a in "0123456789ABCDEFabcdef":
    for b in "0123456789ABCDEFabcdef":
        escaped = "\\x%s%s" % (a, b)
        if escaped not in ESCAPES:
            ESCAPES[escaped] = chr(int("%s%s" % (a, b), 16))
for a in "0123":
    for b in "01234567":
        for c in "01234567":
            escaped = "\\x%s%s%s" % (a, b, c)
            if escaped not in ESCAPES:
                ESCAPES[escaped] = chr(int("%s%s%s" % (a, b, c), 8))

def unescape(s):
    result = []
    i = 0
    while i < len(s):
        if s[i] != "\\":
            result.append(s[i])
            i += 1
            continue
        if s[i + 1] == "x":
            escaped = s[i: i + 4]
            i += 4
        elif s[i + 1] in "01234567":
            escaped = s[i: i + 4]
            i += 4
        else:
            escaped = s[i: i + 2]
            i += 2
        if escaped not in ESCAPES:
            raise ValueError("escape %r unknown" % (escaped, ))
        else:
            result.append(ESCAPES[escaped])
    return "".join(result)

def make_regex_parser():
    from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
    # construct regular expressions by hand, to not go completely insane
    # because of quoting
    special_chars = "*+()[]{}|.-?,^"
    # lexer
    QUOTES = []
    for escaped in ESCAPES.iterkeys():
        QUOTES.append(StringExpression(escaped))
    REST = StringExpression("a")
    for p in string.printable:
        if p not in special_chars:
            REST = REST | StringExpression(p)
    regexs1 = QUOTES + [REST]
    names1 = ['QUOTEDCHAR'] * len(QUOTES) + ['CHAR']
    # parser
    rs, rules, ToAST = parse_ebnf("""
    regex: concatenation "|" regex | <concatenation>;
    concatenation: repetition concatenation | <repetition>;
    repetition: primary "*" |
                primary "+" |
                primary "?" |
                primary "{" numrange "}" |
                <primary>;
    primary: "(" <regex> ")" |
             "[" range "]" |
             char | ".";
    char: QUOTEDCHAR | CHAR;
    range: "^" subrange | subrange;
    subrange: rangeelement+;
    rangeelement: char "-" char | char;
    numrange: num "," num | <num>;
    num: CHAR+;
    """)
    names2, regexs2 = zip(*rs)
    lexer = Lexer(regexs1 + list(regexs2), names1 + list(names2))
    parser = PackratParser(rules, "regex")
    return parser, lexer, ToAST

def parse_regex(s):
    tokens = lexer.tokenize(s)
    s = parser.parse(tokens)
    s = s.visit(RegexToAST())[0]
    res = s.visit(RegexBuilder())
    assert res is not None
    return res

def make_runner(regex, view=False):
    r = parse_regex(regex)
    dfa = r.make_automaton().make_deterministic()
    if view:
        dfa.view()
    dfa.optimize()
    if view:
        dfa.view()
    r = dfa.get_runner()
    return r

class RegexBuilder(object):
    def visit_regex(self, node):
        return node.children[0].visit(self) | node.children[2].visit(self)

    def visit_concatenation(self, node):
        return node.children[0].visit(self) + node.children[1].visit(self)

    def visit_repetition(self, node):
        if len(node.children) == 4:
            subregex = node.children[0].visit(self)
            r1, r2 = node.children[2].visit(self)
            if r1 >= r2:
                return StringExpression("")
            base = StringExpression("")
            for i in range(r1):
                base += subregex
            rest = StringExpression("")
            curr = StringExpression("")
            for i in range(r2 - r1):
                rest = rest | curr
                curr += subregex
            return base + rest
        if node.children[1].additional_info == "*":
            return node.children[0].visit(self).kleene()
        elif node.children[1].additional_info == "+":
            return + node.children[0].visit(self)
        elif node.children[1].additional_info == "?":
            return StringExpression("") | node.children[0].visit(self)

    def visit_primary(self, node):
        if len(node.children) == 1:
            if node.children[0].symbol == "char":
                return node.children[0].visit(self)
            elif node.children[0].additional_info == ".":
                return RangeExpression(chr(0), chr(255))
            raise ParserError
        if node.children[0].additional_info == "(":
            return node.children[1].visit(self)
        else:
            return node.children[1].visit(self)

    def visit_char(self, node):
        if node.children[0].symbol == "QUOTEDCHAR":
            quote = node.children[0].additional_info
            return StringExpression(unescape(quote))
        else:
            return StringExpression(node.children[0].additional_info[-1])

    def visit_range(self, node):
        ranges = node.children[-1].visit(self)
        invert = len(node.children) == 2
        result = set()
        for a, b in ranges:
            for i in range(ord(a), ord(b) + 1):
                result.add(i)
        if invert:
            result = set(range(256)) - result
        compressed = compress_char_set([chr(i) for i in result])
        return reduce(py.std.operator.or_,
                      [RangeExpression(a, chr(ord(a) + b - 1))
                          for a, b in compressed])

    def visit_subrange(self, node):
        return [c.visit(self) for c in node.children]

    def visit_rangeelement(self, node):
        if len(node.children) == 3:
            r = (node.children[0].visit(self).string,
                 node.children[2].visit(self).string)
        else:
            char = node.children[0].visit(self).string
            r = (char, char)
        return r

    def visit_numrange(self, node):
        r1 = node.children[0].visit(self)[0]
        r2 = node.children[2].visit(self)[0] + 1
        return r1, r2

    def visit_num(self, node):
        r = int("".join([c.additional_info for c in node.children]))
        return r, r + 1


# generated code between this line and its other occurence
class RegexToAST(object):
    def visit_regex(self, node):
        length = len(node.children)
        if length == 1:
            return self.visit_concatenation(node.children[0])
        children = []
        children.extend(self.visit_concatenation(node.children[0]))
        children.extend([node.children[1]])
        children.extend(self.visit_regex(node.children[2]))
        return [Nonterminal(node.symbol, children)]
    def visit_concatenation(self, node):
        length = len(node.children)
        if length == 1:
            return self.visit_repetition(node.children[0])
        children = []
        children.extend(self.visit_repetition(node.children[0]))
        children.extend(self.visit_concatenation(node.children[1]))
        return [Nonterminal(node.symbol, children)]
    def visit_repetition(self, node):
        length = len(node.children)
        if length == 1:
            return self.visit_primary(node.children[0])
        if length == 2:
            if node.children[1].symbol == '__1_*':
                children = []
                children.extend(self.visit_primary(node.children[0]))
                children.extend([node.children[1]])
                return [Nonterminal(node.symbol, children)]
            if node.children[1].symbol == '__2_+':
                children = []
                children.extend(self.visit_primary(node.children[0]))
                children.extend([node.children[1]])
                return [Nonterminal(node.symbol, children)]
            children = []
            children.extend(self.visit_primary(node.children[0]))
            children.extend([node.children[1]])
            return [Nonterminal(node.symbol, children)]
        children = []
        children.extend(self.visit_primary(node.children[0]))
        children.extend([node.children[1]])
        children.extend(self.visit_numrange(node.children[2]))
        children.extend([node.children[3]])
        return [Nonterminal(node.symbol, children)]
    def visit_primary(self, node):
        length = len(node.children)
        if length == 1:
            if node.children[0].symbol == '__10_.':
                children = []
                children.extend([node.children[0]])
                return [Nonterminal(node.symbol, children)]
            children = []
            children.extend(self.visit_char(node.children[0]))
            return [Nonterminal(node.symbol, children)]
        if node.children[0].symbol == '__6_(':
            return self.visit_regex(node.children[1])
        children = []
        children.extend([node.children[0]])
        children.extend(self.visit_range(node.children[1]))
        children.extend([node.children[2]])
        return [Nonterminal(node.symbol, children)]
    def visit_char(self, node):
        length = len(node.children)
        if node.children[0].symbol == 'CHAR':
            children = []
            children.extend([node.children[0]])
            return [Nonterminal(node.symbol, children)]
        children = []
        children.extend([node.children[0]])
        return [Nonterminal(node.symbol, children)]
    def visit_range(self, node):
        length = len(node.children)
        if length == 1:
            children = []
            children.extend(self.visit_subrange(node.children[0]))
            return [Nonterminal(node.symbol, children)]
        children = []
        children.extend([node.children[0]])
        children.extend(self.visit_subrange(node.children[1]))
        return [Nonterminal(node.symbol, children)]
    def visit__plus_symbol0(self, node):
        length = len(node.children)
        if length == 1:
            children = []
            children.extend(self.visit_rangeelement(node.children[0]))
            return [Nonterminal(node.symbol, children)]
        children = []
        children.extend(self.visit_rangeelement(node.children[0]))
        expr = self.visit__plus_symbol0(node.children[1])
        assert len(expr) == 1
        children.extend(expr[0].children)
        return [Nonterminal(node.symbol, children)]
    def visit_subrange(self, node):
        children = []
        expr = self.visit__plus_symbol0(node.children[0])
        assert len(expr) == 1
        children.extend(expr[0].children)
        return [Nonterminal(node.symbol, children)]
    def visit_rangeelement(self, node):
        length = len(node.children)
        if length == 1:
            children = []
            children.extend(self.visit_char(node.children[0]))
            return [Nonterminal(node.symbol, children)]
        children = []
        children.extend(self.visit_char(node.children[0]))
        children.extend([node.children[1]])
        children.extend(self.visit_char(node.children[2]))
        return [Nonterminal(node.symbol, children)]
    def visit_numrange(self, node):
        length = len(node.children)
        if length == 1:
            return self.visit_num(node.children[0])
        children = []
        children.extend(self.visit_num(node.children[0]))
        children.extend([node.children[1]])
        children.extend(self.visit_num(node.children[2]))
        return [Nonterminal(node.symbol, children)]
    def visit__plus_symbol1(self, node):
        length = len(node.children)
        if length == 1:
            children = []
            children.extend([node.children[0]])
            return [Nonterminal(node.symbol, children)]
        children = []
        children.extend([node.children[0]])
        expr = self.visit__plus_symbol1(node.children[1])
        assert len(expr) == 1
        children.extend(expr[0].children)
        return [Nonterminal(node.symbol, children)]
    def visit_num(self, node):
        children = []
        expr = self.visit__plus_symbol1(node.children[0])
        assert len(expr) == 1
        children.extend(expr[0].children)
        return [Nonterminal(node.symbol, children)]
parser = PackratParser([Rule('regex', [['concatenation', '__0_|', 'regex'], ['concatenation']]),
  Rule('concatenation', [['repetition', 'concatenation'], ['repetition']]),
  Rule('repetition', [['primary', '__1_*'], ['primary', '__2_+'], ['primary', '__3_?'], ['primary', '__4_{', 'numrange', '__5_}'], ['primary']]),
  Rule('primary', [['__6_(', 'regex', '__7_)'], ['__8_[', 'range', '__9_]'], ['char'], ['__10_.']]),
  Rule('char', [['QUOTEDCHAR'], ['CHAR']]),
  Rule('range', [['__11_^', 'subrange'], ['subrange']]),
  Rule('_plus_symbol0', [['rangeelement', '_plus_symbol0'], ['rangeelement']]),
  Rule('subrange', [['_plus_symbol0']]),
  Rule('rangeelement', [['char', '__12_-', 'char'], ['char']]),
  Rule('numrange', [['num', '__13_,', 'num'], ['num']]),
  Rule('_plus_symbol1', [['CHAR', '_plus_symbol1'], ['CHAR']]),
  Rule('num', [['_plus_symbol1']])],
 'regex')
def recognize(runner, i):
    assert i >= 0
    input = runner.text
    state = 0
    while 1:
        if state == 0:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 0
                return ~i
            if '\t' <= char <= '\r':
                state = 1
            elif ' ' <= char <= "'":
                state = 1
            elif '/' <= char <= '>':
                state = 1
            elif '@' <= char <= 'Z':
                state = 1
            elif '_' <= char <= 'z':
                state = 1
            elif char == '~':
                state = 1
            elif char == '(':
                state = 2
            elif char == ',':
                state = 3
            elif char == '\\':
                state = 4
            elif char == '|':
                state = 5
            elif char == '+':
                state = 6
            elif char == '?':
                state = 7
            elif char == '[':
                state = 8
            elif char == '{':
                state = 9
            elif char == '*':
                state = 10
            elif char == '.':
                state = 11
            elif char == '^':
                state = 12
            elif char == ')':
                state = 13
            elif char == '-':
                state = 14
            elif char == ']':
                state = 15
            elif char == '}':
                state = 16
            else:
                break
        if state == 769:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 769
                return i
            if char == '1':
                state = 847
            elif char == '0':
                state = 848
            elif char == '3':
                state = 849
            elif char == '2':
                state = 850
            elif char == '5':
                state = 851
            elif char == '4':
                state = 852
            elif char == '7':
                state = 853
            elif char == '6':
                state = 854
            else:
                break
        if state == 770:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 770
                return i
            if char == '1':
                state = 839
            elif char == '0':
                state = 840
            elif char == '3':
                state = 841
            elif char == '2':
                state = 842
            elif char == '5':
                state = 843
            elif char == '4':
                state = 844
            elif char == '7':
                state = 845
            elif char == '6':
                state = 846
            else:
                break
        if state == 771:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 771
                return i
            if char == '0':
                state = 832
            elif char == '3':
                state = 833
            elif char == '2':
                state = 834
            elif char == '5':
                state = 835
            elif char == '4':
                state = 836
            elif char == '7':
                state = 837
            elif char == '6':
                state = 838
            elif char == '1':
                state = 831
            else:
                break
        if state == 4:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 4
                return i
            if char == '\x00':
                state = 17
            elif char == '\x83':
                state = 18
            elif char == '\x04':
                state = 19
            elif char == '\x87':
                state = 20
            elif char == '\x08':
                state = 21
            elif char == '\x8b':
                state = 22
            elif char == '\x0c':
                state = 23
            elif char == '\x8f':
                state = 24
            elif char == '\x10':
                state = 25
            elif char == '\x93':
                state = 26
            elif char == '\x14':
                state = 27
            elif char == '\x97':
                state = 28
            elif char == '\x18':
                state = 29
            elif char == '\x9b':
                state = 30
            elif char == '\x1c':
                state = 31
            elif char == '\x9f':
                state = 32
            elif char == ' ':
                state = 33
            elif char == '\xa3':
                state = 34
            elif char == '$':
                state = 35
            elif char == '\xa7':
                state = 36
            elif char == '(':
                state = 37
            elif char == '\xab':
                state = 38
            elif char == ',':
                state = 39
            elif char == '\xaf':
                state = 40
            elif char == '\xb3':
                state = 41
            elif char == '\xb7':
                state = 42
            elif char == '8':
                state = 43
            elif char == '\xbb':
                state = 44
            elif char == '<':
                state = 45
            elif char == '\xbf':
                state = 46
            elif char == '@':
                state = 47
            elif char == '\xc3':
                state = 48
            elif char == 'D':
                state = 49
            elif char == '\xc7':
                state = 50
            elif char == 'H':
                state = 51
            elif char == '\xcb':
                state = 52
            elif char == 'L':
                state = 53
            elif char == '\xcf':
                state = 54
            elif char == 'P':
                state = 55
            elif char == '\xd3':
                state = 56
            elif char == 'T':
                state = 57
            elif char == '\xd7':
                state = 58
            elif char == 'X':
                state = 59
            elif char == '\xdb':
                state = 60
            elif char == '\\':
                state = 61
            elif char == '\xdf':
                state = 62
            elif char == '`':
                state = 63
            elif char == '\xe3':
                state = 64
            elif char == 'd':
                state = 65
            elif char == '\xe7':
                state = 66
            elif char == 'h':
                state = 67
            elif char == '\xeb':
                state = 68
            elif char == 'l':
                state = 69
            elif char == '\xef':
                state = 70
            elif char == 'p':
                state = 71
            elif char == '\xf3':
                state = 72
            elif char == 't':
                state = 73
            elif char == '\xf7':
                state = 74
            elif char == 'x':
                state = 75
            elif char == '\xfb':
                state = 76
            elif char == '|':
                state = 77
            elif char == '\xff':
                state = 78
            elif char == '\x80':
                state = 79
            elif char == '\x03':
                state = 80
            elif char == '\x84':
                state = 81
            elif char == '\x07':
                state = 82
            elif char == '\x88':
                state = 83
            elif char == '\x0b':
                state = 84
            elif char == '\x8c':
                state = 85
            elif char == '\x0f':
                state = 86
            elif char == '\x90':
                state = 87
            elif char == '\x13':
                state = 88
            elif char == '\x94':
                state = 89
            elif char == '\x17':
                state = 90
            elif char == '\x98':
                state = 91
            elif char == '\x1b':
                state = 92
            elif char == '\x9c':
                state = 93
            elif char == '\x1f':
                state = 94
            elif char == '\xa0':
                state = 95
            elif char == '#':
                state = 96
            elif char == '\xa4':
                state = 97
            elif char == "'":
                state = 98
            elif char == '\xa8':
                state = 99
            elif char == '+':
                state = 100
            elif char == '\xac':
                state = 101
            elif char == '/':
                state = 102
            elif char == '\xb0':
                state = 103
            elif char == '\xb4':
                state = 104
            elif char == '\xb8':
                state = 105
            elif char == ';':
                state = 106
            elif char == '\xbc':
                state = 107
            elif char == '?':
                state = 108
            elif char == '\xc0':
                state = 109
            elif char == 'C':
                state = 110
            elif char == '\xc4':
                state = 111
            elif char == 'G':
                state = 112
            elif char == '\xc8':
                state = 113
            elif char == 'K':
                state = 114
            elif char == '\xcc':
                state = 115
            elif char == 'O':
                state = 116
            elif char == '\xd0':
                state = 117
            elif char == 'S':
                state = 118
            elif char == '\xd4':
                state = 119
            elif char == 'W':
                state = 120
            elif char == '\xd8':
                state = 121
            elif char == '[':
                state = 122
            elif char == '\xdc':
                state = 123
            elif char == '_':
                state = 124
            elif char == '\xe0':
                state = 125
            elif char == 'c':
                state = 126
            elif char == '\xe4':
                state = 127
            elif char == 'g':
                state = 128
            elif char == '\xe8':
                state = 129
            elif char == 'k':
                state = 130
            elif char == '\xec':
                state = 131
            elif char == 'o':
                state = 132
            elif char == '\xf0':
                state = 133
            elif char == 's':
                state = 134
            elif char == '\xf4':
                state = 135
            elif char == 'w':
                state = 136
            elif char == '\xf8':
                state = 137
            elif char == '{':
                state = 138
            elif char == '\xfc':
                state = 139
            elif char == '\x7f':
                state = 140
            elif char == '\x81':
                state = 141
            elif char == '\x02':
                state = 142
            elif char == '\x85':
                state = 143
            elif char == '\x06':
                state = 144
            elif char == '\x89':
                state = 145
            elif char == '\n':
                state = 146
            elif char == '\x8d':
                state = 147
            elif char == '\x0e':
                state = 148
            elif char == '\x91':
                state = 149
            elif char == '\x12':
                state = 150
            elif char == '\x95':
                state = 151
            elif char == '\x16':
                state = 152
            elif char == '\x99':
                state = 153
            elif char == '\x1a':
                state = 154
            elif char == '\x9d':
                state = 155
            elif char == '\x1e':
                state = 156
            elif char == '\xa1':
                state = 157
            elif char == '"':
                state = 158
            elif char == '\xa5':
                state = 159
            elif char == '&':
                state = 160
            elif char == '\xa9':
                state = 161
            elif char == '*':
                state = 162
            elif char == '\xad':
                state = 163
            elif char == '.':
                state = 164
            elif char == '\xb1':
                state = 165
            elif char == '\xb5':
                state = 166
            elif char == '\xb9':
                state = 167
            elif char == ':':
                state = 168
            elif char == '\xbd':
                state = 169
            elif char == '>':
                state = 170
            elif char == '\xc1':
                state = 171
            elif char == 'B':
                state = 172
            elif char == '\xc5':
                state = 173
            elif char == 'F':
                state = 174
            elif char == '\xc9':
                state = 175
            elif char == 'J':
                state = 176
            elif char == '\xcd':
                state = 177
            elif char == 'N':
                state = 178
            elif char == '\xd1':
                state = 179
            elif char == 'R':
                state = 180
            elif char == '\xd5':
                state = 181
            elif char == 'V':
                state = 182
            elif char == '\xd9':
                state = 183
            elif char == 'Z':
                state = 184
            elif char == '\xdd':
                state = 185
            elif char == '^':
                state = 186
            elif char == '\xe1':
                state = 187
            elif char == 'b':
                state = 188
            elif char == '\xe5':
                state = 189
            elif char == 'f':
                state = 190
            elif char == '\xe9':
                state = 191
            elif char == 'j':
                state = 192
            elif char == '\xed':
                state = 193
            elif char == 'n':
                state = 194
            elif char == '\xf1':
                state = 195
            elif char == 'r':
                state = 196
            elif char == '\xf5':
                state = 197
            elif char == 'v':
                state = 198
            elif char == '\xf9':
                state = 199
            elif char == 'z':
                state = 200
            elif char == '\xfd':
                state = 201
            elif char == '~':
                state = 202
            elif char == '\x01':
                state = 203
            elif char == '\x82':
                state = 204
            elif char == '\x05':
                state = 205
            elif char == '\x86':
                state = 206
            elif char == '\t':
                state = 207
            elif char == '\x8a':
                state = 208
            elif char == '\r':
                state = 209
            elif char == '\x8e':
                state = 210
            elif char == '\x11':
                state = 211
            elif char == '\x92':
                state = 212
            elif char == '\x15':
                state = 213
            elif char == '\x96':
                state = 214
            elif char == '\x19':
                state = 215
            elif char == '\x9a':
                state = 216
            elif char == '\x1d':
                state = 217
            elif char == '\x9e':
                state = 218
            elif char == '!':
                state = 219
            elif char == '\xa2':
                state = 220
            elif char == '%':
                state = 221
            elif char == '\xa6':
                state = 222
            elif char == ')':
                state = 223
            elif char == '\xaa':
                state = 224
            elif char == '-':
                state = 225
            elif char == '\xae':
                state = 226
            elif char == '\xb2':
                state = 227
            elif char == '\xb6':
                state = 228
            elif char == '9':
                state = 229
            elif char == '\xba':
                state = 230
            elif char == '=':
                state = 231
            elif char == '\xbe':
                state = 232
            elif char == 'A':
                state = 233
            elif char == '\xc2':
                state = 234
            elif char == 'E':
                state = 235
            elif char == '\xc6':
                state = 236
            elif char == 'I':
                state = 237
            elif char == '\xca':
                state = 238
            elif char == 'M':
                state = 239
            elif char == '\xce':
                state = 240
            elif char == 'Q':
                state = 241
            elif char == '\xd2':
                state = 242
            elif char == 'U':
                state = 243
            elif char == '\xd6':
                state = 244
            elif char == 'Y':
                state = 245
            elif char == '\xda':
                state = 246
            elif char == ']':
                state = 247
            elif char == '\xde':
                state = 248
            elif char == 'a':
                state = 249
            elif char == '\xe2':
                state = 250
            elif char == 'e':
                state = 251
            elif char == '\xe6':
                state = 252
            elif char == 'i':
                state = 253
            elif char == '\xea':
                state = 254
            elif char == 'm':
                state = 255
            elif char == '\xee':
                state = 256
            elif char == 'q':
                state = 257
            elif char == '\xf2':
                state = 258
            elif char == 'u':
                state = 259
            elif char == '\xf6':
                state = 260
            elif char == 'y':
                state = 261
            elif char == '\xfa':
                state = 262
            elif char == '}':
                state = 263
            elif char == '\xfe':
                state = 264
            else:
                break
        if state == 773:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 773
                return i
            if char == '1':
                state = 815
            elif char == '0':
                state = 816
            elif char == '3':
                state = 817
            elif char == '2':
                state = 818
            elif char == '5':
                state = 819
            elif char == '4':
                state = 820
            elif char == '7':
                state = 821
            elif char == '6':
                state = 822
            else:
                break
        if state == 774:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 774
                return i
            if char == '1':
                state = 807
            elif char == '0':
                state = 808
            elif char == '3':
                state = 809
            elif char == '2':
                state = 810
            elif char == '5':
                state = 811
            elif char == '4':
                state = 812
            elif char == '7':
                state = 813
            elif char == '6':
                state = 814
            else:
                break
        if state == 942:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 942
                return i
            if char == '1':
                state = 1011
            elif char == '0':
                state = 1012
            elif char == '3':
                state = 1013
            elif char == '2':
                state = 1014
            elif char == '5':
                state = 1015
            elif char == '4':
                state = 1016
            elif char == '7':
                state = 1017
            elif char == '6':
                state = 1018
            else:
                break
        if state == 776:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 776
                return i
            if char == '1':
                state = 791
            elif char == '0':
                state = 792
            elif char == '3':
                state = 793
            elif char == '2':
                state = 794
            elif char == '5':
                state = 795
            elif char == '4':
                state = 796
            elif char == '7':
                state = 797
            elif char == '6':
                state = 798
            else:
                break
        if state == 265:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 265
                return ~i
            if char == '1':
                state = 941
            elif char == '0':
                state = 942
                continue
            elif char == '3':
                state = 943
            elif char == '2':
                state = 944
            elif char == '5':
                state = 945
            elif char == '4':
                state = 946
            elif char == '7':
                state = 947
            elif char == '6':
                state = 948
            elif char == '9':
                state = 949
            elif char == '8':
                state = 950
            elif char == 'A':
                state = 951
            elif char == 'C':
                state = 952
            elif char == 'B':
                state = 953
            elif char == 'E':
                state = 954
            elif char == 'D':
                state = 955
            elif char == 'F':
                state = 956
            elif char == 'a':
                state = 957
            elif char == 'c':
                state = 958
            elif char == 'b':
                state = 959
            elif char == 'e':
                state = 960
            elif char == 'd':
                state = 961
            elif char == 'f':
                state = 962
            else:
                break
        if state == 266:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 266
                return ~i
            if char == '1':
                state = 855
            elif char == '0':
                state = 856
            elif char == '3':
                state = 857
            elif char == '2':
                state = 858
            elif char == '5':
                state = 859
            elif char == '4':
                state = 860
            elif char == '7':
                state = 861
            elif char == '6':
                state = 862
            elif char == '9':
                state = 863
            elif char == '8':
                state = 864
            elif char == 'A':
                state = 865
            elif char == 'C':
                state = 866
            elif char == 'B':
                state = 867
            elif char == 'E':
                state = 868
            elif char == 'D':
                state = 869
            elif char == 'F':
                state = 870
            elif char == 'a':
                state = 871
            elif char == 'c':
                state = 872
            elif char == 'b':
                state = 873
            elif char == 'e':
                state = 874
            elif char == 'd':
                state = 875
            elif char == 'f':
                state = 876
            else:
                break
        if state == 267:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 267
                return ~i
            if char == '1':
                state = 769
                continue
            elif char == '0':
                state = 770
                continue
            elif char == '3':
                state = 771
                continue
            elif char == '2':
                state = 772
            elif char == '5':
                state = 773
                continue
            elif char == '4':
                state = 774
                continue
            elif char == '7':
                state = 775
            elif char == '6':
                state = 776
                continue
            elif char == '9':
                state = 777
            elif char == '8':
                state = 778
            elif char == 'A':
                state = 779
            elif char == 'C':
                state = 780
            elif char == 'B':
                state = 781
            elif char == 'E':
                state = 782
            elif char == 'D':
                state = 783
            elif char == 'F':
                state = 784
            elif char == 'a':
                state = 785
            elif char == 'c':
                state = 786
            elif char == 'b':
                state = 787
            elif char == 'e':
                state = 788
            elif char == 'd':
                state = 789
            elif char == 'f':
                state = 790
            else:
                break
        if state == 268:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 268
                return ~i
            if char == '1':
                state = 683
            elif char == '0':
                state = 684
            elif char == '3':
                state = 685
            elif char == '2':
                state = 686
            elif char == '5':
                state = 687
            elif char == '4':
                state = 688
            elif char == '7':
                state = 689
            elif char == '6':
                state = 690
            elif char == '9':
                state = 691
            elif char == '8':
                state = 692
            elif char == 'A':
                state = 693
            elif char == 'C':
                state = 694
            elif char == 'B':
                state = 695
            elif char == 'E':
                state = 696
            elif char == 'D':
                state = 697
            elif char == 'F':
                state = 698
            elif char == 'a':
                state = 699
            elif char == 'c':
                state = 700
            elif char == 'b':
                state = 701
            elif char == 'e':
                state = 702
            elif char == 'd':
                state = 703
            elif char == 'f':
                state = 704
            else:
                break
        if state == 269:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 269
                return ~i
            if char == '1':
                state = 661
            elif char == '0':
                state = 662
            elif char == '3':
                state = 663
            elif char == '2':
                state = 664
            elif char == '5':
                state = 665
            elif char == '4':
                state = 666
            elif char == '7':
                state = 667
            elif char == '6':
                state = 668
            elif char == '9':
                state = 669
            elif char == '8':
                state = 670
            elif char == 'A':
                state = 671
            elif char == 'C':
                state = 672
            elif char == 'B':
                state = 673
            elif char == 'E':
                state = 674
            elif char == 'D':
                state = 675
            elif char == 'F':
                state = 676
            elif char == 'a':
                state = 677
            elif char == 'c':
                state = 678
            elif char == 'b':
                state = 679
            elif char == 'e':
                state = 680
            elif char == 'd':
                state = 681
            elif char == 'f':
                state = 682
            else:
                break
        if state == 270:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 270
                return ~i
            if char == '0':
                state = 640
            elif char == '3':
                state = 641
            elif char == '2':
                state = 642
            elif char == '5':
                state = 643
            elif char == '4':
                state = 644
            elif char == '7':
                state = 645
            elif char == '6':
                state = 646
            elif char == '9':
                state = 647
            elif char == '8':
                state = 648
            elif char == 'A':
                state = 649
            elif char == 'C':
                state = 650
            elif char == 'B':
                state = 651
            elif char == 'E':
                state = 652
            elif char == 'D':
                state = 653
            elif char == 'F':
                state = 654
            elif char == 'a':
                state = 655
            elif char == 'c':
                state = 656
            elif char == 'b':
                state = 657
            elif char == 'e':
                state = 658
            elif char == 'd':
                state = 659
            elif char == 'f':
                state = 660
            elif char == '1':
                state = 639
            else:
                break
        if state == 271:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 271
                return ~i
            if char == '1':
                state = 617
            elif char == '0':
                state = 618
            elif char == '3':
                state = 619
            elif char == '2':
                state = 620
            elif char == '5':
                state = 621
            elif char == '4':
                state = 622
            elif char == '7':
                state = 623
            elif char == '6':
                state = 624
            elif char == '9':
                state = 625
            elif char == '8':
                state = 626
            elif char == 'A':
                state = 627
            elif char == 'C':
                state = 628
            elif char == 'B':
                state = 629
            elif char == 'E':
                state = 630
            elif char == 'D':
                state = 631
            elif char == 'F':
                state = 632
            elif char == 'a':
                state = 633
            elif char == 'c':
                state = 634
            elif char == 'b':
                state = 635
            elif char == 'e':
                state = 636
            elif char == 'd':
                state = 637
            elif char == 'f':
                state = 638
            else:
                break
        if state == 272:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 272
                return ~i
            if char == '1':
                state = 595
            elif char == '0':
                state = 596
            elif char == '3':
                state = 597
            elif char == '2':
                state = 598
            elif char == '5':
                state = 599
            elif char == '4':
                state = 600
            elif char == '7':
                state = 601
            elif char == '6':
                state = 602
            elif char == '9':
                state = 603
            elif char == '8':
                state = 604
            elif char == 'A':
                state = 605
            elif char == 'C':
                state = 606
            elif char == 'B':
                state = 607
            elif char == 'E':
                state = 608
            elif char == 'D':
                state = 609
            elif char == 'F':
                state = 610
            elif char == 'a':
                state = 611
            elif char == 'c':
                state = 612
            elif char == 'b':
                state = 613
            elif char == 'e':
                state = 614
            elif char == 'd':
                state = 615
            elif char == 'f':
                state = 616
            else:
                break
        if state == 273:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 273
                return ~i
            if char == '1':
                state = 573
            elif char == '0':
                state = 574
            elif char == '3':
                state = 575
            elif char == '2':
                state = 576
            elif char == '5':
                state = 577
            elif char == '4':
                state = 578
            elif char == '7':
                state = 579
            elif char == '6':
                state = 580
            elif char == '9':
                state = 581
            elif char == '8':
                state = 582
            elif char == 'A':
                state = 583
            elif char == 'C':
                state = 584
            elif char == 'B':
                state = 585
            elif char == 'E':
                state = 586
            elif char == 'D':
                state = 587
            elif char == 'F':
                state = 588
            elif char == 'a':
                state = 589
            elif char == 'c':
                state = 590
            elif char == 'b':
                state = 591
            elif char == 'e':
                state = 592
            elif char == 'd':
                state = 593
            elif char == 'f':
                state = 594
            else:
                break
        if state == 274:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 274
                return ~i
            if char == '1':
                state = 551
            elif char == '0':
                state = 552
            elif char == '3':
                state = 553
            elif char == '2':
                state = 554
            elif char == '5':
                state = 555
            elif char == '4':
                state = 556
            elif char == '7':
                state = 557
            elif char == '6':
                state = 558
            elif char == '9':
                state = 559
            elif char == '8':
                state = 560
            elif char == 'A':
                state = 561
            elif char == 'C':
                state = 562
            elif char == 'B':
                state = 563
            elif char == 'E':
                state = 564
            elif char == 'D':
                state = 565
            elif char == 'F':
                state = 566
            elif char == 'a':
                state = 567
            elif char == 'c':
                state = 568
            elif char == 'b':
                state = 569
            elif char == 'e':
                state = 570
            elif char == 'd':
                state = 571
            elif char == 'f':
                state = 572
            else:
                break
        if state == 275:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 275
                return ~i
            if char == '1':
                state = 529
            elif char == '0':
                state = 530
            elif char == '3':
                state = 531
            elif char == '2':
                state = 532
            elif char == '5':
                state = 533
            elif char == '4':
                state = 534
            elif char == '7':
                state = 535
            elif char == '6':
                state = 536
            elif char == '9':
                state = 537
            elif char == '8':
                state = 538
            elif char == 'A':
                state = 539
            elif char == 'C':
                state = 540
            elif char == 'B':
                state = 541
            elif char == 'E':
                state = 542
            elif char == 'D':
                state = 543
            elif char == 'F':
                state = 544
            elif char == 'a':
                state = 545
            elif char == 'c':
                state = 546
            elif char == 'b':
                state = 547
            elif char == 'e':
                state = 548
            elif char == 'd':
                state = 549
            elif char == 'f':
                state = 550
            else:
                break
        if state == 276:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 276
                return ~i
            if char == '4':
                state = 512
            elif char == '7':
                state = 513
            elif char == '6':
                state = 514
            elif char == '9':
                state = 515
            elif char == '8':
                state = 516
            elif char == 'A':
                state = 517
            elif char == 'C':
                state = 518
            elif char == 'B':
                state = 519
            elif char == 'E':
                state = 520
            elif char == 'D':
                state = 521
            elif char == 'F':
                state = 522
            elif char == 'a':
                state = 523
            elif char == 'c':
                state = 524
            elif char == 'b':
                state = 525
            elif char == 'e':
                state = 526
            elif char == 'd':
                state = 527
            elif char == 'f':
                state = 528
            elif char == '1':
                state = 507
            elif char == '0':
                state = 508
            elif char == '3':
                state = 509
            elif char == '2':
                state = 510
            elif char == '5':
                state = 511
            else:
                break
        if state == 277:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 277
                return ~i
            if char == '1':
                state = 485
            elif char == '0':
                state = 486
            elif char == '3':
                state = 487
            elif char == '2':
                state = 488
            elif char == '5':
                state = 489
            elif char == '4':
                state = 490
            elif char == '7':
                state = 491
            elif char == '6':
                state = 492
            elif char == '9':
                state = 493
            elif char == '8':
                state = 494
            elif char == 'A':
                state = 495
            elif char == 'C':
                state = 496
            elif char == 'B':
                state = 497
            elif char == 'E':
                state = 498
            elif char == 'D':
                state = 499
            elif char == 'F':
                state = 500
            elif char == 'a':
                state = 501
            elif char == 'c':
                state = 502
            elif char == 'b':
                state = 503
            elif char == 'e':
                state = 504
            elif char == 'd':
                state = 505
            elif char == 'f':
                state = 506
            else:
                break
        if state == 278:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 278
                return ~i
            if char == '1':
                state = 463
            elif char == '0':
                state = 464
            elif char == '3':
                state = 465
            elif char == '2':
                state = 466
            elif char == '5':
                state = 467
            elif char == '4':
                state = 468
            elif char == '7':
                state = 469
            elif char == '6':
                state = 470
            elif char == '9':
                state = 471
            elif char == '8':
                state = 472
            elif char == 'A':
                state = 473
            elif char == 'C':
                state = 474
            elif char == 'B':
                state = 475
            elif char == 'E':
                state = 476
            elif char == 'D':
                state = 477
            elif char == 'F':
                state = 478
            elif char == 'a':
                state = 479
            elif char == 'c':
                state = 480
            elif char == 'b':
                state = 481
            elif char == 'e':
                state = 482
            elif char == 'd':
                state = 483
            elif char == 'f':
                state = 484
            else:
                break
        if state == 279:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 279
                return ~i
            if char == '1':
                state = 441
            elif char == '0':
                state = 442
            elif char == '3':
                state = 443
            elif char == '2':
                state = 444
            elif char == '5':
                state = 445
            elif char == '4':
                state = 446
            elif char == '7':
                state = 447
            elif char == '6':
                state = 448
            elif char == '9':
                state = 449
            elif char == '8':
                state = 450
            elif char == 'A':
                state = 451
            elif char == 'C':
                state = 452
            elif char == 'B':
                state = 453
            elif char == 'E':
                state = 454
            elif char == 'D':
                state = 455
            elif char == 'F':
                state = 456
            elif char == 'a':
                state = 457
            elif char == 'c':
                state = 458
            elif char == 'b':
                state = 459
            elif char == 'e':
                state = 460
            elif char == 'd':
                state = 461
            elif char == 'f':
                state = 462
            else:
                break
        if state == 280:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 280
                return ~i
            if char == '1':
                state = 419
            elif char == '0':
                state = 420
            elif char == '3':
                state = 421
            elif char == '2':
                state = 422
            elif char == '5':
                state = 423
            elif char == '4':
                state = 424
            elif char == '7':
                state = 425
            elif char == '6':
                state = 426
            elif char == '9':
                state = 427
            elif char == '8':
                state = 428
            elif char == 'A':
                state = 429
            elif char == 'C':
                state = 430
            elif char == 'B':
                state = 431
            elif char == 'E':
                state = 432
            elif char == 'D':
                state = 433
            elif char == 'F':
                state = 434
            elif char == 'a':
                state = 435
            elif char == 'c':
                state = 436
            elif char == 'b':
                state = 437
            elif char == 'e':
                state = 438
            elif char == 'd':
                state = 439
            elif char == 'f':
                state = 440
            else:
                break
        if state == 281:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 281
                return ~i
            if char == '1':
                state = 397
            elif char == '0':
                state = 398
            elif char == '3':
                state = 399
            elif char == '2':
                state = 400
            elif char == '5':
                state = 401
            elif char == '4':
                state = 402
            elif char == '7':
                state = 403
            elif char == '6':
                state = 404
            elif char == '9':
                state = 405
            elif char == '8':
                state = 406
            elif char == 'A':
                state = 407
            elif char == 'C':
                state = 408
            elif char == 'B':
                state = 409
            elif char == 'E':
                state = 410
            elif char == 'D':
                state = 411
            elif char == 'F':
                state = 412
            elif char == 'a':
                state = 413
            elif char == 'c':
                state = 414
            elif char == 'b':
                state = 415
            elif char == 'e':
                state = 416
            elif char == 'd':
                state = 417
            elif char == 'f':
                state = 418
            else:
                break
        if state == 282:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 282
                return ~i
            if char == '8':
                state = 384
            elif char == 'A':
                state = 385
            elif char == 'C':
                state = 386
            elif char == 'B':
                state = 387
            elif char == 'E':
                state = 388
            elif char == 'D':
                state = 389
            elif char == 'F':
                state = 390
            elif char == 'a':
                state = 391
            elif char == 'c':
                state = 392
            elif char == 'b':
                state = 393
            elif char == 'e':
                state = 394
            elif char == 'd':
                state = 395
            elif char == 'f':
                state = 396
            elif char == '1':
                state = 375
            elif char == '0':
                state = 376
            elif char == '3':
                state = 377
            elif char == '2':
                state = 378
            elif char == '5':
                state = 379
            elif char == '4':
                state = 380
            elif char == '7':
                state = 381
            elif char == '6':
                state = 382
            elif char == '9':
                state = 383
            else:
                break
        if state == 283:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 283
                return ~i
            if char == '1':
                state = 353
            elif char == '0':
                state = 354
            elif char == '3':
                state = 355
            elif char == '2':
                state = 356
            elif char == '5':
                state = 357
            elif char == '4':
                state = 358
            elif char == '7':
                state = 359
            elif char == '6':
                state = 360
            elif char == '9':
                state = 361
            elif char == '8':
                state = 362
            elif char == 'A':
                state = 363
            elif char == 'C':
                state = 364
            elif char == 'B':
                state = 365
            elif char == 'E':
                state = 366
            elif char == 'D':
                state = 367
            elif char == 'F':
                state = 368
            elif char == 'a':
                state = 369
            elif char == 'c':
                state = 370
            elif char == 'b':
                state = 371
            elif char == 'e':
                state = 372
            elif char == 'd':
                state = 373
            elif char == 'f':
                state = 374
            else:
                break
        if state == 284:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 284
                return ~i
            if char == '1':
                state = 331
            elif char == '0':
                state = 332
            elif char == '3':
                state = 333
            elif char == '2':
                state = 334
            elif char == '5':
                state = 335
            elif char == '4':
                state = 336
            elif char == '7':
                state = 337
            elif char == '6':
                state = 338
            elif char == '9':
                state = 339
            elif char == '8':
                state = 340
            elif char == 'A':
                state = 341
            elif char == 'C':
                state = 342
            elif char == 'B':
                state = 343
            elif char == 'E':
                state = 344
            elif char == 'D':
                state = 345
            elif char == 'F':
                state = 346
            elif char == 'a':
                state = 347
            elif char == 'c':
                state = 348
            elif char == 'b':
                state = 349
            elif char == 'e':
                state = 350
            elif char == 'd':
                state = 351
            elif char == 'f':
                state = 352
            else:
                break
        if state == 285:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 285
                return ~i
            if char == '1':
                state = 309
            elif char == '0':
                state = 310
            elif char == '3':
                state = 311
            elif char == '2':
                state = 312
            elif char == '5':
                state = 313
            elif char == '4':
                state = 314
            elif char == '7':
                state = 315
            elif char == '6':
                state = 316
            elif char == '9':
                state = 317
            elif char == '8':
                state = 318
            elif char == 'A':
                state = 319
            elif char == 'C':
                state = 320
            elif char == 'B':
                state = 321
            elif char == 'E':
                state = 322
            elif char == 'D':
                state = 323
            elif char == 'F':
                state = 324
            elif char == 'a':
                state = 325
            elif char == 'c':
                state = 326
            elif char == 'b':
                state = 327
            elif char == 'e':
                state = 328
            elif char == 'd':
                state = 329
            elif char == 'f':
                state = 330
            else:
                break
        if state == 286:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 286
                return ~i
            if char == '1':
                state = 287
            elif char == '0':
                state = 288
            elif char == '3':
                state = 289
            elif char == '2':
                state = 290
            elif char == '5':
                state = 291
            elif char == '4':
                state = 292
            elif char == '7':
                state = 293
            elif char == '6':
                state = 294
            elif char == '9':
                state = 295
            elif char == '8':
                state = 296
            elif char == 'A':
                state = 297
            elif char == 'C':
                state = 298
            elif char == 'B':
                state = 299
            elif char == 'E':
                state = 300
            elif char == 'D':
                state = 301
            elif char == 'F':
                state = 302
            elif char == 'a':
                state = 303
            elif char == 'c':
                state = 304
            elif char == 'b':
                state = 305
            elif char == 'e':
                state = 306
            elif char == 'd':
                state = 307
            elif char == 'f':
                state = 308
            else:
                break
        if state == 944:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 944
                return i
            if char == '1':
                state = 995
            elif char == '0':
                state = 996
            elif char == '3':
                state = 997
            elif char == '2':
                state = 998
            elif char == '5':
                state = 999
            elif char == '4':
                state = 1000
            elif char == '7':
                state = 1001
            elif char == '6':
                state = 1002
            else:
                break
        if state == 689:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 689
                return i
            if char == '1':
                state = 713
            elif char == '0':
                state = 714
            elif char == '3':
                state = 715
            elif char == '2':
                state = 716
            elif char == '5':
                state = 717
            elif char == '4':
                state = 718
            elif char == '7':
                state = 719
            elif char == '6':
                state = 720
            else:
                break
        if state == 683:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 683
                return i
            if char == '6':
                state = 768
            elif char == '1':
                state = 761
            elif char == '0':
                state = 762
            elif char == '3':
                state = 763
            elif char == '2':
                state = 764
            elif char == '5':
                state = 765
            elif char == '4':
                state = 766
            elif char == '7':
                state = 767
            else:
                break
        if state == 684:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 684
                return i
            if char == '1':
                state = 753
            elif char == '0':
                state = 754
            elif char == '3':
                state = 755
            elif char == '2':
                state = 756
            elif char == '5':
                state = 757
            elif char == '4':
                state = 758
            elif char == '7':
                state = 759
            elif char == '6':
                state = 760
            else:
                break
        if state == 941:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 941
                return i
            if char == '4':
                state = 1024
            elif char == '7':
                state = 1025
            elif char == '6':
                state = 1026
            elif char == '1':
                state = 1019
            elif char == '0':
                state = 1020
            elif char == '3':
                state = 1021
            elif char == '2':
                state = 1022
            elif char == '5':
                state = 1023
            else:
                break
        if state == 686:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 686
                return i
            if char == '1':
                state = 737
            elif char == '0':
                state = 738
            elif char == '3':
                state = 739
            elif char == '2':
                state = 740
            elif char == '5':
                state = 741
            elif char == '4':
                state = 742
            elif char == '7':
                state = 743
            elif char == '6':
                state = 744
            else:
                break
        if state == 943:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 943
                return i
            if char == '1':
                state = 1003
            elif char == '0':
                state = 1004
            elif char == '3':
                state = 1005
            elif char == '2':
                state = 1006
            elif char == '5':
                state = 1007
            elif char == '4':
                state = 1008
            elif char == '7':
                state = 1009
            elif char == '6':
                state = 1010
            else:
                break
        if state == 688:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 688
                return i
            if char == '1':
                state = 721
            elif char == '0':
                state = 722
            elif char == '3':
                state = 723
            elif char == '2':
                state = 724
            elif char == '5':
                state = 725
            elif char == '4':
                state = 726
            elif char == '7':
                state = 727
            elif char == '6':
                state = 728
            else:
                break
        if state == 945:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 945
                return i
            if char == '4':
                state = 992
            elif char == '7':
                state = 993
            elif char == '6':
                state = 994
            elif char == '1':
                state = 987
            elif char == '0':
                state = 988
            elif char == '3':
                state = 989
            elif char == '2':
                state = 990
            elif char == '5':
                state = 991
            else:
                break
        if state == 690:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 690
                return i
            if char == '1':
                state = 705
            elif char == '0':
                state = 706
            elif char == '3':
                state = 707
            elif char == '2':
                state = 708
            elif char == '5':
                state = 709
            elif char == '4':
                state = 710
            elif char == '7':
                state = 711
            elif char == '6':
                state = 712
            else:
                break
        if state == 947:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 947
                return i
            if char == '1':
                state = 971
            elif char == '0':
                state = 972
            elif char == '3':
                state = 973
            elif char == '2':
                state = 974
            elif char == '5':
                state = 975
            elif char == '4':
                state = 976
            elif char == '7':
                state = 977
            elif char == '6':
                state = 978
            else:
                break
        if state == 948:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 948
                return i
            if char == '1':
                state = 963
            elif char == '0':
                state = 964
            elif char == '3':
                state = 965
            elif char == '2':
                state = 966
            elif char == '5':
                state = 967
            elif char == '4':
                state = 968
            elif char == '7':
                state = 969
            elif char == '6':
                state = 970
            else:
                break
        if state == 687:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 687
                return i
            if char == '6':
                state = 736
            elif char == '1':
                state = 729
            elif char == '0':
                state = 730
            elif char == '3':
                state = 731
            elif char == '2':
                state = 732
            elif char == '5':
                state = 733
            elif char == '4':
                state = 734
            elif char == '7':
                state = 735
            else:
                break
        if state == 75:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 75
                return ~i
            if char == '1':
                state = 265
                continue
            elif char == '0':
                state = 266
                continue
            elif char == '3':
                state = 267
                continue
            elif char == '2':
                state = 268
                continue
            elif char == '5':
                state = 269
                continue
            elif char == '4':
                state = 270
                continue
            elif char == '7':
                state = 271
                continue
            elif char == '6':
                state = 272
                continue
            elif char == '9':
                state = 273
                continue
            elif char == '8':
                state = 274
                continue
            elif char == 'A':
                state = 275
                continue
            elif char == 'C':
                state = 276
                continue
            elif char == 'B':
                state = 277
                continue
            elif char == 'E':
                state = 278
                continue
            elif char == 'D':
                state = 279
                continue
            elif char == 'F':
                state = 280
                continue
            elif char == 'a':
                state = 281
                continue
            elif char == 'c':
                state = 282
                continue
            elif char == 'b':
                state = 283
                continue
            elif char == 'e':
                state = 284
                continue
            elif char == 'd':
                state = 285
                continue
            elif char == 'f':
                state = 286
                continue
            else:
                break
        if state == 855:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 855
                return i
            if char == '1':
                state = 933
            elif char == '0':
                state = 934
            elif char == '3':
                state = 935
            elif char == '2':
                state = 936
            elif char == '5':
                state = 937
            elif char == '4':
                state = 938
            elif char == '7':
                state = 939
            elif char == '6':
                state = 940
            else:
                break
        if state == 856:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 856
                return i
            if char == '2':
                state = 928
            elif char == '5':
                state = 929
            elif char == '4':
                state = 930
            elif char == '7':
                state = 931
            elif char == '6':
                state = 932
            elif char == '1':
                state = 925
            elif char == '0':
                state = 926
            elif char == '3':
                state = 927
            else:
                break
        if state == 857:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 857
                return i
            if char == '1':
                state = 917
            elif char == '0':
                state = 918
            elif char == '3':
                state = 919
            elif char == '2':
                state = 920
            elif char == '5':
                state = 921
            elif char == '4':
                state = 922
            elif char == '7':
                state = 923
            elif char == '6':
                state = 924
            else:
                break
        if state == 858:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 858
                return i
            if char == '1':
                state = 909
            elif char == '0':
                state = 910
            elif char == '3':
                state = 911
            elif char == '2':
                state = 912
            elif char == '5':
                state = 913
            elif char == '4':
                state = 914
            elif char == '7':
                state = 915
            elif char == '6':
                state = 916
            else:
                break
        if state == 859:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 859
                return i
            if char == '1':
                state = 901
            elif char == '0':
                state = 902
            elif char == '3':
                state = 903
            elif char == '2':
                state = 904
            elif char == '5':
                state = 905
            elif char == '4':
                state = 906
            elif char == '7':
                state = 907
            elif char == '6':
                state = 908
            else:
                break
        if state == 860:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 860
                return i
            if char == '2':
                state = 896
            elif char == '5':
                state = 897
            elif char == '4':
                state = 898
            elif char == '7':
                state = 899
            elif char == '6':
                state = 900
            elif char == '1':
                state = 893
            elif char == '0':
                state = 894
            elif char == '3':
                state = 895
            else:
                break
        if state == 861:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 861
                return i
            if char == '1':
                state = 885
            elif char == '0':
                state = 886
            elif char == '3':
                state = 887
            elif char == '2':
                state = 888
            elif char == '5':
                state = 889
            elif char == '4':
                state = 890
            elif char == '7':
                state = 891
            elif char == '6':
                state = 892
            else:
                break
        if state == 862:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 862
                return i
            if char == '1':
                state = 877
            elif char == '0':
                state = 878
            elif char == '3':
                state = 879
            elif char == '2':
                state = 880
            elif char == '5':
                state = 881
            elif char == '4':
                state = 882
            elif char == '7':
                state = 883
            elif char == '6':
                state = 884
            else:
                break
        if state == 685:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 685
                return i
            if char == '1':
                state = 745
            elif char == '0':
                state = 746
            elif char == '3':
                state = 747
            elif char == '2':
                state = 748
            elif char == '5':
                state = 749
            elif char == '4':
                state = 750
            elif char == '7':
                state = 751
            elif char == '6':
                state = 752
            else:
                break
        if state == 772:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 772
                return i
            if char == '1':
                state = 823
            elif char == '0':
                state = 824
            elif char == '3':
                state = 825
            elif char == '2':
                state = 826
            elif char == '5':
                state = 827
            elif char == '4':
                state = 828
            elif char == '7':
                state = 829
            elif char == '6':
                state = 830
            else:
                break
        if state == 775:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 775
                return i
            if char == '0':
                state = 800
            elif char == '3':
                state = 801
            elif char == '2':
                state = 802
            elif char == '5':
                state = 803
            elif char == '4':
                state = 804
            elif char == '7':
                state = 805
            elif char == '6':
                state = 806
            elif char == '1':
                state = 799
            else:
                break
        if state == 946:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 946
                return i
            if char == '1':
                state = 979
            elif char == '0':
                state = 980
            elif char == '3':
                state = 981
            elif char == '2':
                state = 982
            elif char == '5':
                state = 983
            elif char == '4':
                state = 984
            elif char == '7':
                state = 985
            elif char == '6':
                state = 986
            else:
                break
        runner.last_matched_state = state
        runner.last_matched_index = i - 1
        runner.state = state
        if i == len(input):
            return i
        else:
            return ~i
        break
    runner.state = state
    return ~i
lexer = DummyLexer(recognize, DFA(1027,
 {(0, '\t'): 1,
  (0, '\n'): 1,
  (0, '\x0b'): 1,
  (0, '\x0c'): 1,
  (0, '\r'): 1,
  (0, ' '): 1,
  (0, '!'): 1,
  (0, '"'): 1,
  (0, '#'): 1,
  (0, '$'): 1,
  (0, '%'): 1,
  (0, '&'): 1,
  (0, "'"): 1,
  (0, '('): 2,
  (0, ')'): 13,
  (0, '*'): 10,
  (0, '+'): 6,
  (0, ','): 3,
  (0, '-'): 14,
  (0, '.'): 11,
  (0, '/'): 1,
  (0, '0'): 1,
  (0, '1'): 1,
  (0, '2'): 1,
  (0, '3'): 1,
  (0, '4'): 1,
  (0, '5'): 1,
  (0, '6'): 1,
  (0, '7'): 1,
  (0, '8'): 1,
  (0, '9'): 1,
  (0, ':'): 1,
  (0, ';'): 1,
  (0, '<'): 1,
  (0, '='): 1,
  (0, '>'): 1,
  (0, '?'): 7,
  (0, '@'): 1,
  (0, 'A'): 1,
  (0, 'B'): 1,
  (0, 'C'): 1,
  (0, 'D'): 1,
  (0, 'E'): 1,
  (0, 'F'): 1,
  (0, 'G'): 1,
  (0, 'H'): 1,
  (0, 'I'): 1,
  (0, 'J'): 1,
  (0, 'K'): 1,
  (0, 'L'): 1,
  (0, 'M'): 1,
  (0, 'N'): 1,
  (0, 'O'): 1,
  (0, 'P'): 1,
  (0, 'Q'): 1,
  (0, 'R'): 1,
  (0, 'S'): 1,
  (0, 'T'): 1,
  (0, 'U'): 1,
  (0, 'V'): 1,
  (0, 'W'): 1,
  (0, 'X'): 1,
  (0, 'Y'): 1,
  (0, 'Z'): 1,
  (0, '['): 8,
  (0, '\\'): 4,
  (0, ']'): 15,
  (0, '^'): 12,
  (0, '_'): 1,
  (0, '`'): 1,
  (0, 'a'): 1,
  (0, 'b'): 1,
  (0, 'c'): 1,
  (0, 'd'): 1,
  (0, 'e'): 1,
  (0, 'f'): 1,
  (0, 'g'): 1,
  (0, 'h'): 1,
  (0, 'i'): 1,
  (0, 'j'): 1,
  (0, 'k'): 1,
  (0, 'l'): 1,
  (0, 'm'): 1,
  (0, 'n'): 1,
  (0, 'o'): 1,
  (0, 'p'): 1,
  (0, 'q'): 1,
  (0, 'r'): 1,
  (0, 's'): 1,
  (0, 't'): 1,
  (0, 'u'): 1,
  (0, 'v'): 1,
  (0, 'w'): 1,
  (0, 'x'): 1,
  (0, 'y'): 1,
  (0, 'z'): 1,
  (0, '{'): 9,
  (0, '|'): 5,
  (0, '}'): 16,
  (0, '~'): 1,
  (4, '\x00'): 17,
  (4, '\x01'): 203,
  (4, '\x02'): 142,
  (4, '\x03'): 80,
  (4, '\x04'): 19,
  (4, '\x05'): 205,
  (4, '\x06'): 144,
  (4, '\x07'): 82,
  (4, '\x08'): 21,
  (4, '\t'): 207,
  (4, '\n'): 146,
  (4, '\x0b'): 84,
  (4, '\x0c'): 23,
  (4, '\r'): 209,
  (4, '\x0e'): 148,
  (4, '\x0f'): 86,
  (4, '\x10'): 25,
  (4, '\x11'): 211,
  (4, '\x12'): 150,
  (4, '\x13'): 88,
  (4, '\x14'): 27,
  (4, '\x15'): 213,
  (4, '\x16'): 152,
  (4, '\x17'): 90,
  (4, '\x18'): 29,
  (4, '\x19'): 215,
  (4, '\x1a'): 154,
  (4, '\x1b'): 92,
  (4, '\x1c'): 31,
  (4, '\x1d'): 217,
  (4, '\x1e'): 156,
  (4, '\x1f'): 94,
  (4, ' '): 33,
  (4, '!'): 219,
  (4, '"'): 158,
  (4, '#'): 96,
  (4, '$'): 35,
  (4, '%'): 221,
  (4, '&'): 160,
  (4, "'"): 98,
  (4, '('): 37,
  (4, ')'): 223,
  (4, '*'): 162,
  (4, '+'): 100,
  (4, ','): 39,
  (4, '-'): 225,
  (4, '.'): 164,
  (4, '/'): 102,
  (4, '8'): 43,
  (4, '9'): 229,
  (4, ':'): 168,
  (4, ';'): 106,
  (4, '<'): 45,
  (4, '='): 231,
  (4, '>'): 170,
  (4, '?'): 108,
  (4, '@'): 47,
  (4, 'A'): 233,
  (4, 'B'): 172,
  (4, 'C'): 110,
  (4, 'D'): 49,
  (4, 'E'): 235,
  (4, 'F'): 174,
  (4, 'G'): 112,
  (4, 'H'): 51,
  (4, 'I'): 237,
  (4, 'J'): 176,
  (4, 'K'): 114,
  (4, 'L'): 53,
  (4, 'M'): 239,
  (4, 'N'): 178,
  (4, 'O'): 116,
  (4, 'P'): 55,
  (4, 'Q'): 241,
  (4, 'R'): 180,
  (4, 'S'): 118,
  (4, 'T'): 57,
  (4, 'U'): 243,
  (4, 'V'): 182,
  (4, 'W'): 120,
  (4, 'X'): 59,
  (4, 'Y'): 245,
  (4, 'Z'): 184,
  (4, '['): 122,
  (4, '\\'): 61,
  (4, ']'): 247,
  (4, '^'): 186,
  (4, '_'): 124,
  (4, '`'): 63,
  (4, 'a'): 249,
  (4, 'b'): 188,
  (4, 'c'): 126,
  (4, 'd'): 65,
  (4, 'e'): 251,
  (4, 'f'): 190,
  (4, 'g'): 128,
  (4, 'h'): 67,
  (4, 'i'): 253,
  (4, 'j'): 192,
  (4, 'k'): 130,
  (4, 'l'): 69,
  (4, 'm'): 255,
  (4, 'n'): 194,
  (4, 'o'): 132,
  (4, 'p'): 71,
  (4, 'q'): 257,
  (4, 'r'): 196,
  (4, 's'): 134,
  (4, 't'): 73,
  (4, 'u'): 259,
  (4, 'v'): 198,
  (4, 'w'): 136,
  (4, 'x'): 75,
  (4, 'y'): 261,
  (4, 'z'): 200,
  (4, '{'): 138,
  (4, '|'): 77,
  (4, '}'): 263,
  (4, '~'): 202,
  (4, '\x7f'): 140,
  (4, '\x80'): 79,
  (4, '\x81'): 141,
  (4, '\x82'): 204,
  (4, '\x83'): 18,
  (4, '\x84'): 81,
  (4, '\x85'): 143,
  (4, '\x86'): 206,
  (4, '\x87'): 20,
  (4, '\x88'): 83,
  (4, '\x89'): 145,
  (4, '\x8a'): 208,
  (4, '\x8b'): 22,
  (4, '\x8c'): 85,
  (4, '\x8d'): 147,
  (4, '\x8e'): 210,
  (4, '\x8f'): 24,
  (4, '\x90'): 87,
  (4, '\x91'): 149,
  (4, '\x92'): 212,
  (4, '\x93'): 26,
  (4, '\x94'): 89,
  (4, '\x95'): 151,
  (4, '\x96'): 214,
  (4, '\x97'): 28,
  (4, '\x98'): 91,
  (4, '\x99'): 153,
  (4, '\x9a'): 216,
  (4, '\x9b'): 30,
  (4, '\x9c'): 93,
  (4, '\x9d'): 155,
  (4, '\x9e'): 218,
  (4, '\x9f'): 32,
  (4, '\xa0'): 95,
  (4, '\xa1'): 157,
  (4, '\xa2'): 220,
  (4, '\xa3'): 34,
  (4, '\xa4'): 97,
  (4, '\xa5'): 159,
  (4, '\xa6'): 222,
  (4, '\xa7'): 36,
  (4, '\xa8'): 99,
  (4, '\xa9'): 161,
  (4, '\xaa'): 224,
  (4, '\xab'): 38,
  (4, '\xac'): 101,
  (4, '\xad'): 163,
  (4, '\xae'): 226,
  (4, '\xaf'): 40,
  (4, '\xb0'): 103,
  (4, '\xb1'): 165,
  (4, '\xb2'): 227,
  (4, '\xb3'): 41,
  (4, '\xb4'): 104,
  (4, '\xb5'): 166,
  (4, '\xb6'): 228,
  (4, '\xb7'): 42,
  (4, '\xb8'): 105,
  (4, '\xb9'): 167,
  (4, '\xba'): 230,
  (4, '\xbb'): 44,
  (4, '\xbc'): 107,
  (4, '\xbd'): 169,
  (4, '\xbe'): 232,
  (4, '\xbf'): 46,
  (4, '\xc0'): 109,
  (4, '\xc1'): 171,
  (4, '\xc2'): 234,
  (4, '\xc3'): 48,
  (4, '\xc4'): 111,
  (4, '\xc5'): 173,
  (4, '\xc6'): 236,
  (4, '\xc7'): 50,
  (4, '\xc8'): 113,
  (4, '\xc9'): 175,
  (4, '\xca'): 238,
  (4, '\xcb'): 52,
  (4, '\xcc'): 115,
  (4, '\xcd'): 177,
  (4, '\xce'): 240,
  (4, '\xcf'): 54,
  (4, '\xd0'): 117,
  (4, '\xd1'): 179,
  (4, '\xd2'): 242,
  (4, '\xd3'): 56,
  (4, '\xd4'): 119,
  (4, '\xd5'): 181,
  (4, '\xd6'): 244,
  (4, '\xd7'): 58,
  (4, '\xd8'): 121,
  (4, '\xd9'): 183,
  (4, '\xda'): 246,
  (4, '\xdb'): 60,
  (4, '\xdc'): 123,
  (4, '\xdd'): 185,
  (4, '\xde'): 248,
  (4, '\xdf'): 62,
  (4, '\xe0'): 125,
  (4, '\xe1'): 187,
  (4, '\xe2'): 250,
  (4, '\xe3'): 64,
  (4, '\xe4'): 127,
  (4, '\xe5'): 189,
  (4, '\xe6'): 252,
  (4, '\xe7'): 66,
  (4, '\xe8'): 129,
  (4, '\xe9'): 191,
  (4, '\xea'): 254,
  (4, '\xeb'): 68,
  (4, '\xec'): 131,
  (4, '\xed'): 193,
  (4, '\xee'): 256,
  (4, '\xef'): 70,
  (4, '\xf0'): 133,
  (4, '\xf1'): 195,
  (4, '\xf2'): 258,
  (4, '\xf3'): 72,
  (4, '\xf4'): 135,
  (4, '\xf5'): 197,
  (4, '\xf6'): 260,
  (4, '\xf7'): 74,
  (4, '\xf8'): 137,
  (4, '\xf9'): 199,
  (4, '\xfa'): 262,
  (4, '\xfb'): 76,
  (4, '\xfc'): 139,
  (4, '\xfd'): 201,
  (4, '\xfe'): 264,
  (4, '\xff'): 78,
  (75, '0'): 266,
  (75, '1'): 265,
  (75, '2'): 268,
  (75, '3'): 267,
  (75, '4'): 270,
  (75, '5'): 269,
  (75, '6'): 272,
  (75, '7'): 271,
  (75, '8'): 274,
  (75, '9'): 273,
  (75, 'A'): 275,
  (75, 'B'): 277,
  (75, 'C'): 276,
  (75, 'D'): 279,
  (75, 'E'): 278,
  (75, 'F'): 280,
  (75, 'a'): 281,
  (75, 'b'): 283,
  (75, 'c'): 282,
  (75, 'd'): 285,
  (75, 'e'): 284,
  (75, 'f'): 286,
  (265, '0'): 942,
  (265, '1'): 941,
  (265, '2'): 944,
  (265, '3'): 943,
  (265, '4'): 946,
  (265, '5'): 945,
  (265, '6'): 948,
  (265, '7'): 947,
  (265, '8'): 950,
  (265, '9'): 949,
  (265, 'A'): 951,
  (265, 'B'): 953,
  (265, 'C'): 952,
  (265, 'D'): 955,
  (265, 'E'): 954,
  (265, 'F'): 956,
  (265, 'a'): 957,
  (265, 'b'): 959,
  (265, 'c'): 958,
  (265, 'd'): 961,
  (265, 'e'): 960,
  (265, 'f'): 962,
  (266, '0'): 856,
  (266, '1'): 855,
  (266, '2'): 858,
  (266, '3'): 857,
  (266, '4'): 860,
  (266, '5'): 859,
  (266, '6'): 862,
  (266, '7'): 861,
  (266, '8'): 864,
  (266, '9'): 863,
  (266, 'A'): 865,
  (266, 'B'): 867,
  (266, 'C'): 866,
  (266, 'D'): 869,
  (266, 'E'): 868,
  (266, 'F'): 870,
  (266, 'a'): 871,
  (266, 'b'): 873,
  (266, 'c'): 872,
  (266, 'd'): 875,
  (266, 'e'): 874,
  (266, 'f'): 876,
  (267, '0'): 770,
  (267, '1'): 769,
  (267, '2'): 772,
  (267, '3'): 771,
  (267, '4'): 774,
  (267, '5'): 773,
  (267, '6'): 776,
  (267, '7'): 775,
  (267, '8'): 778,
  (267, '9'): 777,
  (267, 'A'): 779,
  (267, 'B'): 781,
  (267, 'C'): 780,
  (267, 'D'): 783,
  (267, 'E'): 782,
  (267, 'F'): 784,
  (267, 'a'): 785,
  (267, 'b'): 787,
  (267, 'c'): 786,
  (267, 'd'): 789,
  (267, 'e'): 788,
  (267, 'f'): 790,
  (268, '0'): 684,
  (268, '1'): 683,
  (268, '2'): 686,
  (268, '3'): 685,
  (268, '4'): 688,
  (268, '5'): 687,
  (268, '6'): 690,
  (268, '7'): 689,
  (268, '8'): 692,
  (268, '9'): 691,
  (268, 'A'): 693,
  (268, 'B'): 695,
  (268, 'C'): 694,
  (268, 'D'): 697,
  (268, 'E'): 696,
  (268, 'F'): 698,
  (268, 'a'): 699,
  (268, 'b'): 701,
  (268, 'c'): 700,
  (268, 'd'): 703,
  (268, 'e'): 702,
  (268, 'f'): 704,
  (269, '0'): 662,
  (269, '1'): 661,
  (269, '2'): 664,
  (269, '3'): 663,
  (269, '4'): 666,
  (269, '5'): 665,
  (269, '6'): 668,
  (269, '7'): 667,
  (269, '8'): 670,
  (269, '9'): 669,
  (269, 'A'): 671,
  (269, 'B'): 673,
  (269, 'C'): 672,
  (269, 'D'): 675,
  (269, 'E'): 674,
  (269, 'F'): 676,
  (269, 'a'): 677,
  (269, 'b'): 679,
  (269, 'c'): 678,
  (269, 'd'): 681,
  (269, 'e'): 680,
  (269, 'f'): 682,
  (270, '0'): 640,
  (270, '1'): 639,
  (270, '2'): 642,
  (270, '3'): 641,
  (270, '4'): 644,
  (270, '5'): 643,
  (270, '6'): 646,
  (270, '7'): 645,
  (270, '8'): 648,
  (270, '9'): 647,
  (270, 'A'): 649,
  (270, 'B'): 651,
  (270, 'C'): 650,
  (270, 'D'): 653,
  (270, 'E'): 652,
  (270, 'F'): 654,
  (270, 'a'): 655,
  (270, 'b'): 657,
  (270, 'c'): 656,
  (270, 'd'): 659,
  (270, 'e'): 658,
  (270, 'f'): 660,
  (271, '0'): 618,
  (271, '1'): 617,
  (271, '2'): 620,
  (271, '3'): 619,
  (271, '4'): 622,
  (271, '5'): 621,
  (271, '6'): 624,
  (271, '7'): 623,
  (271, '8'): 626,
  (271, '9'): 625,
  (271, 'A'): 627,
  (271, 'B'): 629,
  (271, 'C'): 628,
  (271, 'D'): 631,
  (271, 'E'): 630,
  (271, 'F'): 632,
  (271, 'a'): 633,
  (271, 'b'): 635,
  (271, 'c'): 634,
  (271, 'd'): 637,
  (271, 'e'): 636,
  (271, 'f'): 638,
  (272, '0'): 596,
  (272, '1'): 595,
  (272, '2'): 598,
  (272, '3'): 597,
  (272, '4'): 600,
  (272, '5'): 599,
  (272, '6'): 602,
  (272, '7'): 601,
  (272, '8'): 604,
  (272, '9'): 603,
  (272, 'A'): 605,
  (272, 'B'): 607,
  (272, 'C'): 606,
  (272, 'D'): 609,
  (272, 'E'): 608,
  (272, 'F'): 610,
  (272, 'a'): 611,
  (272, 'b'): 613,
  (272, 'c'): 612,
  (272, 'd'): 615,
  (272, 'e'): 614,
  (272, 'f'): 616,
  (273, '0'): 574,
  (273, '1'): 573,
  (273, '2'): 576,
  (273, '3'): 575,
  (273, '4'): 578,
  (273, '5'): 577,
  (273, '6'): 580,
  (273, '7'): 579,
  (273, '8'): 582,
  (273, '9'): 581,
  (273, 'A'): 583,
  (273, 'B'): 585,
  (273, 'C'): 584,
  (273, 'D'): 587,
  (273, 'E'): 586,
  (273, 'F'): 588,
  (273, 'a'): 589,
  (273, 'b'): 591,
  (273, 'c'): 590,
  (273, 'd'): 593,
  (273, 'e'): 592,
  (273, 'f'): 594,
  (274, '0'): 552,
  (274, '1'): 551,
  (274, '2'): 554,
  (274, '3'): 553,
  (274, '4'): 556,
  (274, '5'): 555,
  (274, '6'): 558,
  (274, '7'): 557,
  (274, '8'): 560,
  (274, '9'): 559,
  (274, 'A'): 561,
  (274, 'B'): 563,
  (274, 'C'): 562,
  (274, 'D'): 565,
  (274, 'E'): 564,
  (274, 'F'): 566,
  (274, 'a'): 567,
  (274, 'b'): 569,
  (274, 'c'): 568,
  (274, 'd'): 571,
  (274, 'e'): 570,
  (274, 'f'): 572,
  (275, '0'): 530,
  (275, '1'): 529,
  (275, '2'): 532,
  (275, '3'): 531,
  (275, '4'): 534,
  (275, '5'): 533,
  (275, '6'): 536,
  (275, '7'): 535,
  (275, '8'): 538,
  (275, '9'): 537,
  (275, 'A'): 539,
  (275, 'B'): 541,
  (275, 'C'): 540,
  (275, 'D'): 543,
  (275, 'E'): 542,
  (275, 'F'): 544,
  (275, 'a'): 545,
  (275, 'b'): 547,
  (275, 'c'): 546,
  (275, 'd'): 549,
  (275, 'e'): 548,
  (275, 'f'): 550,
  (276, '0'): 508,
  (276, '1'): 507,
  (276, '2'): 510,
  (276, '3'): 509,
  (276, '4'): 512,
  (276, '5'): 511,
  (276, '6'): 514,
  (276, '7'): 513,
  (276, '8'): 516,
  (276, '9'): 515,
  (276, 'A'): 517,
  (276, 'B'): 519,
  (276, 'C'): 518,
  (276, 'D'): 521,
  (276, 'E'): 520,
  (276, 'F'): 522,
  (276, 'a'): 523,
  (276, 'b'): 525,
  (276, 'c'): 524,
  (276, 'd'): 527,
  (276, 'e'): 526,
  (276, 'f'): 528,
  (277, '0'): 486,
  (277, '1'): 485,
  (277, '2'): 488,
  (277, '3'): 487,
  (277, '4'): 490,
  (277, '5'): 489,
  (277, '6'): 492,
  (277, '7'): 491,
  (277, '8'): 494,
  (277, '9'): 493,
  (277, 'A'): 495,
  (277, 'B'): 497,
  (277, 'C'): 496,
  (277, 'D'): 499,
  (277, 'E'): 498,
  (277, 'F'): 500,
  (277, 'a'): 501,
  (277, 'b'): 503,
  (277, 'c'): 502,
  (277, 'd'): 505,
  (277, 'e'): 504,
  (277, 'f'): 506,
  (278, '0'): 464,
  (278, '1'): 463,
  (278, '2'): 466,
  (278, '3'): 465,
  (278, '4'): 468,
  (278, '5'): 467,
  (278, '6'): 470,
  (278, '7'): 469,
  (278, '8'): 472,
  (278, '9'): 471,
  (278, 'A'): 473,
  (278, 'B'): 475,
  (278, 'C'): 474,
  (278, 'D'): 477,
  (278, 'E'): 476,
  (278, 'F'): 478,
  (278, 'a'): 479,
  (278, 'b'): 481,
  (278, 'c'): 480,
  (278, 'd'): 483,
  (278, 'e'): 482,
  (278, 'f'): 484,
  (279, '0'): 442,
  (279, '1'): 441,
  (279, '2'): 444,
  (279, '3'): 443,
  (279, '4'): 446,
  (279, '5'): 445,
  (279, '6'): 448,
  (279, '7'): 447,
  (279, '8'): 450,
  (279, '9'): 449,
  (279, 'A'): 451,
  (279, 'B'): 453,
  (279, 'C'): 452,
  (279, 'D'): 455,
  (279, 'E'): 454,
  (279, 'F'): 456,
  (279, 'a'): 457,
  (279, 'b'): 459,
  (279, 'c'): 458,
  (279, 'd'): 461,
  (279, 'e'): 460,
  (279, 'f'): 462,
  (280, '0'): 420,
  (280, '1'): 419,
  (280, '2'): 422,
  (280, '3'): 421,
  (280, '4'): 424,
  (280, '5'): 423,
  (280, '6'): 426,
  (280, '7'): 425,
  (280, '8'): 428,
  (280, '9'): 427,
  (280, 'A'): 429,
  (280, 'B'): 431,
  (280, 'C'): 430,
  (280, 'D'): 433,
  (280, 'E'): 432,
  (280, 'F'): 434,
  (280, 'a'): 435,
  (280, 'b'): 437,
  (280, 'c'): 436,
  (280, 'd'): 439,
  (280, 'e'): 438,
  (280, 'f'): 440,
  (281, '0'): 398,
  (281, '1'): 397,
  (281, '2'): 400,
  (281, '3'): 399,
  (281, '4'): 402,
  (281, '5'): 401,
  (281, '6'): 404,
  (281, '7'): 403,
  (281, '8'): 406,
  (281, '9'): 405,
  (281, 'A'): 407,
  (281, 'B'): 409,
  (281, 'C'): 408,
  (281, 'D'): 411,
  (281, 'E'): 410,
  (281, 'F'): 412,
  (281, 'a'): 413,
  (281, 'b'): 415,
  (281, 'c'): 414,
  (281, 'd'): 417,
  (281, 'e'): 416,
  (281, 'f'): 418,
  (282, '0'): 376,
  (282, '1'): 375,
  (282, '2'): 378,
  (282, '3'): 377,
  (282, '4'): 380,
  (282, '5'): 379,
  (282, '6'): 382,
  (282, '7'): 381,
  (282, '8'): 384,
  (282, '9'): 383,
  (282, 'A'): 385,
  (282, 'B'): 387,
  (282, 'C'): 386,
  (282, 'D'): 389,
  (282, 'E'): 388,
  (282, 'F'): 390,
  (282, 'a'): 391,
  (282, 'b'): 393,
  (282, 'c'): 392,
  (282, 'd'): 395,
  (282, 'e'): 394,
  (282, 'f'): 396,
  (283, '0'): 354,
  (283, '1'): 353,
  (283, '2'): 356,
  (283, '3'): 355,
  (283, '4'): 358,
  (283, '5'): 357,
  (283, '6'): 360,
  (283, '7'): 359,
  (283, '8'): 362,
  (283, '9'): 361,
  (283, 'A'): 363,
  (283, 'B'): 365,
  (283, 'C'): 364,
  (283, 'D'): 367,
  (283, 'E'): 366,
  (283, 'F'): 368,
  (283, 'a'): 369,
  (283, 'b'): 371,
  (283, 'c'): 370,
  (283, 'd'): 373,
  (283, 'e'): 372,
  (283, 'f'): 374,
  (284, '0'): 332,
  (284, '1'): 331,
  (284, '2'): 334,
  (284, '3'): 333,
  (284, '4'): 336,
  (284, '5'): 335,
  (284, '6'): 338,
  (284, '7'): 337,
  (284, '8'): 340,
  (284, '9'): 339,
  (284, 'A'): 341,
  (284, 'B'): 343,
  (284, 'C'): 342,
  (284, 'D'): 345,
  (284, 'E'): 344,
  (284, 'F'): 346,
  (284, 'a'): 347,
  (284, 'b'): 349,
  (284, 'c'): 348,
  (284, 'd'): 351,
  (284, 'e'): 350,
  (284, 'f'): 352,
  (285, '0'): 310,
  (285, '1'): 309,
  (285, '2'): 312,
  (285, '3'): 311,
  (285, '4'): 314,
  (285, '5'): 313,
  (285, '6'): 316,
  (285, '7'): 315,
  (285, '8'): 318,
  (285, '9'): 317,
  (285, 'A'): 319,
  (285, 'B'): 321,
  (285, 'C'): 320,
  (285, 'D'): 323,
  (285, 'E'): 322,
  (285, 'F'): 324,
  (285, 'a'): 325,
  (285, 'b'): 327,
  (285, 'c'): 326,
  (285, 'd'): 329,
  (285, 'e'): 328,
  (285, 'f'): 330,
  (286, '0'): 288,
  (286, '1'): 287,
  (286, '2'): 290,
  (286, '3'): 289,
  (286, '4'): 292,
  (286, '5'): 291,
  (286, '6'): 294,
  (286, '7'): 293,
  (286, '8'): 296,
  (286, '9'): 295,
  (286, 'A'): 297,
  (286, 'B'): 299,
  (286, 'C'): 298,
  (286, 'D'): 301,
  (286, 'E'): 300,
  (286, 'F'): 302,
  (286, 'a'): 303,
  (286, 'b'): 305,
  (286, 'c'): 304,
  (286, 'd'): 307,
  (286, 'e'): 306,
  (286, 'f'): 308,
  (683, '0'): 762,
  (683, '1'): 761,
  (683, '2'): 764,
  (683, '3'): 763,
  (683, '4'): 766,
  (683, '5'): 765,
  (683, '6'): 768,
  (683, '7'): 767,
  (684, '0'): 754,
  (684, '1'): 753,
  (684, '2'): 756,
  (684, '3'): 755,
  (684, '4'): 758,
  (684, '5'): 757,
  (684, '6'): 760,
  (684, '7'): 759,
  (685, '0'): 746,
  (685, '1'): 745,
  (685, '2'): 748,
  (685, '3'): 747,
  (685, '4'): 750,
  (685, '5'): 749,
  (685, '6'): 752,
  (685, '7'): 751,
  (686, '0'): 738,
  (686, '1'): 737,
  (686, '2'): 740,
  (686, '3'): 739,
  (686, '4'): 742,
  (686, '5'): 741,
  (686, '6'): 744,
  (686, '7'): 743,
  (687, '0'): 730,
  (687, '1'): 729,
  (687, '2'): 732,
  (687, '3'): 731,
  (687, '4'): 734,
  (687, '5'): 733,
  (687, '6'): 736,
  (687, '7'): 735,
  (688, '0'): 722,
  (688, '1'): 721,
  (688, '2'): 724,
  (688, '3'): 723,
  (688, '4'): 726,
  (688, '5'): 725,
  (688, '6'): 728,
  (688, '7'): 727,
  (689, '0'): 714,
  (689, '1'): 713,
  (689, '2'): 716,
  (689, '3'): 715,
  (689, '4'): 718,
  (689, '5'): 717,
  (689, '6'): 720,
  (689, '7'): 719,
  (690, '0'): 706,
  (690, '1'): 705,
  (690, '2'): 708,
  (690, '3'): 707,
  (690, '4'): 710,
  (690, '5'): 709,
  (690, '6'): 712,
  (690, '7'): 711,
  (769, '0'): 848,
  (769, '1'): 847,
  (769, '2'): 850,
  (769, '3'): 849,
  (769, '4'): 852,
  (769, '5'): 851,
  (769, '6'): 854,
  (769, '7'): 853,
  (770, '0'): 840,
  (770, '1'): 839,
  (770, '2'): 842,
  (770, '3'): 841,
  (770, '4'): 844,
  (770, '5'): 843,
  (770, '6'): 846,
  (770, '7'): 845,
  (771, '0'): 832,
  (771, '1'): 831,
  (771, '2'): 834,
  (771, '3'): 833,
  (771, '4'): 836,
  (771, '5'): 835,
  (771, '6'): 838,
  (771, '7'): 837,
  (772, '0'): 824,
  (772, '1'): 823,
  (772, '2'): 826,
  (772, '3'): 825,
  (772, '4'): 828,
  (772, '5'): 827,
  (772, '6'): 830,
  (772, '7'): 829,
  (773, '0'): 816,
  (773, '1'): 815,
  (773, '2'): 818,
  (773, '3'): 817,
  (773, '4'): 820,
  (773, '5'): 819,
  (773, '6'): 822,
  (773, '7'): 821,
  (774, '0'): 808,
  (774, '1'): 807,
  (774, '2'): 810,
  (774, '3'): 809,
  (774, '4'): 812,
  (774, '5'): 811,
  (774, '6'): 814,
  (774, '7'): 813,
  (775, '0'): 800,
  (775, '1'): 799,
  (775, '2'): 802,
  (775, '3'): 801,
  (775, '4'): 804,
  (775, '5'): 803,
  (775, '6'): 806,
  (775, '7'): 805,
  (776, '0'): 792,
  (776, '1'): 791,
  (776, '2'): 794,
  (776, '3'): 793,
  (776, '4'): 796,
  (776, '5'): 795,
  (776, '6'): 798,
  (776, '7'): 797,
  (855, '0'): 934,
  (855, '1'): 933,
  (855, '2'): 936,
  (855, '3'): 935,
  (855, '4'): 938,
  (855, '5'): 937,
  (855, '6'): 940,
  (855, '7'): 939,
  (856, '0'): 926,
  (856, '1'): 925,
  (856, '2'): 928,
  (856, '3'): 927,
  (856, '4'): 930,
  (856, '5'): 929,
  (856, '6'): 932,
  (856, '7'): 931,
  (857, '0'): 918,
  (857, '1'): 917,
  (857, '2'): 920,
  (857, '3'): 919,
  (857, '4'): 922,
  (857, '5'): 921,
  (857, '6'): 924,
  (857, '7'): 923,
  (858, '0'): 910,
  (858, '1'): 909,
  (858, '2'): 912,
  (858, '3'): 911,
  (858, '4'): 914,
  (858, '5'): 913,
  (858, '6'): 916,
  (858, '7'): 915,
  (859, '0'): 902,
  (859, '1'): 901,
  (859, '2'): 904,
  (859, '3'): 903,
  (859, '4'): 906,
  (859, '5'): 905,
  (859, '6'): 908,
  (859, '7'): 907,
  (860, '0'): 894,
  (860, '1'): 893,
  (860, '2'): 896,
  (860, '3'): 895,
  (860, '4'): 898,
  (860, '5'): 897,
  (860, '6'): 900,
  (860, '7'): 899,
  (861, '0'): 886,
  (861, '1'): 885,
  (861, '2'): 888,
  (861, '3'): 887,
  (861, '4'): 890,
  (861, '5'): 889,
  (861, '6'): 892,
  (861, '7'): 891,
  (862, '0'): 878,
  (862, '1'): 877,
  (862, '2'): 880,
  (862, '3'): 879,
  (862, '4'): 882,
  (862, '5'): 881,
  (862, '6'): 884,
  (862, '7'): 883,
  (941, '0'): 1020,
  (941, '1'): 1019,
  (941, '2'): 1022,
  (941, '3'): 1021,
  (941, '4'): 1024,
  (941, '5'): 1023,
  (941, '6'): 1026,
  (941, '7'): 1025,
  (942, '0'): 1012,
  (942, '1'): 1011,
  (942, '2'): 1014,
  (942, '3'): 1013,
  (942, '4'): 1016,
  (942, '5'): 1015,
  (942, '6'): 1018,
  (942, '7'): 1017,
  (943, '0'): 1004,
  (943, '1'): 1003,
  (943, '2'): 1006,
  (943, '3'): 1005,
  (943, '4'): 1008,
  (943, '5'): 1007,
  (943, '6'): 1010,
  (943, '7'): 1009,
  (944, '0'): 996,
  (944, '1'): 995,
  (944, '2'): 998,
  (944, '3'): 997,
  (944, '4'): 1000,
  (944, '5'): 999,
  (944, '6'): 1002,
  (944, '7'): 1001,
  (945, '0'): 988,
  (945, '1'): 987,
  (945, '2'): 990,
  (945, '3'): 989,
  (945, '4'): 992,
  (945, '5'): 991,
  (945, '6'): 994,
  (945, '7'): 993,
  (946, '0'): 980,
  (946, '1'): 979,
  (946, '2'): 982,
  (946, '3'): 981,
  (946, '4'): 984,
  (946, '5'): 983,
  (946, '6'): 986,
  (946, '7'): 985,
  (947, '0'): 972,
  (947, '1'): 971,
  (947, '2'): 974,
  (947, '3'): 973,
  (947, '4'): 976,
  (947, '5'): 975,
  (947, '6'): 978,
  (947, '7'): 977,
  (948, '0'): 964,
  (948, '1'): 963,
  (948, '2'): 966,
  (948, '3'): 965,
  (948, '4'): 968,
  (948, '5'): 967,
  (948, '6'): 970,
  (948, '7'): 969},
 set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981, 982, 983, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022, 1023, 1024, 1025, 1026]),
 set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802, 803, 804, 805, 806, 807, 808, 809, 810, 811, 812, 813, 814, 815, 816, 817, 818, 819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831, 832, 833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845, 846, 847, 848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 877, 878, 879, 880, 881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893, 894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 918, 919, 920, 921, 922, 923, 924, 925, 926, 927, 928, 929, 930, 931, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981, 982, 983, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022, 1023, 1024, 1025, 1026]),
 ['0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0',
  'CHAR',
  '__6_(',
  '__13_,',
  'QUOTEDCHAR',
  '__0_|',
  '__2_+',
  '__3_?',
  '__8_[',
  '__4_{',
  '__1_*',
  '__10_.',
  '__11_^',
  '__7_)',
  '__12_-',
  '__9_]',
  '__5_}',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  '2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  '3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR']), {})
# generated code between this line and its other occurence

if __name__ == '__main__':
    f = py.magic.autopath()
    oldcontent = f.read()
    s = "# GENERATED CODE BETWEEN THIS LINE AND ITS OTHER OCCURENCE\n".lower()
    pre, gen, after = oldcontent.split(s)

    parser, lexer, ToAST = make_regex_parser()
    transformer = ToAST.source
    newcontent = "%s%s%s\nparser = %r\n%s\n%s%s" % (
            pre, s, ToAST.source.replace("ToAST", "RegexToAST"),
            parser, lexer.get_dummy_repr(), s, after)
    print newcontent
    f.write(newcontent)
