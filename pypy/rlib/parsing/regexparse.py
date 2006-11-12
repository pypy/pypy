import py
from pypy.rlib.parsing.parsing import PackratParser, Rule
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

def make_regex_parser():
    from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
    # construct regular expressions by hand, to not go completely insane
    # because of quoting
    special_chars = "*+()[]{}|.-?,^"
    # lexer
    QUOTES = []
    for i in range(256):
        # 'x' is reserved for hexadecimal escapes
        if chr(i) != 'x':
            QUOTES.append(StringExpression("\\" + chr(i)))
    for a in "0123456789ABCDEFabcdef":
        for b in "0123456789ABCDEFabcdef":
            QUOTES.append(StringExpression("\\x%s%s" % (a, b)))
    REST = StringExpression("a")
    for p in string.printable:
        if p not in special_chars:
            REST = REST | StringExpression(p)
    regexs1 = QUOTES + [REST]
    names1 = ['QUOTEDCHAR'] * len(QUOTES) + ['CHAR']
    # parser
    rs, rules, transformer = parse_ebnf("""
    regex: concatenation "|" regex | concatenation;
    concatenation: repetition concatenation | repetition;
    repetition: primary "*" |
                primary "+" |
                primary "?" |
                primary "{" numrange "}" |
                primary;
    primary: "(" regex ")" |
             "[" range "]" |
             char | ".";
    char: QUOTEDCHAR | CHAR;
    range: "^" subrange | subrange;
    subrange: char "-" char subrange | char "-" char | char subrange | char;
    numrange: num "," num | num;
    num: CHAR num | CHAR;
    """)
    names2, regexs2 = zip(*rs)
    lexer = Lexer(regexs1 + list(regexs2), names1 + list(names2))
    parser = PackratParser(rules, "regex")
    return parser, lexer

def parse_regex(s):
    tokens = lexer.tokenize(s)
    s = parser.parse(tokens)
    return s.visit(RegexBuilder())

class RegexBuilder(object):
    def visit_regex(self, node):
        if len(node.children) == 1:
            return node.children[0].visit(self)
        return node.children[0].visit(self) | node.children[2].visit(self)
    def visit_concatenation(self, node):
        if len(node.children) == 1:
            return node.children[0].visit(self)
        return node.children[0].visit(self) + node.children[1].visit(self)
    def visit_repetition(self, node):
        if len(node.children) == 1:
            return node.children[0].visit(self)
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
        if node.children[1].symbol == "*":
            return node.children[0].visit(self).kleene()
        elif node.children[1].symbol == "+":
            return + node.children[0].visit(self)
        elif node.children[1].symbol == "?":
            return StringExpression("") | node.children[0].visit(self)
    def visit_primary(self, node):
        if len(node.children) == 1:
            if node.children[0].symbol == "char":
                return node.children[0].visit(self)
            elif node.children[0].symbol == ".":
                return RangeExpression(chr(0), chr(255))
            raise ParserError
        if node.children[0].symbol == "(":
            return node.children[1].visit(self)
        else:
            return node.children[1].visit(self)
    def visit_char(self, node):
        if node.children[0].symbol == "QUOTEDCHAR":
            quote = node.children[0].additional_info
            if quote in ESCAPES:
                return StringExpression(ESCAPES[quote])
            if quote[1] == "x":
                return StringExpression(chr(int(quote[2:], 16)))
            return StringExpression(node.children[0].additional_info[-1])
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
        if len(node.children) >= 3:
            r = (node.children[0].visit(self).string,
                 node.children[2].visit(self).string)
        else:
            char = node.children[0].visit(self).string
            r = (char, char)
        if len(node.children) in (2, 4):
            return [r] + node.children[-1].visit(self)
        else:
            return [r]
    def visit_numrange(self, node):
        if len(node.children) == 3:
            r1 = node.children[0].visit(self)
            r2 = node.children[2].visit(self) + 1
        else:
            r1 = node.children[0].visit(self)
            r2 = r1 + 1
        return r1, r2
    def visit_num(self, node):
        if len(node.children) == 2:
            return (int(node.children[0].additional_info) * 10 +
                    node.children[1].visit(self))
        return int(node.children[0].additional_info)



# generated code between this line and its other occurence
parser = PackratParser([Rule('regex', [['concatenation', '|', 'regex'], ['concatenation']]),
  Rule('concatenation', [['repetition', 'concatenation'], ['repetition']]),
  Rule('repetition', [['primary', '*'], ['primary', '+'], ['primary', '?'], ['primary', '{', 'numrange', '}'], ['primary']]),
  Rule('primary', [['(', 'regex', ')'], ['[', 'range', ']'], ['char'], ['.']]),
  Rule('char', [['QUOTEDCHAR'], ['CHAR']]),
  Rule('range', [['^', 'subrange'], ['subrange']]),
  Rule('subrange', [['char', '-', 'char', 'subrange'], ['char', '-', 'char'], ['char', 'subrange'], ['char']]),
  Rule('numrange', [['num', ',', 'num'], ['num']]),
  Rule('num', [['CHAR', 'num'], ['CHAR']])],
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
            elif char == '0':
                state = 41
            elif char == '\xb3':
                state = 42
            elif char == '4':
                state = 43
            elif char == '\xb7':
                state = 44
            elif char == '8':
                state = 45
            elif char == '\xbb':
                state = 46
            elif char == '<':
                state = 47
            elif char == '\xbf':
                state = 48
            elif char == '@':
                state = 49
            elif char == '\xc3':
                state = 50
            elif char == 'D':
                state = 51
            elif char == '\xc7':
                state = 52
            elif char == 'H':
                state = 53
            elif char == '\xcb':
                state = 54
            elif char == 'L':
                state = 55
            elif char == '\xcf':
                state = 56
            elif char == 'P':
                state = 57
            elif char == '\xd3':
                state = 58
            elif char == 'T':
                state = 59
            elif char == '\xd7':
                state = 60
            elif char == 'X':
                state = 61
            elif char == '\xdb':
                state = 62
            elif char == '\\':
                state = 63
            elif char == '\xdf':
                state = 64
            elif char == '`':
                state = 65
            elif char == '\xe3':
                state = 66
            elif char == 'd':
                state = 67
            elif char == '\xe7':
                state = 68
            elif char == 'h':
                state = 69
            elif char == '\xeb':
                state = 70
            elif char == 'l':
                state = 71
            elif char == '\xef':
                state = 72
            elif char == 'p':
                state = 73
            elif char == '\xf3':
                state = 74
            elif char == 't':
                state = 75
            elif char == '\xf7':
                state = 76
            elif char == 'x':
                state = 77
            elif char == '\xfb':
                state = 78
            elif char == '|':
                state = 79
            elif char == '\xff':
                state = 80
            elif char == '\x80':
                state = 81
            elif char == '\x03':
                state = 82
            elif char == '\x84':
                state = 83
            elif char == '\x07':
                state = 84
            elif char == '\x88':
                state = 85
            elif char == '\x0b':
                state = 86
            elif char == '\x8c':
                state = 87
            elif char == '\x0f':
                state = 88
            elif char == '\x90':
                state = 89
            elif char == '\x13':
                state = 90
            elif char == '\x94':
                state = 91
            elif char == '\x17':
                state = 92
            elif char == '\x98':
                state = 93
            elif char == '\x1b':
                state = 94
            elif char == '\x9c':
                state = 95
            elif char == '\x1f':
                state = 96
            elif char == '\xa0':
                state = 97
            elif char == '#':
                state = 98
            elif char == '\xa4':
                state = 99
            elif char == "'":
                state = 100
            elif char == '\xa8':
                state = 101
            elif char == '+':
                state = 102
            elif char == '\xac':
                state = 103
            elif char == '/':
                state = 104
            elif char == '\xb0':
                state = 105
            elif char == '3':
                state = 106
            elif char == '\xb4':
                state = 107
            elif char == '7':
                state = 108
            elif char == '\xb8':
                state = 109
            elif char == ';':
                state = 110
            elif char == '\xbc':
                state = 111
            elif char == '?':
                state = 112
            elif char == '\xc0':
                state = 113
            elif char == 'C':
                state = 114
            elif char == '\xc4':
                state = 115
            elif char == 'G':
                state = 116
            elif char == '\xc8':
                state = 117
            elif char == 'K':
                state = 118
            elif char == '\xcc':
                state = 119
            elif char == 'O':
                state = 120
            elif char == '\xd0':
                state = 121
            elif char == 'S':
                state = 122
            elif char == '\xd4':
                state = 123
            elif char == 'W':
                state = 124
            elif char == '\xd8':
                state = 125
            elif char == '[':
                state = 126
            elif char == '\xdc':
                state = 127
            elif char == '_':
                state = 128
            elif char == '\xe0':
                state = 129
            elif char == 'c':
                state = 130
            elif char == '\xe4':
                state = 131
            elif char == 'g':
                state = 132
            elif char == '\xe8':
                state = 133
            elif char == 'k':
                state = 134
            elif char == '\xec':
                state = 135
            elif char == 'o':
                state = 136
            elif char == '\xf0':
                state = 137
            elif char == 's':
                state = 138
            elif char == '\xf4':
                state = 139
            elif char == 'w':
                state = 140
            elif char == '\xf8':
                state = 141
            elif char == '{':
                state = 142
            elif char == '\xfc':
                state = 143
            elif char == '\x7f':
                state = 144
            elif char == '\x81':
                state = 145
            elif char == '\x02':
                state = 146
            elif char == '\x85':
                state = 147
            elif char == '\x06':
                state = 148
            elif char == '\x89':
                state = 149
            elif char == '\n':
                state = 150
            elif char == '\x8d':
                state = 151
            elif char == '\x0e':
                state = 152
            elif char == '\x91':
                state = 153
            elif char == '\x12':
                state = 154
            elif char == '\x95':
                state = 155
            elif char == '\x16':
                state = 156
            elif char == '\x99':
                state = 157
            elif char == '\x1a':
                state = 158
            elif char == '\x9d':
                state = 159
            elif char == '\x1e':
                state = 160
            elif char == '\xa1':
                state = 161
            elif char == '"':
                state = 162
            elif char == '\xa5':
                state = 163
            elif char == '&':
                state = 164
            elif char == '\xa9':
                state = 165
            elif char == '*':
                state = 166
            elif char == '\xad':
                state = 167
            elif char == '.':
                state = 168
            elif char == '\xb1':
                state = 169
            elif char == '2':
                state = 170
            elif char == '\xb5':
                state = 171
            elif char == '6':
                state = 172
            elif char == '\xb9':
                state = 173
            elif char == ':':
                state = 174
            elif char == '\xbd':
                state = 175
            elif char == '>':
                state = 176
            elif char == '\xc1':
                state = 177
            elif char == 'B':
                state = 178
            elif char == '\xc5':
                state = 179
            elif char == 'F':
                state = 180
            elif char == '\xc9':
                state = 181
            elif char == 'J':
                state = 182
            elif char == '\xcd':
                state = 183
            elif char == 'N':
                state = 184
            elif char == '\xd1':
                state = 185
            elif char == 'R':
                state = 186
            elif char == '\xd5':
                state = 187
            elif char == 'V':
                state = 188
            elif char == '\xd9':
                state = 189
            elif char == 'Z':
                state = 190
            elif char == '\xdd':
                state = 191
            elif char == '^':
                state = 192
            elif char == '\xe1':
                state = 193
            elif char == 'b':
                state = 194
            elif char == '\xe5':
                state = 195
            elif char == 'f':
                state = 196
            elif char == '\xe9':
                state = 197
            elif char == 'j':
                state = 198
            elif char == '\xed':
                state = 199
            elif char == 'n':
                state = 200
            elif char == '\xf1':
                state = 201
            elif char == 'r':
                state = 202
            elif char == '\xf5':
                state = 203
            elif char == 'v':
                state = 204
            elif char == '\xf9':
                state = 205
            elif char == 'z':
                state = 206
            elif char == '\xfd':
                state = 207
            elif char == '~':
                state = 208
            elif char == '\x01':
                state = 209
            elif char == '\x82':
                state = 210
            elif char == '\x05':
                state = 211
            elif char == '\x86':
                state = 212
            elif char == '\t':
                state = 213
            elif char == '\x8a':
                state = 214
            elif char == '\r':
                state = 215
            elif char == '\x8e':
                state = 216
            elif char == '\x11':
                state = 217
            elif char == '\x92':
                state = 218
            elif char == '\x15':
                state = 219
            elif char == '\x96':
                state = 220
            elif char == '\x19':
                state = 221
            elif char == '\x9a':
                state = 222
            elif char == '\x1d':
                state = 223
            elif char == '\x9e':
                state = 224
            elif char == '!':
                state = 225
            elif char == '\xa2':
                state = 226
            elif char == '%':
                state = 227
            elif char == '\xa6':
                state = 228
            elif char == ')':
                state = 229
            elif char == '\xaa':
                state = 230
            elif char == '-':
                state = 231
            elif char == '\xae':
                state = 232
            elif char == '1':
                state = 233
            elif char == '\xb2':
                state = 234
            elif char == '5':
                state = 235
            elif char == '\xb6':
                state = 236
            elif char == '9':
                state = 237
            elif char == '\xba':
                state = 238
            elif char == '=':
                state = 239
            elif char == '\xbe':
                state = 240
            elif char == 'A':
                state = 241
            elif char == '\xc2':
                state = 242
            elif char == 'E':
                state = 243
            elif char == '\xc6':
                state = 244
            elif char == 'I':
                state = 245
            elif char == '\xca':
                state = 246
            elif char == 'M':
                state = 247
            elif char == '\xce':
                state = 248
            elif char == 'Q':
                state = 249
            elif char == '\xd2':
                state = 250
            elif char == 'U':
                state = 251
            elif char == '\xd6':
                state = 252
            elif char == 'Y':
                state = 253
            elif char == '\xda':
                state = 254
            elif char == ']':
                state = 255
            elif char == '\xde':
                state = 256
            elif char == 'a':
                state = 257
            elif char == '\xe2':
                state = 258
            elif char == 'e':
                state = 259
            elif char == '\xe6':
                state = 260
            elif char == 'i':
                state = 261
            elif char == '\xea':
                state = 262
            elif char == 'm':
                state = 263
            elif char == '\xee':
                state = 264
            elif char == 'q':
                state = 265
            elif char == '\xf2':
                state = 266
            elif char == 'u':
                state = 267
            elif char == '\xf6':
                state = 268
            elif char == 'y':
                state = 269
            elif char == '\xfa':
                state = 270
            elif char == '}':
                state = 271
            elif char == '\xfe':
                state = 272
            else:
                break
        if state == 273:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 273
                return ~i
            if char == 'C':
                state = 768
            elif char == 'B':
                state = 769
            elif char == 'E':
                state = 770
            elif char == 'D':
                state = 771
            elif char == 'F':
                state = 772
            elif char == 'a':
                state = 773
            elif char == 'c':
                state = 774
            elif char == 'b':
                state = 775
            elif char == 'e':
                state = 776
            elif char == 'd':
                state = 777
            elif char == 'f':
                state = 778
            elif char == '1':
                state = 757
            elif char == '0':
                state = 758
            elif char == '3':
                state = 759
            elif char == '2':
                state = 760
            elif char == '5':
                state = 761
            elif char == '4':
                state = 762
            elif char == '7':
                state = 763
            elif char == '6':
                state = 764
            elif char == '9':
                state = 765
            elif char == '8':
                state = 766
            elif char == 'A':
                state = 767
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
                state = 735
            elif char == '0':
                state = 736
            elif char == '3':
                state = 737
            elif char == '2':
                state = 738
            elif char == '5':
                state = 739
            elif char == '4':
                state = 740
            elif char == '7':
                state = 741
            elif char == '6':
                state = 742
            elif char == '9':
                state = 743
            elif char == '8':
                state = 744
            elif char == 'A':
                state = 745
            elif char == 'C':
                state = 746
            elif char == 'B':
                state = 747
            elif char == 'E':
                state = 748
            elif char == 'D':
                state = 749
            elif char == 'F':
                state = 750
            elif char == 'a':
                state = 751
            elif char == 'c':
                state = 752
            elif char == 'b':
                state = 753
            elif char == 'e':
                state = 754
            elif char == 'd':
                state = 755
            elif char == 'f':
                state = 756
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
            elif char == '9':
                state = 721
            elif char == '8':
                state = 722
            elif char == 'A':
                state = 723
            elif char == 'C':
                state = 724
            elif char == 'B':
                state = 725
            elif char == 'E':
                state = 726
            elif char == 'D':
                state = 727
            elif char == 'F':
                state = 728
            elif char == 'a':
                state = 729
            elif char == 'c':
                state = 730
            elif char == 'b':
                state = 731
            elif char == 'e':
                state = 732
            elif char == 'd':
                state = 733
            elif char == 'f':
                state = 734
            else:
                break
        if state == 276:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 276
                return ~i
            if char == '1':
                state = 691
            elif char == '0':
                state = 692
            elif char == '3':
                state = 693
            elif char == '2':
                state = 694
            elif char == '5':
                state = 695
            elif char == '4':
                state = 696
            elif char == '7':
                state = 697
            elif char == '6':
                state = 698
            elif char == '9':
                state = 699
            elif char == '8':
                state = 700
            elif char == 'A':
                state = 701
            elif char == 'C':
                state = 702
            elif char == 'B':
                state = 703
            elif char == 'E':
                state = 704
            elif char == 'D':
                state = 705
            elif char == 'F':
                state = 706
            elif char == 'a':
                state = 707
            elif char == 'c':
                state = 708
            elif char == 'b':
                state = 709
            elif char == 'e':
                state = 710
            elif char == 'd':
                state = 711
            elif char == 'f':
                state = 712
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
                state = 669
            elif char == '0':
                state = 670
            elif char == '3':
                state = 671
            elif char == '2':
                state = 672
            elif char == '5':
                state = 673
            elif char == '4':
                state = 674
            elif char == '7':
                state = 675
            elif char == '6':
                state = 676
            elif char == '9':
                state = 677
            elif char == '8':
                state = 678
            elif char == 'A':
                state = 679
            elif char == 'C':
                state = 680
            elif char == 'B':
                state = 681
            elif char == 'E':
                state = 682
            elif char == 'D':
                state = 683
            elif char == 'F':
                state = 684
            elif char == 'a':
                state = 685
            elif char == 'c':
                state = 686
            elif char == 'b':
                state = 687
            elif char == 'e':
                state = 688
            elif char == 'd':
                state = 689
            elif char == 'f':
                state = 690
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
                state = 647
            elif char == '0':
                state = 648
            elif char == '3':
                state = 649
            elif char == '2':
                state = 650
            elif char == '5':
                state = 651
            elif char == '4':
                state = 652
            elif char == '7':
                state = 653
            elif char == '6':
                state = 654
            elif char == '9':
                state = 655
            elif char == '8':
                state = 656
            elif char == 'A':
                state = 657
            elif char == 'C':
                state = 658
            elif char == 'B':
                state = 659
            elif char == 'E':
                state = 660
            elif char == 'D':
                state = 661
            elif char == 'F':
                state = 662
            elif char == 'a':
                state = 663
            elif char == 'c':
                state = 664
            elif char == 'b':
                state = 665
            elif char == 'e':
                state = 666
            elif char == 'd':
                state = 667
            elif char == 'f':
                state = 668
            else:
                break
        if state == 279:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 279
                return ~i
            if char == 'F':
                state = 640
            elif char == 'a':
                state = 641
            elif char == 'c':
                state = 642
            elif char == 'b':
                state = 643
            elif char == 'e':
                state = 644
            elif char == 'd':
                state = 645
            elif char == 'f':
                state = 646
            elif char == '1':
                state = 625
            elif char == '0':
                state = 626
            elif char == '3':
                state = 627
            elif char == '2':
                state = 628
            elif char == '5':
                state = 629
            elif char == '4':
                state = 630
            elif char == '7':
                state = 631
            elif char == '6':
                state = 632
            elif char == '9':
                state = 633
            elif char == '8':
                state = 634
            elif char == 'A':
                state = 635
            elif char == 'C':
                state = 636
            elif char == 'B':
                state = 637
            elif char == 'E':
                state = 638
            elif char == 'D':
                state = 639
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
                state = 603
            elif char == '0':
                state = 604
            elif char == '3':
                state = 605
            elif char == '2':
                state = 606
            elif char == '5':
                state = 607
            elif char == '4':
                state = 608
            elif char == '7':
                state = 609
            elif char == '6':
                state = 610
            elif char == '9':
                state = 611
            elif char == '8':
                state = 612
            elif char == 'A':
                state = 613
            elif char == 'C':
                state = 614
            elif char == 'B':
                state = 615
            elif char == 'E':
                state = 616
            elif char == 'D':
                state = 617
            elif char == 'F':
                state = 618
            elif char == 'a':
                state = 619
            elif char == 'c':
                state = 620
            elif char == 'b':
                state = 621
            elif char == 'e':
                state = 622
            elif char == 'd':
                state = 623
            elif char == 'f':
                state = 624
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
                state = 581
            elif char == '0':
                state = 582
            elif char == '3':
                state = 583
            elif char == '2':
                state = 584
            elif char == '5':
                state = 585
            elif char == '4':
                state = 586
            elif char == '7':
                state = 587
            elif char == '6':
                state = 588
            elif char == '9':
                state = 589
            elif char == '8':
                state = 590
            elif char == 'A':
                state = 591
            elif char == 'C':
                state = 592
            elif char == 'B':
                state = 593
            elif char == 'E':
                state = 594
            elif char == 'D':
                state = 595
            elif char == 'F':
                state = 596
            elif char == 'a':
                state = 597
            elif char == 'c':
                state = 598
            elif char == 'b':
                state = 599
            elif char == 'e':
                state = 600
            elif char == 'd':
                state = 601
            elif char == 'f':
                state = 602
            else:
                break
        if state == 282:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 282
                return ~i
            if char == '1':
                state = 559
            elif char == '0':
                state = 560
            elif char == '3':
                state = 561
            elif char == '2':
                state = 562
            elif char == '5':
                state = 563
            elif char == '4':
                state = 564
            elif char == '7':
                state = 565
            elif char == '6':
                state = 566
            elif char == '9':
                state = 567
            elif char == '8':
                state = 568
            elif char == 'A':
                state = 569
            elif char == 'C':
                state = 570
            elif char == 'B':
                state = 571
            elif char == 'E':
                state = 572
            elif char == 'D':
                state = 573
            elif char == 'F':
                state = 574
            elif char == 'a':
                state = 575
            elif char == 'c':
                state = 576
            elif char == 'b':
                state = 577
            elif char == 'e':
                state = 578
            elif char == 'd':
                state = 579
            elif char == 'f':
                state = 580
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
                state = 537
            elif char == '0':
                state = 538
            elif char == '3':
                state = 539
            elif char == '2':
                state = 540
            elif char == '5':
                state = 541
            elif char == '4':
                state = 542
            elif char == '7':
                state = 543
            elif char == '6':
                state = 544
            elif char == '9':
                state = 545
            elif char == '8':
                state = 546
            elif char == 'A':
                state = 547
            elif char == 'C':
                state = 548
            elif char == 'B':
                state = 549
            elif char == 'E':
                state = 550
            elif char == 'D':
                state = 551
            elif char == 'F':
                state = 552
            elif char == 'a':
                state = 553
            elif char == 'c':
                state = 554
            elif char == 'b':
                state = 555
            elif char == 'e':
                state = 556
            elif char == 'd':
                state = 557
            elif char == 'f':
                state = 558
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
                state = 515
            elif char == '0':
                state = 516
            elif char == '3':
                state = 517
            elif char == '2':
                state = 518
            elif char == '5':
                state = 519
            elif char == '4':
                state = 520
            elif char == '7':
                state = 521
            elif char == '6':
                state = 522
            elif char == '9':
                state = 523
            elif char == '8':
                state = 524
            elif char == 'A':
                state = 525
            elif char == 'C':
                state = 526
            elif char == 'B':
                state = 527
            elif char == 'E':
                state = 528
            elif char == 'D':
                state = 529
            elif char == 'F':
                state = 530
            elif char == 'a':
                state = 531
            elif char == 'c':
                state = 532
            elif char == 'b':
                state = 533
            elif char == 'e':
                state = 534
            elif char == 'd':
                state = 535
            elif char == 'f':
                state = 536
            else:
                break
        if state == 285:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 285
                return ~i
            if char == 'e':
                state = 512
            elif char == 'd':
                state = 513
            elif char == 'f':
                state = 514
            elif char == '1':
                state = 493
            elif char == '0':
                state = 494
            elif char == '3':
                state = 495
            elif char == '2':
                state = 496
            elif char == '5':
                state = 497
            elif char == '4':
                state = 498
            elif char == '7':
                state = 499
            elif char == '6':
                state = 500
            elif char == '9':
                state = 501
            elif char == '8':
                state = 502
            elif char == 'A':
                state = 503
            elif char == 'C':
                state = 504
            elif char == 'B':
                state = 505
            elif char == 'E':
                state = 506
            elif char == 'D':
                state = 507
            elif char == 'F':
                state = 508
            elif char == 'a':
                state = 509
            elif char == 'c':
                state = 510
            elif char == 'b':
                state = 511
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
                state = 471
            elif char == '0':
                state = 472
            elif char == '3':
                state = 473
            elif char == '2':
                state = 474
            elif char == '5':
                state = 475
            elif char == '4':
                state = 476
            elif char == '7':
                state = 477
            elif char == '6':
                state = 478
            elif char == '9':
                state = 479
            elif char == '8':
                state = 480
            elif char == 'A':
                state = 481
            elif char == 'C':
                state = 482
            elif char == 'B':
                state = 483
            elif char == 'E':
                state = 484
            elif char == 'D':
                state = 485
            elif char == 'F':
                state = 486
            elif char == 'a':
                state = 487
            elif char == 'c':
                state = 488
            elif char == 'b':
                state = 489
            elif char == 'e':
                state = 490
            elif char == 'd':
                state = 491
            elif char == 'f':
                state = 492
            else:
                break
        if state == 287:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 287
                return ~i
            if char == '1':
                state = 449
            elif char == '0':
                state = 450
            elif char == '3':
                state = 451
            elif char == '2':
                state = 452
            elif char == '5':
                state = 453
            elif char == '4':
                state = 454
            elif char == '7':
                state = 455
            elif char == '6':
                state = 456
            elif char == '9':
                state = 457
            elif char == '8':
                state = 458
            elif char == 'A':
                state = 459
            elif char == 'C':
                state = 460
            elif char == 'B':
                state = 461
            elif char == 'E':
                state = 462
            elif char == 'D':
                state = 463
            elif char == 'F':
                state = 464
            elif char == 'a':
                state = 465
            elif char == 'c':
                state = 466
            elif char == 'b':
                state = 467
            elif char == 'e':
                state = 468
            elif char == 'd':
                state = 469
            elif char == 'f':
                state = 470
            else:
                break
        if state == 288:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 288
                return ~i
            if char == '1':
                state = 427
            elif char == '0':
                state = 428
            elif char == '3':
                state = 429
            elif char == '2':
                state = 430
            elif char == '5':
                state = 431
            elif char == '4':
                state = 432
            elif char == '7':
                state = 433
            elif char == '6':
                state = 434
            elif char == '9':
                state = 435
            elif char == '8':
                state = 436
            elif char == 'A':
                state = 437
            elif char == 'C':
                state = 438
            elif char == 'B':
                state = 439
            elif char == 'E':
                state = 440
            elif char == 'D':
                state = 441
            elif char == 'F':
                state = 442
            elif char == 'a':
                state = 443
            elif char == 'c':
                state = 444
            elif char == 'b':
                state = 445
            elif char == 'e':
                state = 446
            elif char == 'd':
                state = 447
            elif char == 'f':
                state = 448
            else:
                break
        if state == 289:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 289
                return ~i
            if char == '1':
                state = 405
            elif char == '0':
                state = 406
            elif char == '3':
                state = 407
            elif char == '2':
                state = 408
            elif char == '5':
                state = 409
            elif char == '4':
                state = 410
            elif char == '7':
                state = 411
            elif char == '6':
                state = 412
            elif char == '9':
                state = 413
            elif char == '8':
                state = 414
            elif char == 'A':
                state = 415
            elif char == 'C':
                state = 416
            elif char == 'B':
                state = 417
            elif char == 'E':
                state = 418
            elif char == 'D':
                state = 419
            elif char == 'F':
                state = 420
            elif char == 'a':
                state = 421
            elif char == 'c':
                state = 422
            elif char == 'b':
                state = 423
            elif char == 'e':
                state = 424
            elif char == 'd':
                state = 425
            elif char == 'f':
                state = 426
            else:
                break
        if state == 290:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 290
                return ~i
            if char == '0':
                state = 384
            elif char == '3':
                state = 385
            elif char == '2':
                state = 386
            elif char == '5':
                state = 387
            elif char == '4':
                state = 388
            elif char == '7':
                state = 389
            elif char == '6':
                state = 390
            elif char == '9':
                state = 391
            elif char == '8':
                state = 392
            elif char == 'A':
                state = 393
            elif char == 'C':
                state = 394
            elif char == 'B':
                state = 395
            elif char == 'E':
                state = 396
            elif char == 'D':
                state = 397
            elif char == 'F':
                state = 398
            elif char == 'a':
                state = 399
            elif char == 'c':
                state = 400
            elif char == 'b':
                state = 401
            elif char == 'e':
                state = 402
            elif char == 'd':
                state = 403
            elif char == 'f':
                state = 404
            elif char == '1':
                state = 383
            else:
                break
        if state == 291:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 291
                return ~i
            if char == '1':
                state = 361
            elif char == '0':
                state = 362
            elif char == '3':
                state = 363
            elif char == '2':
                state = 364
            elif char == '5':
                state = 365
            elif char == '4':
                state = 366
            elif char == '7':
                state = 367
            elif char == '6':
                state = 368
            elif char == '9':
                state = 369
            elif char == '8':
                state = 370
            elif char == 'A':
                state = 371
            elif char == 'C':
                state = 372
            elif char == 'B':
                state = 373
            elif char == 'E':
                state = 374
            elif char == 'D':
                state = 375
            elif char == 'F':
                state = 376
            elif char == 'a':
                state = 377
            elif char == 'c':
                state = 378
            elif char == 'b':
                state = 379
            elif char == 'e':
                state = 380
            elif char == 'd':
                state = 381
            elif char == 'f':
                state = 382
            else:
                break
        if state == 292:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 292
                return ~i
            if char == '1':
                state = 339
            elif char == '0':
                state = 340
            elif char == '3':
                state = 341
            elif char == '2':
                state = 342
            elif char == '5':
                state = 343
            elif char == '4':
                state = 344
            elif char == '7':
                state = 345
            elif char == '6':
                state = 346
            elif char == '9':
                state = 347
            elif char == '8':
                state = 348
            elif char == 'A':
                state = 349
            elif char == 'C':
                state = 350
            elif char == 'B':
                state = 351
            elif char == 'E':
                state = 352
            elif char == 'D':
                state = 353
            elif char == 'F':
                state = 354
            elif char == 'a':
                state = 355
            elif char == 'c':
                state = 356
            elif char == 'b':
                state = 357
            elif char == 'e':
                state = 358
            elif char == 'd':
                state = 359
            elif char == 'f':
                state = 360
            else:
                break
        if state == 293:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 293
                return ~i
            if char == '1':
                state = 317
            elif char == '0':
                state = 318
            elif char == '3':
                state = 319
            elif char == '2':
                state = 320
            elif char == '5':
                state = 321
            elif char == '4':
                state = 322
            elif char == '7':
                state = 323
            elif char == '6':
                state = 324
            elif char == '9':
                state = 325
            elif char == '8':
                state = 326
            elif char == 'A':
                state = 327
            elif char == 'C':
                state = 328
            elif char == 'B':
                state = 329
            elif char == 'E':
                state = 330
            elif char == 'D':
                state = 331
            elif char == 'F':
                state = 332
            elif char == 'a':
                state = 333
            elif char == 'c':
                state = 334
            elif char == 'b':
                state = 335
            elif char == 'e':
                state = 336
            elif char == 'd':
                state = 337
            elif char == 'f':
                state = 338
            else:
                break
        if state == 294:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 294
                return ~i
            if char == '1':
                state = 295
            elif char == '0':
                state = 296
            elif char == '3':
                state = 297
            elif char == '2':
                state = 298
            elif char == '5':
                state = 299
            elif char == '4':
                state = 300
            elif char == '7':
                state = 301
            elif char == '6':
                state = 302
            elif char == '9':
                state = 303
            elif char == '8':
                state = 304
            elif char == 'A':
                state = 305
            elif char == 'C':
                state = 306
            elif char == 'B':
                state = 307
            elif char == 'E':
                state = 308
            elif char == 'D':
                state = 309
            elif char == 'F':
                state = 310
            elif char == 'a':
                state = 311
            elif char == 'c':
                state = 312
            elif char == 'b':
                state = 313
            elif char == 'e':
                state = 314
            elif char == 'd':
                state = 315
            elif char == 'f':
                state = 316
            else:
                break
        if state == 77:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 77
                return ~i
            if char == '1':
                state = 273
                continue
            elif char == '0':
                state = 274
                continue
            elif char == '3':
                state = 275
                continue
            elif char == '2':
                state = 276
                continue
            elif char == '5':
                state = 277
                continue
            elif char == '4':
                state = 278
                continue
            elif char == '7':
                state = 279
                continue
            elif char == '6':
                state = 280
                continue
            elif char == '9':
                state = 281
                continue
            elif char == '8':
                state = 282
                continue
            elif char == 'A':
                state = 283
                continue
            elif char == 'C':
                state = 284
                continue
            elif char == 'B':
                state = 285
                continue
            elif char == 'E':
                state = 286
                continue
            elif char == 'D':
                state = 287
                continue
            elif char == 'F':
                state = 288
                continue
            elif char == 'a':
                state = 289
                continue
            elif char == 'c':
                state = 290
                continue
            elif char == 'b':
                state = 291
                continue
            elif char == 'e':
                state = 292
                continue
            elif char == 'd':
                state = 293
                continue
            elif char == 'f':
                state = 294
                continue
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
lexer = DummyLexer(recognize, DFA(779,
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
  (4, '\x01'): 209,
  (4, '\x02'): 146,
  (4, '\x03'): 82,
  (4, '\x04'): 19,
  (4, '\x05'): 211,
  (4, '\x06'): 148,
  (4, '\x07'): 84,
  (4, '\x08'): 21,
  (4, '\t'): 213,
  (4, '\n'): 150,
  (4, '\x0b'): 86,
  (4, '\x0c'): 23,
  (4, '\r'): 215,
  (4, '\x0e'): 152,
  (4, '\x0f'): 88,
  (4, '\x10'): 25,
  (4, '\x11'): 217,
  (4, '\x12'): 154,
  (4, '\x13'): 90,
  (4, '\x14'): 27,
  (4, '\x15'): 219,
  (4, '\x16'): 156,
  (4, '\x17'): 92,
  (4, '\x18'): 29,
  (4, '\x19'): 221,
  (4, '\x1a'): 158,
  (4, '\x1b'): 94,
  (4, '\x1c'): 31,
  (4, '\x1d'): 223,
  (4, '\x1e'): 160,
  (4, '\x1f'): 96,
  (4, ' '): 33,
  (4, '!'): 225,
  (4, '"'): 162,
  (4, '#'): 98,
  (4, '$'): 35,
  (4, '%'): 227,
  (4, '&'): 164,
  (4, "'"): 100,
  (4, '('): 37,
  (4, ')'): 229,
  (4, '*'): 166,
  (4, '+'): 102,
  (4, ','): 39,
  (4, '-'): 231,
  (4, '.'): 168,
  (4, '/'): 104,
  (4, '0'): 41,
  (4, '1'): 233,
  (4, '2'): 170,
  (4, '3'): 106,
  (4, '4'): 43,
  (4, '5'): 235,
  (4, '6'): 172,
  (4, '7'): 108,
  (4, '8'): 45,
  (4, '9'): 237,
  (4, ':'): 174,
  (4, ';'): 110,
  (4, '<'): 47,
  (4, '='): 239,
  (4, '>'): 176,
  (4, '?'): 112,
  (4, '@'): 49,
  (4, 'A'): 241,
  (4, 'B'): 178,
  (4, 'C'): 114,
  (4, 'D'): 51,
  (4, 'E'): 243,
  (4, 'F'): 180,
  (4, 'G'): 116,
  (4, 'H'): 53,
  (4, 'I'): 245,
  (4, 'J'): 182,
  (4, 'K'): 118,
  (4, 'L'): 55,
  (4, 'M'): 247,
  (4, 'N'): 184,
  (4, 'O'): 120,
  (4, 'P'): 57,
  (4, 'Q'): 249,
  (4, 'R'): 186,
  (4, 'S'): 122,
  (4, 'T'): 59,
  (4, 'U'): 251,
  (4, 'V'): 188,
  (4, 'W'): 124,
  (4, 'X'): 61,
  (4, 'Y'): 253,
  (4, 'Z'): 190,
  (4, '['): 126,
  (4, '\\'): 63,
  (4, ']'): 255,
  (4, '^'): 192,
  (4, '_'): 128,
  (4, '`'): 65,
  (4, 'a'): 257,
  (4, 'b'): 194,
  (4, 'c'): 130,
  (4, 'd'): 67,
  (4, 'e'): 259,
  (4, 'f'): 196,
  (4, 'g'): 132,
  (4, 'h'): 69,
  (4, 'i'): 261,
  (4, 'j'): 198,
  (4, 'k'): 134,
  (4, 'l'): 71,
  (4, 'm'): 263,
  (4, 'n'): 200,
  (4, 'o'): 136,
  (4, 'p'): 73,
  (4, 'q'): 265,
  (4, 'r'): 202,
  (4, 's'): 138,
  (4, 't'): 75,
  (4, 'u'): 267,
  (4, 'v'): 204,
  (4, 'w'): 140,
  (4, 'x'): 77,
  (4, 'y'): 269,
  (4, 'z'): 206,
  (4, '{'): 142,
  (4, '|'): 79,
  (4, '}'): 271,
  (4, '~'): 208,
  (4, '\x7f'): 144,
  (4, '\x80'): 81,
  (4, '\x81'): 145,
  (4, '\x82'): 210,
  (4, '\x83'): 18,
  (4, '\x84'): 83,
  (4, '\x85'): 147,
  (4, '\x86'): 212,
  (4, '\x87'): 20,
  (4, '\x88'): 85,
  (4, '\x89'): 149,
  (4, '\x8a'): 214,
  (4, '\x8b'): 22,
  (4, '\x8c'): 87,
  (4, '\x8d'): 151,
  (4, '\x8e'): 216,
  (4, '\x8f'): 24,
  (4, '\x90'): 89,
  (4, '\x91'): 153,
  (4, '\x92'): 218,
  (4, '\x93'): 26,
  (4, '\x94'): 91,
  (4, '\x95'): 155,
  (4, '\x96'): 220,
  (4, '\x97'): 28,
  (4, '\x98'): 93,
  (4, '\x99'): 157,
  (4, '\x9a'): 222,
  (4, '\x9b'): 30,
  (4, '\x9c'): 95,
  (4, '\x9d'): 159,
  (4, '\x9e'): 224,
  (4, '\x9f'): 32,
  (4, '\xa0'): 97,
  (4, '\xa1'): 161,
  (4, '\xa2'): 226,
  (4, '\xa3'): 34,
  (4, '\xa4'): 99,
  (4, '\xa5'): 163,
  (4, '\xa6'): 228,
  (4, '\xa7'): 36,
  (4, '\xa8'): 101,
  (4, '\xa9'): 165,
  (4, '\xaa'): 230,
  (4, '\xab'): 38,
  (4, '\xac'): 103,
  (4, '\xad'): 167,
  (4, '\xae'): 232,
  (4, '\xaf'): 40,
  (4, '\xb0'): 105,
  (4, '\xb1'): 169,
  (4, '\xb2'): 234,
  (4, '\xb3'): 42,
  (4, '\xb4'): 107,
  (4, '\xb5'): 171,
  (4, '\xb6'): 236,
  (4, '\xb7'): 44,
  (4, '\xb8'): 109,
  (4, '\xb9'): 173,
  (4, '\xba'): 238,
  (4, '\xbb'): 46,
  (4, '\xbc'): 111,
  (4, '\xbd'): 175,
  (4, '\xbe'): 240,
  (4, '\xbf'): 48,
  (4, '\xc0'): 113,
  (4, '\xc1'): 177,
  (4, '\xc2'): 242,
  (4, '\xc3'): 50,
  (4, '\xc4'): 115,
  (4, '\xc5'): 179,
  (4, '\xc6'): 244,
  (4, '\xc7'): 52,
  (4, '\xc8'): 117,
  (4, '\xc9'): 181,
  (4, '\xca'): 246,
  (4, '\xcb'): 54,
  (4, '\xcc'): 119,
  (4, '\xcd'): 183,
  (4, '\xce'): 248,
  (4, '\xcf'): 56,
  (4, '\xd0'): 121,
  (4, '\xd1'): 185,
  (4, '\xd2'): 250,
  (4, '\xd3'): 58,
  (4, '\xd4'): 123,
  (4, '\xd5'): 187,
  (4, '\xd6'): 252,
  (4, '\xd7'): 60,
  (4, '\xd8'): 125,
  (4, '\xd9'): 189,
  (4, '\xda'): 254,
  (4, '\xdb'): 62,
  (4, '\xdc'): 127,
  (4, '\xdd'): 191,
  (4, '\xde'): 256,
  (4, '\xdf'): 64,
  (4, '\xe0'): 129,
  (4, '\xe1'): 193,
  (4, '\xe2'): 258,
  (4, '\xe3'): 66,
  (4, '\xe4'): 131,
  (4, '\xe5'): 195,
  (4, '\xe6'): 260,
  (4, '\xe7'): 68,
  (4, '\xe8'): 133,
  (4, '\xe9'): 197,
  (4, '\xea'): 262,
  (4, '\xeb'): 70,
  (4, '\xec'): 135,
  (4, '\xed'): 199,
  (4, '\xee'): 264,
  (4, '\xef'): 72,
  (4, '\xf0'): 137,
  (4, '\xf1'): 201,
  (4, '\xf2'): 266,
  (4, '\xf3'): 74,
  (4, '\xf4'): 139,
  (4, '\xf5'): 203,
  (4, '\xf6'): 268,
  (4, '\xf7'): 76,
  (4, '\xf8'): 141,
  (4, '\xf9'): 205,
  (4, '\xfa'): 270,
  (4, '\xfb'): 78,
  (4, '\xfc'): 143,
  (4, '\xfd'): 207,
  (4, '\xfe'): 272,
  (4, '\xff'): 80,
  (77, '0'): 274,
  (77, '1'): 273,
  (77, '2'): 276,
  (77, '3'): 275,
  (77, '4'): 278,
  (77, '5'): 277,
  (77, '6'): 280,
  (77, '7'): 279,
  (77, '8'): 282,
  (77, '9'): 281,
  (77, 'A'): 283,
  (77, 'B'): 285,
  (77, 'C'): 284,
  (77, 'D'): 287,
  (77, 'E'): 286,
  (77, 'F'): 288,
  (77, 'a'): 289,
  (77, 'b'): 291,
  (77, 'c'): 290,
  (77, 'd'): 293,
  (77, 'e'): 292,
  (77, 'f'): 294,
  (273, '0'): 758,
  (273, '1'): 757,
  (273, '2'): 760,
  (273, '3'): 759,
  (273, '4'): 762,
  (273, '5'): 761,
  (273, '6'): 764,
  (273, '7'): 763,
  (273, '8'): 766,
  (273, '9'): 765,
  (273, 'A'): 767,
  (273, 'B'): 769,
  (273, 'C'): 768,
  (273, 'D'): 771,
  (273, 'E'): 770,
  (273, 'F'): 772,
  (273, 'a'): 773,
  (273, 'b'): 775,
  (273, 'c'): 774,
  (273, 'd'): 777,
  (273, 'e'): 776,
  (273, 'f'): 778,
  (274, '0'): 736,
  (274, '1'): 735,
  (274, '2'): 738,
  (274, '3'): 737,
  (274, '4'): 740,
  (274, '5'): 739,
  (274, '6'): 742,
  (274, '7'): 741,
  (274, '8'): 744,
  (274, '9'): 743,
  (274, 'A'): 745,
  (274, 'B'): 747,
  (274, 'C'): 746,
  (274, 'D'): 749,
  (274, 'E'): 748,
  (274, 'F'): 750,
  (274, 'a'): 751,
  (274, 'b'): 753,
  (274, 'c'): 752,
  (274, 'd'): 755,
  (274, 'e'): 754,
  (274, 'f'): 756,
  (275, '0'): 714,
  (275, '1'): 713,
  (275, '2'): 716,
  (275, '3'): 715,
  (275, '4'): 718,
  (275, '5'): 717,
  (275, '6'): 720,
  (275, '7'): 719,
  (275, '8'): 722,
  (275, '9'): 721,
  (275, 'A'): 723,
  (275, 'B'): 725,
  (275, 'C'): 724,
  (275, 'D'): 727,
  (275, 'E'): 726,
  (275, 'F'): 728,
  (275, 'a'): 729,
  (275, 'b'): 731,
  (275, 'c'): 730,
  (275, 'd'): 733,
  (275, 'e'): 732,
  (275, 'f'): 734,
  (276, '0'): 692,
  (276, '1'): 691,
  (276, '2'): 694,
  (276, '3'): 693,
  (276, '4'): 696,
  (276, '5'): 695,
  (276, '6'): 698,
  (276, '7'): 697,
  (276, '8'): 700,
  (276, '9'): 699,
  (276, 'A'): 701,
  (276, 'B'): 703,
  (276, 'C'): 702,
  (276, 'D'): 705,
  (276, 'E'): 704,
  (276, 'F'): 706,
  (276, 'a'): 707,
  (276, 'b'): 709,
  (276, 'c'): 708,
  (276, 'd'): 711,
  (276, 'e'): 710,
  (276, 'f'): 712,
  (277, '0'): 670,
  (277, '1'): 669,
  (277, '2'): 672,
  (277, '3'): 671,
  (277, '4'): 674,
  (277, '5'): 673,
  (277, '6'): 676,
  (277, '7'): 675,
  (277, '8'): 678,
  (277, '9'): 677,
  (277, 'A'): 679,
  (277, 'B'): 681,
  (277, 'C'): 680,
  (277, 'D'): 683,
  (277, 'E'): 682,
  (277, 'F'): 684,
  (277, 'a'): 685,
  (277, 'b'): 687,
  (277, 'c'): 686,
  (277, 'd'): 689,
  (277, 'e'): 688,
  (277, 'f'): 690,
  (278, '0'): 648,
  (278, '1'): 647,
  (278, '2'): 650,
  (278, '3'): 649,
  (278, '4'): 652,
  (278, '5'): 651,
  (278, '6'): 654,
  (278, '7'): 653,
  (278, '8'): 656,
  (278, '9'): 655,
  (278, 'A'): 657,
  (278, 'B'): 659,
  (278, 'C'): 658,
  (278, 'D'): 661,
  (278, 'E'): 660,
  (278, 'F'): 662,
  (278, 'a'): 663,
  (278, 'b'): 665,
  (278, 'c'): 664,
  (278, 'd'): 667,
  (278, 'e'): 666,
  (278, 'f'): 668,
  (279, '0'): 626,
  (279, '1'): 625,
  (279, '2'): 628,
  (279, '3'): 627,
  (279, '4'): 630,
  (279, '5'): 629,
  (279, '6'): 632,
  (279, '7'): 631,
  (279, '8'): 634,
  (279, '9'): 633,
  (279, 'A'): 635,
  (279, 'B'): 637,
  (279, 'C'): 636,
  (279, 'D'): 639,
  (279, 'E'): 638,
  (279, 'F'): 640,
  (279, 'a'): 641,
  (279, 'b'): 643,
  (279, 'c'): 642,
  (279, 'd'): 645,
  (279, 'e'): 644,
  (279, 'f'): 646,
  (280, '0'): 604,
  (280, '1'): 603,
  (280, '2'): 606,
  (280, '3'): 605,
  (280, '4'): 608,
  (280, '5'): 607,
  (280, '6'): 610,
  (280, '7'): 609,
  (280, '8'): 612,
  (280, '9'): 611,
  (280, 'A'): 613,
  (280, 'B'): 615,
  (280, 'C'): 614,
  (280, 'D'): 617,
  (280, 'E'): 616,
  (280, 'F'): 618,
  (280, 'a'): 619,
  (280, 'b'): 621,
  (280, 'c'): 620,
  (280, 'd'): 623,
  (280, 'e'): 622,
  (280, 'f'): 624,
  (281, '0'): 582,
  (281, '1'): 581,
  (281, '2'): 584,
  (281, '3'): 583,
  (281, '4'): 586,
  (281, '5'): 585,
  (281, '6'): 588,
  (281, '7'): 587,
  (281, '8'): 590,
  (281, '9'): 589,
  (281, 'A'): 591,
  (281, 'B'): 593,
  (281, 'C'): 592,
  (281, 'D'): 595,
  (281, 'E'): 594,
  (281, 'F'): 596,
  (281, 'a'): 597,
  (281, 'b'): 599,
  (281, 'c'): 598,
  (281, 'd'): 601,
  (281, 'e'): 600,
  (281, 'f'): 602,
  (282, '0'): 560,
  (282, '1'): 559,
  (282, '2'): 562,
  (282, '3'): 561,
  (282, '4'): 564,
  (282, '5'): 563,
  (282, '6'): 566,
  (282, '7'): 565,
  (282, '8'): 568,
  (282, '9'): 567,
  (282, 'A'): 569,
  (282, 'B'): 571,
  (282, 'C'): 570,
  (282, 'D'): 573,
  (282, 'E'): 572,
  (282, 'F'): 574,
  (282, 'a'): 575,
  (282, 'b'): 577,
  (282, 'c'): 576,
  (282, 'd'): 579,
  (282, 'e'): 578,
  (282, 'f'): 580,
  (283, '0'): 538,
  (283, '1'): 537,
  (283, '2'): 540,
  (283, '3'): 539,
  (283, '4'): 542,
  (283, '5'): 541,
  (283, '6'): 544,
  (283, '7'): 543,
  (283, '8'): 546,
  (283, '9'): 545,
  (283, 'A'): 547,
  (283, 'B'): 549,
  (283, 'C'): 548,
  (283, 'D'): 551,
  (283, 'E'): 550,
  (283, 'F'): 552,
  (283, 'a'): 553,
  (283, 'b'): 555,
  (283, 'c'): 554,
  (283, 'd'): 557,
  (283, 'e'): 556,
  (283, 'f'): 558,
  (284, '0'): 516,
  (284, '1'): 515,
  (284, '2'): 518,
  (284, '3'): 517,
  (284, '4'): 520,
  (284, '5'): 519,
  (284, '6'): 522,
  (284, '7'): 521,
  (284, '8'): 524,
  (284, '9'): 523,
  (284, 'A'): 525,
  (284, 'B'): 527,
  (284, 'C'): 526,
  (284, 'D'): 529,
  (284, 'E'): 528,
  (284, 'F'): 530,
  (284, 'a'): 531,
  (284, 'b'): 533,
  (284, 'c'): 532,
  (284, 'd'): 535,
  (284, 'e'): 534,
  (284, 'f'): 536,
  (285, '0'): 494,
  (285, '1'): 493,
  (285, '2'): 496,
  (285, '3'): 495,
  (285, '4'): 498,
  (285, '5'): 497,
  (285, '6'): 500,
  (285, '7'): 499,
  (285, '8'): 502,
  (285, '9'): 501,
  (285, 'A'): 503,
  (285, 'B'): 505,
  (285, 'C'): 504,
  (285, 'D'): 507,
  (285, 'E'): 506,
  (285, 'F'): 508,
  (285, 'a'): 509,
  (285, 'b'): 511,
  (285, 'c'): 510,
  (285, 'd'): 513,
  (285, 'e'): 512,
  (285, 'f'): 514,
  (286, '0'): 472,
  (286, '1'): 471,
  (286, '2'): 474,
  (286, '3'): 473,
  (286, '4'): 476,
  (286, '5'): 475,
  (286, '6'): 478,
  (286, '7'): 477,
  (286, '8'): 480,
  (286, '9'): 479,
  (286, 'A'): 481,
  (286, 'B'): 483,
  (286, 'C'): 482,
  (286, 'D'): 485,
  (286, 'E'): 484,
  (286, 'F'): 486,
  (286, 'a'): 487,
  (286, 'b'): 489,
  (286, 'c'): 488,
  (286, 'd'): 491,
  (286, 'e'): 490,
  (286, 'f'): 492,
  (287, '0'): 450,
  (287, '1'): 449,
  (287, '2'): 452,
  (287, '3'): 451,
  (287, '4'): 454,
  (287, '5'): 453,
  (287, '6'): 456,
  (287, '7'): 455,
  (287, '8'): 458,
  (287, '9'): 457,
  (287, 'A'): 459,
  (287, 'B'): 461,
  (287, 'C'): 460,
  (287, 'D'): 463,
  (287, 'E'): 462,
  (287, 'F'): 464,
  (287, 'a'): 465,
  (287, 'b'): 467,
  (287, 'c'): 466,
  (287, 'd'): 469,
  (287, 'e'): 468,
  (287, 'f'): 470,
  (288, '0'): 428,
  (288, '1'): 427,
  (288, '2'): 430,
  (288, '3'): 429,
  (288, '4'): 432,
  (288, '5'): 431,
  (288, '6'): 434,
  (288, '7'): 433,
  (288, '8'): 436,
  (288, '9'): 435,
  (288, 'A'): 437,
  (288, 'B'): 439,
  (288, 'C'): 438,
  (288, 'D'): 441,
  (288, 'E'): 440,
  (288, 'F'): 442,
  (288, 'a'): 443,
  (288, 'b'): 445,
  (288, 'c'): 444,
  (288, 'd'): 447,
  (288, 'e'): 446,
  (288, 'f'): 448,
  (289, '0'): 406,
  (289, '1'): 405,
  (289, '2'): 408,
  (289, '3'): 407,
  (289, '4'): 410,
  (289, '5'): 409,
  (289, '6'): 412,
  (289, '7'): 411,
  (289, '8'): 414,
  (289, '9'): 413,
  (289, 'A'): 415,
  (289, 'B'): 417,
  (289, 'C'): 416,
  (289, 'D'): 419,
  (289, 'E'): 418,
  (289, 'F'): 420,
  (289, 'a'): 421,
  (289, 'b'): 423,
  (289, 'c'): 422,
  (289, 'd'): 425,
  (289, 'e'): 424,
  (289, 'f'): 426,
  (290, '0'): 384,
  (290, '1'): 383,
  (290, '2'): 386,
  (290, '3'): 385,
  (290, '4'): 388,
  (290, '5'): 387,
  (290, '6'): 390,
  (290, '7'): 389,
  (290, '8'): 392,
  (290, '9'): 391,
  (290, 'A'): 393,
  (290, 'B'): 395,
  (290, 'C'): 394,
  (290, 'D'): 397,
  (290, 'E'): 396,
  (290, 'F'): 398,
  (290, 'a'): 399,
  (290, 'b'): 401,
  (290, 'c'): 400,
  (290, 'd'): 403,
  (290, 'e'): 402,
  (290, 'f'): 404,
  (291, '0'): 362,
  (291, '1'): 361,
  (291, '2'): 364,
  (291, '3'): 363,
  (291, '4'): 366,
  (291, '5'): 365,
  (291, '6'): 368,
  (291, '7'): 367,
  (291, '8'): 370,
  (291, '9'): 369,
  (291, 'A'): 371,
  (291, 'B'): 373,
  (291, 'C'): 372,
  (291, 'D'): 375,
  (291, 'E'): 374,
  (291, 'F'): 376,
  (291, 'a'): 377,
  (291, 'b'): 379,
  (291, 'c'): 378,
  (291, 'd'): 381,
  (291, 'e'): 380,
  (291, 'f'): 382,
  (292, '0'): 340,
  (292, '1'): 339,
  (292, '2'): 342,
  (292, '3'): 341,
  (292, '4'): 344,
  (292, '5'): 343,
  (292, '6'): 346,
  (292, '7'): 345,
  (292, '8'): 348,
  (292, '9'): 347,
  (292, 'A'): 349,
  (292, 'B'): 351,
  (292, 'C'): 350,
  (292, 'D'): 353,
  (292, 'E'): 352,
  (292, 'F'): 354,
  (292, 'a'): 355,
  (292, 'b'): 357,
  (292, 'c'): 356,
  (292, 'd'): 359,
  (292, 'e'): 358,
  (292, 'f'): 360,
  (293, '0'): 318,
  (293, '1'): 317,
  (293, '2'): 320,
  (293, '3'): 319,
  (293, '4'): 322,
  (293, '5'): 321,
  (293, '6'): 324,
  (293, '7'): 323,
  (293, '8'): 326,
  (293, '9'): 325,
  (293, 'A'): 327,
  (293, 'B'): 329,
  (293, 'C'): 328,
  (293, 'D'): 331,
  (293, 'E'): 330,
  (293, 'F'): 332,
  (293, 'a'): 333,
  (293, 'b'): 335,
  (293, 'c'): 334,
  (293, 'd'): 337,
  (293, 'e'): 336,
  (293, 'f'): 338,
  (294, '0'): 296,
  (294, '1'): 295,
  (294, '2'): 298,
  (294, '3'): 297,
  (294, '4'): 300,
  (294, '5'): 299,
  (294, '6'): 302,
  (294, '7'): 301,
  (294, '8'): 304,
  (294, '9'): 303,
  (294, 'A'): 305,
  (294, 'B'): 307,
  (294, 'C'): 306,
  (294, 'D'): 309,
  (294, 'E'): 308,
  (294, 'F'): 310,
  (294, 'a'): 311,
  (294, 'b'): 313,
  (294, 'c'): 312,
  (294, 'd'): 315,
  (294, 'e'): 314,
  (294, 'f'): 316},
 set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778]),
 set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 482, 483, 484, 485, 486, 487, 488, 489, 490, 491, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519, 520, 521, 522, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564, 565, 566, 567, 568, 569, 570, 571, 572, 573, 574, 575, 576, 577, 578, 579, 580, 581, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595, 596, 597, 598, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610, 611, 612, 613, 614, 615, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625, 626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 699, 700, 701, 702, 703, 704, 705, 706, 707, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771, 772, 773, 774, 775, 776, 777, 778]),
 ['0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, start|, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0',
  'CHAR',
  '(',
  ',',
  'CHAR',
  '|',
  '+',
  '?',
  '[',
  '{',
  '*',
  '.',
  '^',
  ')',
  '-',
  ']',
  '}',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  '2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
  'QUOTEDCHAR',
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
  'QUOTEDCHAR']), {})
# generated code between this line and its other occurence

if __name__ == '__main__':
    f = py.magic.autopath()
    oldcontent = f.read()
    s = "# GENERATED CODE BETWEEN THIS LINE AND ITS OTHER OCCURENCE\n".lower()
    pre, gen, after = oldcontent.split(s)

    parser, lexer = make_regex_parser()
    newcontent = "%s%sparser = %r\n%s\n%s%s" % (
            pre, s, parser, lexer.get_dummy_repr(), s, after)
    print newcontent
    f.write(newcontent)
