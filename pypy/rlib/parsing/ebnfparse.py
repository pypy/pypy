import py
from pypy.rlib.parsing.parsing import PackratParser, Rule
from pypy.rlib.parsing.tree import Nonterminal, Symbol, RPythonVisitor
from pypy.rlib.parsing.regexparse import parse_regex
import string
from pypy.rlib.parsing.regex import *
from pypy.rlib.parsing.deterministic import DFA
from pypy.rlib.parsing.lexer import Lexer, DummyLexer

def make_ebnf_parser():
    NONTERMINALNAME = parse_regex("([a-z]|_)[a-z0-9_]*")
    SYMBOLNAME = parse_regex("_*[A-Z]([A-Z]|_)*")
    LONGQUOTED = parse_regex(r'"[^\"]*(\\\"?[^\"]+)*(\\\")?"')
    QUOTEDQUOTE = parse_regex("""'"'""")
    COMMENT = parse_regex("#[^\\n]*\\n")
    names1 = ['SYMBOLNAME', 'NONTERMINALNAME', 'QUOTE', 'QUOTE', 'IGNORE',
              'IGNORE', 'IGNORE', 'IGNORE']
    regexs1 = [SYMBOLNAME, NONTERMINALNAME, LONGQUOTED, QUOTEDQUOTE, COMMENT,
               StringExpression('\n'), StringExpression(' '),
               StringExpression('\t')]
    rs, rules, transformer = parse_ebnf(r"""
    file: list EOF;
    list: element*;
    element: regex | production;
    regex: SYMBOLNAME ":" QUOTE ";";
    production: NONTERMINALNAME ":" body ";";
    body: expansion "|" body | expansion;
    expansion: enclosed expansion | enclosed;
    enclosed: "[" primary "]" |
              "<" primary ">" |
              primary_parens "*" |
              primary;
    primary_parens: "(" expansion ")" | primary;
    primary: NONTERMINALNAME | SYMBOLNAME | QUOTE;
    """)
    names2, regexs2 = zip(*rs)
    lexer = Lexer(regexs1 + list(regexs2), names1 + list(names2),
                  ignore=['IGNORE'])
    parser = PackratParser(rules, "file")
    transformer
    return parser, lexer, transformer

def parse_ebnf(s):
    visitor = ParserBuilder()
    tokens = lexer.tokenize(s, True)
    print tokens
    s = parser.parse(tokens)
    s = s.visit(EBNFToAST())
    s.visit(visitor)
    visitor.fix_rule_order()
    ToAstVisitor = make_transformer(visitor.rules, visitor.changes,
                                    visitor.star_rules)
    return zip(visitor.names, visitor.regexs), visitor.rules, ToAstVisitor

def make_parse_function(regexs, rules, eof=False):
    from pypy.rlib.parsing.lexer import Lexer
    names, regexs = zip(*regexs)
    if "IGNORE" in names:
        ignore = ["IGNORE"]
    else:
        ignore = []
    lexer = Lexer(list(regexs), list(names), ignore=ignore)
    parser = PackratParser(rules, rules[0].nonterminal)
    def parse(s):
        tokens = lexer.tokenize(s, eof=eof)
        s = parser.parse(tokens)
        return s
    return parse

class ParserBuilder(object):
    def __init__(self):
        self.regexs = []
        self.names = []
        self.rules = []
        self.changes = []
        self.star_rules = {}
        self.first_rule = None
    def visit_file(self, node):
        return node.children[0].visit(self)
    def visit_list(self, node):
        for child in node.children[0].children:
            child.visit(self)
    def visit_element(self, node):
        node.children[0].visit(self)
    def visit_regex(self, node):
        regextext = node.children[2].additional_info[1:-1].replace('\\"', '"')
        regex = parse_regex(regextext)
        if regex is None:
            raise ValueError(
                "%s is not a valid regular expression" % regextext)
        self.regexs.append(regex)
        self.names.append(node.children[0].additional_info)
    def visit_production(self, node):
        self.conditions = []
        self.returnvals = []
        name = node.children[0].additional_info
        expansions, changes = node.children[2].visit(self)
        self.rules.append(Rule(name, expansions))
        if self.first_rule is None:
            self.first_rule = name
        self.changes.append(changes)
    def visit_body(self, node):
        if len(node.children) == 1:
            expansion, changes = node.children[0].visit(self)
            return [expansion], [changes]
        expansion, change = node.children[0].visit(self)
        expansions, changes = node.children[2].visit(self)
        expansions.insert(0, expansion)
        changes.insert(0, change)
        return expansions, changes
    def visit_expansion(self, node):
        if len(node.children) == 1:
            return node.children[0].visit(self)
        expansion1, changes1 = node.children[0].visit(self)
        expansion2, changes2 = node.children[1].visit(self)
        return expansion1 + expansion2, changes1 + changes2
    def visit_enclosed(self, node):
        if len(node.children) == 1:
            return node.children[0].visit(self), " "
        elif len(node.children) == 3:
            return (node.children[1].visit(self),
                    node.children[0].additional_info)
        elif len(node.children) == 2:
            # XXX
            expansions, changes = node.children[0].visit(self)
            name = "_star_symbol%s" % (len(self.star_rules), )
            self.rules.append(Rule(name, [expansions + [name], []]))
            self.changes.append([changes + " ", changes])
            self.star_rules[name] = self.rules[-1]
            return [name], " "
    def visit_primary_parens(self, node):
        if len(node.children) == 1:
            return node.children[0].visit(self), " "
        else:
            return node.children[1].visit(self)
    def visit_primary(self, node):
        if len(node.children) == 3:
            return node.children[1].visit(self)
        elif node.children[0].symbol == "QUOTE":
            # harmless, since the string starts and ends with quotes
            content = node.children[0].additional_info[1:-1]
            if content.endswith("'"):
                e = '"""' + content + '"""'
            else:
                e = "'''" + content + "'''"
            name = eval(e)
            self.names.insert(0, name)
            self.regexs.insert(0, StringExpression(name))
            return [name]
        else:
            return [node.children[0].additional_info]
    def fix_rule_order(self):
        if self.rules[0].nonterminal != self.first_rule:
            i = [r.nonterminal for r in self.rules].index(self.first_rule)
            self.rules[i], self.rules[0] = self.rules[0], self.rules[i]
            self.changes[i], self.changes[0] = self.changes[0], self.changes[i]

def make_transformer(rules, changes, star_rules):
    rulenames = dict.fromkeys([r.nonterminal for r in rules])
    result = ["class ToAST(RPythonVisitor):"]
    result.append("    def general_visit(self, node):")
    result.append("        return node")
    for rule, change in zip(rules, changes):
        lenchanges = [len(c) for c in change]
        result.append("    def visit_%s(self, node):" % (rule.nonterminal, ))
        if rule.nonterminal in star_rules:
            subchange = change[0]
            expansion = rule.expansions[0]
            result.append("        children = []")
            result.append("        while len(node.children) == %s:" % (
                          len(expansion), ))
            children = []
            for i, (n, c) in enumerate(zip(expansion[:-1], subchange[:-1])):
                if c == " ":
                    children.append("self.dispatch(node.children[%s])" % (i, ))
            result.append(
                "            children.extend([%s])" % (
                (",\n" + " " * 45).join(children)))
            result.append("            node = node.children[-1]")
            result.append(
                "        children.extend([%s])" % (
                (",\n" + " " * 45).join(children)))
            result.append("        return Nonterminal('__list', children)")
            continue
        for j, (expansion, subchange) in enumerate(
            zip(rule.expansions, change)):
            if len(rule.expansions) == 1:
                result.append("        if True:")
            elif j == len(rule.expansions) - 1:
                result.append("        else:")
            elif lenchanges.count(len(expansion)) == 1:
                result.append("        if len(node.children) == %s:" %
                   (len(expansion), ))
            else:
                conds = ["len(node.children) == %s" % (len(expansion), )]
                for i, n in enumerate(expansion):
                    conds.append("node.children[%s].symbol == %r" % (i, n))
                result.append(
                    "        if (%s):" % (" and \n            ".join(conds), ))
            if "<" in subchange:
                i = subchange.index("<")
                assert subchange.count("<") == 1
                result.append("            return self.dispatch(node.children[%s])" % (i, ))
            else:
                children = []
                assert len(expansion) == len(subchange)
                for i, (n, c) in enumerate(zip(expansion, subchange)):
                    if c == " ":
                        children.append("self.dispatch(node.children[%s])" % (i, ))
                result.append(
                    "            return Nonterminal(node.symbol, [%s])" % (
                    (",\n" + " " * 45).join(children)))
        result.append("")
    return "\n".join(result)


# generated code between this line and its other occurence
class EBNFToAST(object):
    def visit_file(self, node):
        if True:
            return Nonterminal(node.symbol, [node.children[0].visit(self),
                                             node.children[1].visit(self)])

    def visit__star_symbol0(self, node):
        children = []
        while len(node.children) == 2:
            children.extend([node.children[0].visit(self)])
            node = node.children[-1]
        children.extend([node.children[0].visit(self)])
        return Nonterminal('__list', children)
    def visit_list(self, node):
        if True:
            return Nonterminal(node.symbol, [node.children[0].visit(self)])

    def visit_element(self, node):
        if (len(node.children) == 1 and 
            node.children[0].symbol == 'regex'):
            return Nonterminal(node.symbol, [node.children[0].visit(self)])
        else:
            return Nonterminal(node.symbol, [node.children[0].visit(self)])

    def visit_regex(self, node):
        if True:
            return Nonterminal(node.symbol, [node.children[0].visit(self),
                                             node.children[1].visit(self),
                                             node.children[2].visit(self),
                                             node.children[3].visit(self)])

    def visit_production(self, node):
        if True:
            return Nonterminal(node.symbol, [node.children[0].visit(self),
                                             node.children[1].visit(self),
                                             node.children[2].visit(self),
                                             node.children[3].visit(self)])

    def visit_body(self, node):
        if len(node.children) == 3:
            return Nonterminal(node.symbol, [node.children[0].visit(self),
                                             node.children[1].visit(self),
                                             node.children[2].visit(self)])
        else:
            return Nonterminal(node.symbol, [node.children[0].visit(self)])

    def visit_expansion(self, node):
        if len(node.children) == 2:
            return Nonterminal(node.symbol, [node.children[0].visit(self),
                                             node.children[1].visit(self)])
        else:
            return Nonterminal(node.symbol, [node.children[0].visit(self)])

    def visit_enclosed(self, node):
        if (len(node.children) == 3 and 
            node.children[0].symbol == '[' and 
            node.children[1].symbol == 'primary' and 
            node.children[2].symbol == ']'):
            return Nonterminal(node.symbol, [node.children[0].visit(self),
                                             node.children[1].visit(self),
                                             node.children[2].visit(self)])
        if (len(node.children) == 3 and 
            node.children[0].symbol == '<' and 
            node.children[1].symbol == 'primary' and 
            node.children[2].symbol == '>'):
            return Nonterminal(node.symbol, [node.children[0].visit(self),
                                             node.children[1].visit(self),
                                             node.children[2].visit(self)])
        if len(node.children) == 2:
            return Nonterminal(node.symbol, [node.children[0].visit(self),
                                             node.children[1].visit(self)])
        else:
            return Nonterminal(node.symbol, [node.children[0].visit(self)])

    def visit_primary_parens(self, node):
        if len(node.children) == 3:
            return Nonterminal(node.symbol, [node.children[0].visit(self),
                                             node.children[1].visit(self),
                                             node.children[2].visit(self)])
        else:
            return Nonterminal(node.symbol, [node.children[0].visit(self)])

    def visit_primary(self, node):
        if (len(node.children) == 1 and 
            node.children[0].symbol == 'NONTERMINALNAME'):
            return Nonterminal(node.symbol, [node.children[0].visit(self)])
        if (len(node.children) == 1 and 
            node.children[0].symbol == 'SYMBOLNAME'):
            return Nonterminal(node.symbol, [node.children[0].visit(self)])
        else:
            return Nonterminal(node.symbol, [node.children[0].visit(self)])

parser = PackratParser([Rule('file', [['list', 'EOF']]),
  Rule('_star_symbol0', [['element', '_star_symbol0'], ['element']]),
  Rule('list', [['_star_symbol0']]),
  Rule('element', [['regex'], ['production']]),
  Rule('regex', [['SYMBOLNAME', ':', 'QUOTE', ';']]),
  Rule('production', [['NONTERMINALNAME', ':', 'body', ';']]),
  Rule('body', [['expansion', '|', 'body'], ['expansion']]),
  Rule('expansion', [['enclosed', 'expansion'], ['enclosed']]),
  Rule('enclosed', [['[', 'primary', ']'], ['<', 'primary', '>'], ['primary_parens', '*'], ['primary']]),
  Rule('primary_parens', [['(', 'expansion', ')'], ['primary']]),
  Rule('primary', [['NONTERMINALNAME'], ['SYMBOLNAME'], ['QUOTE']])],
 'file')
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
            if char == '\t':
                state = 1
            elif char == '\n':
                state = 2
            elif 'A' <= char <= 'Z':
                state = 3
            elif char == ' ':
                state = 4
            elif char == '#':
                state = 5
            elif char == '"':
                state = 6
            elif char == "'":
                state = 7
            elif char == ')':
                state = 8
            elif char == '(':
                state = 9
            elif char == '*':
                state = 10
            elif char == ';':
                state = 11
            elif char == ':':
                state = 12
            elif char == '<':
                state = 13
            elif char == '>':
                state = 14
            elif char == '[':
                state = 15
            elif char == ']':
                state = 16
            elif char == '_':
                state = 17
            elif 'a' <= char <= 'z':
                state = 18
            elif char == '|':
                state = 19
            else:
                break
        if state == 3:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 3
                return i
            if 'A' <= char <= 'Z':
                state = 3
                continue
            elif char == '_':
                state = 3
                continue
            else:
                break
        if state == 5:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 5
                return ~i
            if char == '\n':
                state = 25
            elif '\x00' <= char <= '\t':
                state = 5
                continue
            elif '\x0b' <= char <= '\xff':
                state = 5
                continue
            else:
                break
        if state == 6:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 6
                return ~i
            if char == '\\':
                state = 22
            elif '\x00' <= char <= '!':
                state = 6
                continue
            elif '#' <= char <= '[':
                state = 6
                continue
            elif ']' <= char <= '\xff':
                state = 6
                continue
            elif char == '"':
                state = 23
            else:
                break
        if state == 7:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 7
                return ~i
            if char == '"':
                state = 20
            else:
                break
        if state == 17:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 17
                return i
            if char == '_':
                state = 17
                continue
            elif '0' <= char <= '9':
                state = 18
            elif 'a' <= char <= 'z':
                state = 18
            elif 'A' <= char <= 'Z':
                state = 3
                continue
            else:
                break
        if state == 18:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 18
                return i
            if '0' <= char <= '9':
                state = 18
                continue
            elif char == '_':
                state = 18
                continue
            elif 'a' <= char <= 'z':
                state = 18
                continue
            else:
                break
        if state == 20:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 20
                return ~i
            if char == "'":
                state = 21
            else:
                break
        if state == 22:
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 22
                return ~i
            if char == '"':
                state = 24
            elif char == '\\':
                state = 22
                continue
            elif '\x00' <= char <= '!':
                state = 6
                continue
            elif '#' <= char <= '[':
                state = 6
                continue
            elif ']' <= char <= '\xff':
                state = 6
                continue
            else:
                break
        if state == 24:
            runner.last_matched_index = i - 1
            runner.last_matched_state = state
            if i < len(input):
                char = input[i]
                i += 1
            else:
                runner.state = 24
                return i
            if '\x00' <= char <= '!':
                state = 6
                continue
            elif '#' <= char <= '\xff':
                state = 6
                continue
            elif char == '"':
                state = 23
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
lexer = DummyLexer(recognize, DFA(26,
 {(0, '\t'): 1,
  (0, '\n'): 2,
  (0, ' '): 4,
  (0, '"'): 6,
  (0, '#'): 5,
  (0, "'"): 7,
  (0, '('): 9,
  (0, ')'): 8,
  (0, '*'): 10,
  (0, ':'): 12,
  (0, ';'): 11,
  (0, '<'): 13,
  (0, '>'): 14,
  (0, 'A'): 3,
  (0, 'B'): 3,
  (0, 'C'): 3,
  (0, 'D'): 3,
  (0, 'E'): 3,
  (0, 'F'): 3,
  (0, 'G'): 3,
  (0, 'H'): 3,
  (0, 'I'): 3,
  (0, 'J'): 3,
  (0, 'K'): 3,
  (0, 'L'): 3,
  (0, 'M'): 3,
  (0, 'N'): 3,
  (0, 'O'): 3,
  (0, 'P'): 3,
  (0, 'Q'): 3,
  (0, 'R'): 3,
  (0, 'S'): 3,
  (0, 'T'): 3,
  (0, 'U'): 3,
  (0, 'V'): 3,
  (0, 'W'): 3,
  (0, 'X'): 3,
  (0, 'Y'): 3,
  (0, 'Z'): 3,
  (0, '['): 15,
  (0, ']'): 16,
  (0, '_'): 17,
  (0, 'a'): 18,
  (0, 'b'): 18,
  (0, 'c'): 18,
  (0, 'd'): 18,
  (0, 'e'): 18,
  (0, 'f'): 18,
  (0, 'g'): 18,
  (0, 'h'): 18,
  (0, 'i'): 18,
  (0, 'j'): 18,
  (0, 'k'): 18,
  (0, 'l'): 18,
  (0, 'm'): 18,
  (0, 'n'): 18,
  (0, 'o'): 18,
  (0, 'p'): 18,
  (0, 'q'): 18,
  (0, 'r'): 18,
  (0, 's'): 18,
  (0, 't'): 18,
  (0, 'u'): 18,
  (0, 'v'): 18,
  (0, 'w'): 18,
  (0, 'x'): 18,
  (0, 'y'): 18,
  (0, 'z'): 18,
  (0, '|'): 19,
  (3, 'A'): 3,
  (3, 'B'): 3,
  (3, 'C'): 3,
  (3, 'D'): 3,
  (3, 'E'): 3,
  (3, 'F'): 3,
  (3, 'G'): 3,
  (3, 'H'): 3,
  (3, 'I'): 3,
  (3, 'J'): 3,
  (3, 'K'): 3,
  (3, 'L'): 3,
  (3, 'M'): 3,
  (3, 'N'): 3,
  (3, 'O'): 3,
  (3, 'P'): 3,
  (3, 'Q'): 3,
  (3, 'R'): 3,
  (3, 'S'): 3,
  (3, 'T'): 3,
  (3, 'U'): 3,
  (3, 'V'): 3,
  (3, 'W'): 3,
  (3, 'X'): 3,
  (3, 'Y'): 3,
  (3, 'Z'): 3,
  (3, '_'): 3,
  (5, '\x00'): 5,
  (5, '\x01'): 5,
  (5, '\x02'): 5,
  (5, '\x03'): 5,
  (5, '\x04'): 5,
  (5, '\x05'): 5,
  (5, '\x06'): 5,
  (5, '\x07'): 5,
  (5, '\x08'): 5,
  (5, '\t'): 5,
  (5, '\n'): 25,
  (5, '\x0b'): 5,
  (5, '\x0c'): 5,
  (5, '\r'): 5,
  (5, '\x0e'): 5,
  (5, '\x0f'): 5,
  (5, '\x10'): 5,
  (5, '\x11'): 5,
  (5, '\x12'): 5,
  (5, '\x13'): 5,
  (5, '\x14'): 5,
  (5, '\x15'): 5,
  (5, '\x16'): 5,
  (5, '\x17'): 5,
  (5, '\x18'): 5,
  (5, '\x19'): 5,
  (5, '\x1a'): 5,
  (5, '\x1b'): 5,
  (5, '\x1c'): 5,
  (5, '\x1d'): 5,
  (5, '\x1e'): 5,
  (5, '\x1f'): 5,
  (5, ' '): 5,
  (5, '!'): 5,
  (5, '"'): 5,
  (5, '#'): 5,
  (5, '$'): 5,
  (5, '%'): 5,
  (5, '&'): 5,
  (5, "'"): 5,
  (5, '('): 5,
  (5, ')'): 5,
  (5, '*'): 5,
  (5, '+'): 5,
  (5, ','): 5,
  (5, '-'): 5,
  (5, '.'): 5,
  (5, '/'): 5,
  (5, '0'): 5,
  (5, '1'): 5,
  (5, '2'): 5,
  (5, '3'): 5,
  (5, '4'): 5,
  (5, '5'): 5,
  (5, '6'): 5,
  (5, '7'): 5,
  (5, '8'): 5,
  (5, '9'): 5,
  (5, ':'): 5,
  (5, ';'): 5,
  (5, '<'): 5,
  (5, '='): 5,
  (5, '>'): 5,
  (5, '?'): 5,
  (5, '@'): 5,
  (5, 'A'): 5,
  (5, 'B'): 5,
  (5, 'C'): 5,
  (5, 'D'): 5,
  (5, 'E'): 5,
  (5, 'F'): 5,
  (5, 'G'): 5,
  (5, 'H'): 5,
  (5, 'I'): 5,
  (5, 'J'): 5,
  (5, 'K'): 5,
  (5, 'L'): 5,
  (5, 'M'): 5,
  (5, 'N'): 5,
  (5, 'O'): 5,
  (5, 'P'): 5,
  (5, 'Q'): 5,
  (5, 'R'): 5,
  (5, 'S'): 5,
  (5, 'T'): 5,
  (5, 'U'): 5,
  (5, 'V'): 5,
  (5, 'W'): 5,
  (5, 'X'): 5,
  (5, 'Y'): 5,
  (5, 'Z'): 5,
  (5, '['): 5,
  (5, '\\'): 5,
  (5, ']'): 5,
  (5, '^'): 5,
  (5, '_'): 5,
  (5, '`'): 5,
  (5, 'a'): 5,
  (5, 'b'): 5,
  (5, 'c'): 5,
  (5, 'd'): 5,
  (5, 'e'): 5,
  (5, 'f'): 5,
  (5, 'g'): 5,
  (5, 'h'): 5,
  (5, 'i'): 5,
  (5, 'j'): 5,
  (5, 'k'): 5,
  (5, 'l'): 5,
  (5, 'm'): 5,
  (5, 'n'): 5,
  (5, 'o'): 5,
  (5, 'p'): 5,
  (5, 'q'): 5,
  (5, 'r'): 5,
  (5, 's'): 5,
  (5, 't'): 5,
  (5, 'u'): 5,
  (5, 'v'): 5,
  (5, 'w'): 5,
  (5, 'x'): 5,
  (5, 'y'): 5,
  (5, 'z'): 5,
  (5, '{'): 5,
  (5, '|'): 5,
  (5, '}'): 5,
  (5, '~'): 5,
  (5, '\x7f'): 5,
  (5, '\x80'): 5,
  (5, '\x81'): 5,
  (5, '\x82'): 5,
  (5, '\x83'): 5,
  (5, '\x84'): 5,
  (5, '\x85'): 5,
  (5, '\x86'): 5,
  (5, '\x87'): 5,
  (5, '\x88'): 5,
  (5, '\x89'): 5,
  (5, '\x8a'): 5,
  (5, '\x8b'): 5,
  (5, '\x8c'): 5,
  (5, '\x8d'): 5,
  (5, '\x8e'): 5,
  (5, '\x8f'): 5,
  (5, '\x90'): 5,
  (5, '\x91'): 5,
  (5, '\x92'): 5,
  (5, '\x93'): 5,
  (5, '\x94'): 5,
  (5, '\x95'): 5,
  (5, '\x96'): 5,
  (5, '\x97'): 5,
  (5, '\x98'): 5,
  (5, '\x99'): 5,
  (5, '\x9a'): 5,
  (5, '\x9b'): 5,
  (5, '\x9c'): 5,
  (5, '\x9d'): 5,
  (5, '\x9e'): 5,
  (5, '\x9f'): 5,
  (5, '\xa0'): 5,
  (5, '\xa1'): 5,
  (5, '\xa2'): 5,
  (5, '\xa3'): 5,
  (5, '\xa4'): 5,
  (5, '\xa5'): 5,
  (5, '\xa6'): 5,
  (5, '\xa7'): 5,
  (5, '\xa8'): 5,
  (5, '\xa9'): 5,
  (5, '\xaa'): 5,
  (5, '\xab'): 5,
  (5, '\xac'): 5,
  (5, '\xad'): 5,
  (5, '\xae'): 5,
  (5, '\xaf'): 5,
  (5, '\xb0'): 5,
  (5, '\xb1'): 5,
  (5, '\xb2'): 5,
  (5, '\xb3'): 5,
  (5, '\xb4'): 5,
  (5, '\xb5'): 5,
  (5, '\xb6'): 5,
  (5, '\xb7'): 5,
  (5, '\xb8'): 5,
  (5, '\xb9'): 5,
  (5, '\xba'): 5,
  (5, '\xbb'): 5,
  (5, '\xbc'): 5,
  (5, '\xbd'): 5,
  (5, '\xbe'): 5,
  (5, '\xbf'): 5,
  (5, '\xc0'): 5,
  (5, '\xc1'): 5,
  (5, '\xc2'): 5,
  (5, '\xc3'): 5,
  (5, '\xc4'): 5,
  (5, '\xc5'): 5,
  (5, '\xc6'): 5,
  (5, '\xc7'): 5,
  (5, '\xc8'): 5,
  (5, '\xc9'): 5,
  (5, '\xca'): 5,
  (5, '\xcb'): 5,
  (5, '\xcc'): 5,
  (5, '\xcd'): 5,
  (5, '\xce'): 5,
  (5, '\xcf'): 5,
  (5, '\xd0'): 5,
  (5, '\xd1'): 5,
  (5, '\xd2'): 5,
  (5, '\xd3'): 5,
  (5, '\xd4'): 5,
  (5, '\xd5'): 5,
  (5, '\xd6'): 5,
  (5, '\xd7'): 5,
  (5, '\xd8'): 5,
  (5, '\xd9'): 5,
  (5, '\xda'): 5,
  (5, '\xdb'): 5,
  (5, '\xdc'): 5,
  (5, '\xdd'): 5,
  (5, '\xde'): 5,
  (5, '\xdf'): 5,
  (5, '\xe0'): 5,
  (5, '\xe1'): 5,
  (5, '\xe2'): 5,
  (5, '\xe3'): 5,
  (5, '\xe4'): 5,
  (5, '\xe5'): 5,
  (5, '\xe6'): 5,
  (5, '\xe7'): 5,
  (5, '\xe8'): 5,
  (5, '\xe9'): 5,
  (5, '\xea'): 5,
  (5, '\xeb'): 5,
  (5, '\xec'): 5,
  (5, '\xed'): 5,
  (5, '\xee'): 5,
  (5, '\xef'): 5,
  (5, '\xf0'): 5,
  (5, '\xf1'): 5,
  (5, '\xf2'): 5,
  (5, '\xf3'): 5,
  (5, '\xf4'): 5,
  (5, '\xf5'): 5,
  (5, '\xf6'): 5,
  (5, '\xf7'): 5,
  (5, '\xf8'): 5,
  (5, '\xf9'): 5,
  (5, '\xfa'): 5,
  (5, '\xfb'): 5,
  (5, '\xfc'): 5,
  (5, '\xfd'): 5,
  (5, '\xfe'): 5,
  (5, '\xff'): 5,
  (6, '\x00'): 6,
  (6, '\x01'): 6,
  (6, '\x02'): 6,
  (6, '\x03'): 6,
  (6, '\x04'): 6,
  (6, '\x05'): 6,
  (6, '\x06'): 6,
  (6, '\x07'): 6,
  (6, '\x08'): 6,
  (6, '\t'): 6,
  (6, '\n'): 6,
  (6, '\x0b'): 6,
  (6, '\x0c'): 6,
  (6, '\r'): 6,
  (6, '\x0e'): 6,
  (6, '\x0f'): 6,
  (6, '\x10'): 6,
  (6, '\x11'): 6,
  (6, '\x12'): 6,
  (6, '\x13'): 6,
  (6, '\x14'): 6,
  (6, '\x15'): 6,
  (6, '\x16'): 6,
  (6, '\x17'): 6,
  (6, '\x18'): 6,
  (6, '\x19'): 6,
  (6, '\x1a'): 6,
  (6, '\x1b'): 6,
  (6, '\x1c'): 6,
  (6, '\x1d'): 6,
  (6, '\x1e'): 6,
  (6, '\x1f'): 6,
  (6, ' '): 6,
  (6, '!'): 6,
  (6, '"'): 23,
  (6, '#'): 6,
  (6, '$'): 6,
  (6, '%'): 6,
  (6, '&'): 6,
  (6, "'"): 6,
  (6, '('): 6,
  (6, ')'): 6,
  (6, '*'): 6,
  (6, '+'): 6,
  (6, ','): 6,
  (6, '-'): 6,
  (6, '.'): 6,
  (6, '/'): 6,
  (6, '0'): 6,
  (6, '1'): 6,
  (6, '2'): 6,
  (6, '3'): 6,
  (6, '4'): 6,
  (6, '5'): 6,
  (6, '6'): 6,
  (6, '7'): 6,
  (6, '8'): 6,
  (6, '9'): 6,
  (6, ':'): 6,
  (6, ';'): 6,
  (6, '<'): 6,
  (6, '='): 6,
  (6, '>'): 6,
  (6, '?'): 6,
  (6, '@'): 6,
  (6, 'A'): 6,
  (6, 'B'): 6,
  (6, 'C'): 6,
  (6, 'D'): 6,
  (6, 'E'): 6,
  (6, 'F'): 6,
  (6, 'G'): 6,
  (6, 'H'): 6,
  (6, 'I'): 6,
  (6, 'J'): 6,
  (6, 'K'): 6,
  (6, 'L'): 6,
  (6, 'M'): 6,
  (6, 'N'): 6,
  (6, 'O'): 6,
  (6, 'P'): 6,
  (6, 'Q'): 6,
  (6, 'R'): 6,
  (6, 'S'): 6,
  (6, 'T'): 6,
  (6, 'U'): 6,
  (6, 'V'): 6,
  (6, 'W'): 6,
  (6, 'X'): 6,
  (6, 'Y'): 6,
  (6, 'Z'): 6,
  (6, '['): 6,
  (6, '\\'): 22,
  (6, ']'): 6,
  (6, '^'): 6,
  (6, '_'): 6,
  (6, '`'): 6,
  (6, 'a'): 6,
  (6, 'b'): 6,
  (6, 'c'): 6,
  (6, 'd'): 6,
  (6, 'e'): 6,
  (6, 'f'): 6,
  (6, 'g'): 6,
  (6, 'h'): 6,
  (6, 'i'): 6,
  (6, 'j'): 6,
  (6, 'k'): 6,
  (6, 'l'): 6,
  (6, 'm'): 6,
  (6, 'n'): 6,
  (6, 'o'): 6,
  (6, 'p'): 6,
  (6, 'q'): 6,
  (6, 'r'): 6,
  (6, 's'): 6,
  (6, 't'): 6,
  (6, 'u'): 6,
  (6, 'v'): 6,
  (6, 'w'): 6,
  (6, 'x'): 6,
  (6, 'y'): 6,
  (6, 'z'): 6,
  (6, '{'): 6,
  (6, '|'): 6,
  (6, '}'): 6,
  (6, '~'): 6,
  (6, '\x7f'): 6,
  (6, '\x80'): 6,
  (6, '\x81'): 6,
  (6, '\x82'): 6,
  (6, '\x83'): 6,
  (6, '\x84'): 6,
  (6, '\x85'): 6,
  (6, '\x86'): 6,
  (6, '\x87'): 6,
  (6, '\x88'): 6,
  (6, '\x89'): 6,
  (6, '\x8a'): 6,
  (6, '\x8b'): 6,
  (6, '\x8c'): 6,
  (6, '\x8d'): 6,
  (6, '\x8e'): 6,
  (6, '\x8f'): 6,
  (6, '\x90'): 6,
  (6, '\x91'): 6,
  (6, '\x92'): 6,
  (6, '\x93'): 6,
  (6, '\x94'): 6,
  (6, '\x95'): 6,
  (6, '\x96'): 6,
  (6, '\x97'): 6,
  (6, '\x98'): 6,
  (6, '\x99'): 6,
  (6, '\x9a'): 6,
  (6, '\x9b'): 6,
  (6, '\x9c'): 6,
  (6, '\x9d'): 6,
  (6, '\x9e'): 6,
  (6, '\x9f'): 6,
  (6, '\xa0'): 6,
  (6, '\xa1'): 6,
  (6, '\xa2'): 6,
  (6, '\xa3'): 6,
  (6, '\xa4'): 6,
  (6, '\xa5'): 6,
  (6, '\xa6'): 6,
  (6, '\xa7'): 6,
  (6, '\xa8'): 6,
  (6, '\xa9'): 6,
  (6, '\xaa'): 6,
  (6, '\xab'): 6,
  (6, '\xac'): 6,
  (6, '\xad'): 6,
  (6, '\xae'): 6,
  (6, '\xaf'): 6,
  (6, '\xb0'): 6,
  (6, '\xb1'): 6,
  (6, '\xb2'): 6,
  (6, '\xb3'): 6,
  (6, '\xb4'): 6,
  (6, '\xb5'): 6,
  (6, '\xb6'): 6,
  (6, '\xb7'): 6,
  (6, '\xb8'): 6,
  (6, '\xb9'): 6,
  (6, '\xba'): 6,
  (6, '\xbb'): 6,
  (6, '\xbc'): 6,
  (6, '\xbd'): 6,
  (6, '\xbe'): 6,
  (6, '\xbf'): 6,
  (6, '\xc0'): 6,
  (6, '\xc1'): 6,
  (6, '\xc2'): 6,
  (6, '\xc3'): 6,
  (6, '\xc4'): 6,
  (6, '\xc5'): 6,
  (6, '\xc6'): 6,
  (6, '\xc7'): 6,
  (6, '\xc8'): 6,
  (6, '\xc9'): 6,
  (6, '\xca'): 6,
  (6, '\xcb'): 6,
  (6, '\xcc'): 6,
  (6, '\xcd'): 6,
  (6, '\xce'): 6,
  (6, '\xcf'): 6,
  (6, '\xd0'): 6,
  (6, '\xd1'): 6,
  (6, '\xd2'): 6,
  (6, '\xd3'): 6,
  (6, '\xd4'): 6,
  (6, '\xd5'): 6,
  (6, '\xd6'): 6,
  (6, '\xd7'): 6,
  (6, '\xd8'): 6,
  (6, '\xd9'): 6,
  (6, '\xda'): 6,
  (6, '\xdb'): 6,
  (6, '\xdc'): 6,
  (6, '\xdd'): 6,
  (6, '\xde'): 6,
  (6, '\xdf'): 6,
  (6, '\xe0'): 6,
  (6, '\xe1'): 6,
  (6, '\xe2'): 6,
  (6, '\xe3'): 6,
  (6, '\xe4'): 6,
  (6, '\xe5'): 6,
  (6, '\xe6'): 6,
  (6, '\xe7'): 6,
  (6, '\xe8'): 6,
  (6, '\xe9'): 6,
  (6, '\xea'): 6,
  (6, '\xeb'): 6,
  (6, '\xec'): 6,
  (6, '\xed'): 6,
  (6, '\xee'): 6,
  (6, '\xef'): 6,
  (6, '\xf0'): 6,
  (6, '\xf1'): 6,
  (6, '\xf2'): 6,
  (6, '\xf3'): 6,
  (6, '\xf4'): 6,
  (6, '\xf5'): 6,
  (6, '\xf6'): 6,
  (6, '\xf7'): 6,
  (6, '\xf8'): 6,
  (6, '\xf9'): 6,
  (6, '\xfa'): 6,
  (6, '\xfb'): 6,
  (6, '\xfc'): 6,
  (6, '\xfd'): 6,
  (6, '\xfe'): 6,
  (6, '\xff'): 6,
  (7, '"'): 20,
  (17, '0'): 18,
  (17, '1'): 18,
  (17, '2'): 18,
  (17, '3'): 18,
  (17, '4'): 18,
  (17, '5'): 18,
  (17, '6'): 18,
  (17, '7'): 18,
  (17, '8'): 18,
  (17, '9'): 18,
  (17, 'A'): 3,
  (17, 'B'): 3,
  (17, 'C'): 3,
  (17, 'D'): 3,
  (17, 'E'): 3,
  (17, 'F'): 3,
  (17, 'G'): 3,
  (17, 'H'): 3,
  (17, 'I'): 3,
  (17, 'J'): 3,
  (17, 'K'): 3,
  (17, 'L'): 3,
  (17, 'M'): 3,
  (17, 'N'): 3,
  (17, 'O'): 3,
  (17, 'P'): 3,
  (17, 'Q'): 3,
  (17, 'R'): 3,
  (17, 'S'): 3,
  (17, 'T'): 3,
  (17, 'U'): 3,
  (17, 'V'): 3,
  (17, 'W'): 3,
  (17, 'X'): 3,
  (17, 'Y'): 3,
  (17, 'Z'): 3,
  (17, '_'): 17,
  (17, 'a'): 18,
  (17, 'b'): 18,
  (17, 'c'): 18,
  (17, 'd'): 18,
  (17, 'e'): 18,
  (17, 'f'): 18,
  (17, 'g'): 18,
  (17, 'h'): 18,
  (17, 'i'): 18,
  (17, 'j'): 18,
  (17, 'k'): 18,
  (17, 'l'): 18,
  (17, 'm'): 18,
  (17, 'n'): 18,
  (17, 'o'): 18,
  (17, 'p'): 18,
  (17, 'q'): 18,
  (17, 'r'): 18,
  (17, 's'): 18,
  (17, 't'): 18,
  (17, 'u'): 18,
  (17, 'v'): 18,
  (17, 'w'): 18,
  (17, 'x'): 18,
  (17, 'y'): 18,
  (17, 'z'): 18,
  (18, '0'): 18,
  (18, '1'): 18,
  (18, '2'): 18,
  (18, '3'): 18,
  (18, '4'): 18,
  (18, '5'): 18,
  (18, '6'): 18,
  (18, '7'): 18,
  (18, '8'): 18,
  (18, '9'): 18,
  (18, '_'): 18,
  (18, 'a'): 18,
  (18, 'b'): 18,
  (18, 'c'): 18,
  (18, 'd'): 18,
  (18, 'e'): 18,
  (18, 'f'): 18,
  (18, 'g'): 18,
  (18, 'h'): 18,
  (18, 'i'): 18,
  (18, 'j'): 18,
  (18, 'k'): 18,
  (18, 'l'): 18,
  (18, 'm'): 18,
  (18, 'n'): 18,
  (18, 'o'): 18,
  (18, 'p'): 18,
  (18, 'q'): 18,
  (18, 'r'): 18,
  (18, 's'): 18,
  (18, 't'): 18,
  (18, 'u'): 18,
  (18, 'v'): 18,
  (18, 'w'): 18,
  (18, 'x'): 18,
  (18, 'y'): 18,
  (18, 'z'): 18,
  (20, "'"): 21,
  (22, '\x00'): 6,
  (22, '\x01'): 6,
  (22, '\x02'): 6,
  (22, '\x03'): 6,
  (22, '\x04'): 6,
  (22, '\x05'): 6,
  (22, '\x06'): 6,
  (22, '\x07'): 6,
  (22, '\x08'): 6,
  (22, '\t'): 6,
  (22, '\n'): 6,
  (22, '\x0b'): 6,
  (22, '\x0c'): 6,
  (22, '\r'): 6,
  (22, '\x0e'): 6,
  (22, '\x0f'): 6,
  (22, '\x10'): 6,
  (22, '\x11'): 6,
  (22, '\x12'): 6,
  (22, '\x13'): 6,
  (22, '\x14'): 6,
  (22, '\x15'): 6,
  (22, '\x16'): 6,
  (22, '\x17'): 6,
  (22, '\x18'): 6,
  (22, '\x19'): 6,
  (22, '\x1a'): 6,
  (22, '\x1b'): 6,
  (22, '\x1c'): 6,
  (22, '\x1d'): 6,
  (22, '\x1e'): 6,
  (22, '\x1f'): 6,
  (22, ' '): 6,
  (22, '!'): 6,
  (22, '"'): 24,
  (22, '#'): 6,
  (22, '$'): 6,
  (22, '%'): 6,
  (22, '&'): 6,
  (22, "'"): 6,
  (22, '('): 6,
  (22, ')'): 6,
  (22, '*'): 6,
  (22, '+'): 6,
  (22, ','): 6,
  (22, '-'): 6,
  (22, '.'): 6,
  (22, '/'): 6,
  (22, '0'): 6,
  (22, '1'): 6,
  (22, '2'): 6,
  (22, '3'): 6,
  (22, '4'): 6,
  (22, '5'): 6,
  (22, '6'): 6,
  (22, '7'): 6,
  (22, '8'): 6,
  (22, '9'): 6,
  (22, ':'): 6,
  (22, ';'): 6,
  (22, '<'): 6,
  (22, '='): 6,
  (22, '>'): 6,
  (22, '?'): 6,
  (22, '@'): 6,
  (22, 'A'): 6,
  (22, 'B'): 6,
  (22, 'C'): 6,
  (22, 'D'): 6,
  (22, 'E'): 6,
  (22, 'F'): 6,
  (22, 'G'): 6,
  (22, 'H'): 6,
  (22, 'I'): 6,
  (22, 'J'): 6,
  (22, 'K'): 6,
  (22, 'L'): 6,
  (22, 'M'): 6,
  (22, 'N'): 6,
  (22, 'O'): 6,
  (22, 'P'): 6,
  (22, 'Q'): 6,
  (22, 'R'): 6,
  (22, 'S'): 6,
  (22, 'T'): 6,
  (22, 'U'): 6,
  (22, 'V'): 6,
  (22, 'W'): 6,
  (22, 'X'): 6,
  (22, 'Y'): 6,
  (22, 'Z'): 6,
  (22, '['): 6,
  (22, '\\'): 22,
  (22, ']'): 6,
  (22, '^'): 6,
  (22, '_'): 6,
  (22, '`'): 6,
  (22, 'a'): 6,
  (22, 'b'): 6,
  (22, 'c'): 6,
  (22, 'd'): 6,
  (22, 'e'): 6,
  (22, 'f'): 6,
  (22, 'g'): 6,
  (22, 'h'): 6,
  (22, 'i'): 6,
  (22, 'j'): 6,
  (22, 'k'): 6,
  (22, 'l'): 6,
  (22, 'm'): 6,
  (22, 'n'): 6,
  (22, 'o'): 6,
  (22, 'p'): 6,
  (22, 'q'): 6,
  (22, 'r'): 6,
  (22, 's'): 6,
  (22, 't'): 6,
  (22, 'u'): 6,
  (22, 'v'): 6,
  (22, 'w'): 6,
  (22, 'x'): 6,
  (22, 'y'): 6,
  (22, 'z'): 6,
  (22, '{'): 6,
  (22, '|'): 6,
  (22, '}'): 6,
  (22, '~'): 6,
  (22, '\x7f'): 6,
  (22, '\x80'): 6,
  (22, '\x81'): 6,
  (22, '\x82'): 6,
  (22, '\x83'): 6,
  (22, '\x84'): 6,
  (22, '\x85'): 6,
  (22, '\x86'): 6,
  (22, '\x87'): 6,
  (22, '\x88'): 6,
  (22, '\x89'): 6,
  (22, '\x8a'): 6,
  (22, '\x8b'): 6,
  (22, '\x8c'): 6,
  (22, '\x8d'): 6,
  (22, '\x8e'): 6,
  (22, '\x8f'): 6,
  (22, '\x90'): 6,
  (22, '\x91'): 6,
  (22, '\x92'): 6,
  (22, '\x93'): 6,
  (22, '\x94'): 6,
  (22, '\x95'): 6,
  (22, '\x96'): 6,
  (22, '\x97'): 6,
  (22, '\x98'): 6,
  (22, '\x99'): 6,
  (22, '\x9a'): 6,
  (22, '\x9b'): 6,
  (22, '\x9c'): 6,
  (22, '\x9d'): 6,
  (22, '\x9e'): 6,
  (22, '\x9f'): 6,
  (22, '\xa0'): 6,
  (22, '\xa1'): 6,
  (22, '\xa2'): 6,
  (22, '\xa3'): 6,
  (22, '\xa4'): 6,
  (22, '\xa5'): 6,
  (22, '\xa6'): 6,
  (22, '\xa7'): 6,
  (22, '\xa8'): 6,
  (22, '\xa9'): 6,
  (22, '\xaa'): 6,
  (22, '\xab'): 6,
  (22, '\xac'): 6,
  (22, '\xad'): 6,
  (22, '\xae'): 6,
  (22, '\xaf'): 6,
  (22, '\xb0'): 6,
  (22, '\xb1'): 6,
  (22, '\xb2'): 6,
  (22, '\xb3'): 6,
  (22, '\xb4'): 6,
  (22, '\xb5'): 6,
  (22, '\xb6'): 6,
  (22, '\xb7'): 6,
  (22, '\xb8'): 6,
  (22, '\xb9'): 6,
  (22, '\xba'): 6,
  (22, '\xbb'): 6,
  (22, '\xbc'): 6,
  (22, '\xbd'): 6,
  (22, '\xbe'): 6,
  (22, '\xbf'): 6,
  (22, '\xc0'): 6,
  (22, '\xc1'): 6,
  (22, '\xc2'): 6,
  (22, '\xc3'): 6,
  (22, '\xc4'): 6,
  (22, '\xc5'): 6,
  (22, '\xc6'): 6,
  (22, '\xc7'): 6,
  (22, '\xc8'): 6,
  (22, '\xc9'): 6,
  (22, '\xca'): 6,
  (22, '\xcb'): 6,
  (22, '\xcc'): 6,
  (22, '\xcd'): 6,
  (22, '\xce'): 6,
  (22, '\xcf'): 6,
  (22, '\xd0'): 6,
  (22, '\xd1'): 6,
  (22, '\xd2'): 6,
  (22, '\xd3'): 6,
  (22, '\xd4'): 6,
  (22, '\xd5'): 6,
  (22, '\xd6'): 6,
  (22, '\xd7'): 6,
  (22, '\xd8'): 6,
  (22, '\xd9'): 6,
  (22, '\xda'): 6,
  (22, '\xdb'): 6,
  (22, '\xdc'): 6,
  (22, '\xdd'): 6,
  (22, '\xde'): 6,
  (22, '\xdf'): 6,
  (22, '\xe0'): 6,
  (22, '\xe1'): 6,
  (22, '\xe2'): 6,
  (22, '\xe3'): 6,
  (22, '\xe4'): 6,
  (22, '\xe5'): 6,
  (22, '\xe6'): 6,
  (22, '\xe7'): 6,
  (22, '\xe8'): 6,
  (22, '\xe9'): 6,
  (22, '\xea'): 6,
  (22, '\xeb'): 6,
  (22, '\xec'): 6,
  (22, '\xed'): 6,
  (22, '\xee'): 6,
  (22, '\xef'): 6,
  (22, '\xf0'): 6,
  (22, '\xf1'): 6,
  (22, '\xf2'): 6,
  (22, '\xf3'): 6,
  (22, '\xf4'): 6,
  (22, '\xf5'): 6,
  (22, '\xf6'): 6,
  (22, '\xf7'): 6,
  (22, '\xf8'): 6,
  (22, '\xf9'): 6,
  (22, '\xfa'): 6,
  (22, '\xfb'): 6,
  (22, '\xfc'): 6,
  (22, '\xfd'): 6,
  (22, '\xfe'): 6,
  (22, '\xff'): 6,
  (24, '\x00'): 6,
  (24, '\x01'): 6,
  (24, '\x02'): 6,
  (24, '\x03'): 6,
  (24, '\x04'): 6,
  (24, '\x05'): 6,
  (24, '\x06'): 6,
  (24, '\x07'): 6,
  (24, '\x08'): 6,
  (24, '\t'): 6,
  (24, '\n'): 6,
  (24, '\x0b'): 6,
  (24, '\x0c'): 6,
  (24, '\r'): 6,
  (24, '\x0e'): 6,
  (24, '\x0f'): 6,
  (24, '\x10'): 6,
  (24, '\x11'): 6,
  (24, '\x12'): 6,
  (24, '\x13'): 6,
  (24, '\x14'): 6,
  (24, '\x15'): 6,
  (24, '\x16'): 6,
  (24, '\x17'): 6,
  (24, '\x18'): 6,
  (24, '\x19'): 6,
  (24, '\x1a'): 6,
  (24, '\x1b'): 6,
  (24, '\x1c'): 6,
  (24, '\x1d'): 6,
  (24, '\x1e'): 6,
  (24, '\x1f'): 6,
  (24, ' '): 6,
  (24, '!'): 6,
  (24, '"'): 23,
  (24, '#'): 6,
  (24, '$'): 6,
  (24, '%'): 6,
  (24, '&'): 6,
  (24, "'"): 6,
  (24, '('): 6,
  (24, ')'): 6,
  (24, '*'): 6,
  (24, '+'): 6,
  (24, ','): 6,
  (24, '-'): 6,
  (24, '.'): 6,
  (24, '/'): 6,
  (24, '0'): 6,
  (24, '1'): 6,
  (24, '2'): 6,
  (24, '3'): 6,
  (24, '4'): 6,
  (24, '5'): 6,
  (24, '6'): 6,
  (24, '7'): 6,
  (24, '8'): 6,
  (24, '9'): 6,
  (24, ':'): 6,
  (24, ';'): 6,
  (24, '<'): 6,
  (24, '='): 6,
  (24, '>'): 6,
  (24, '?'): 6,
  (24, '@'): 6,
  (24, 'A'): 6,
  (24, 'B'): 6,
  (24, 'C'): 6,
  (24, 'D'): 6,
  (24, 'E'): 6,
  (24, 'F'): 6,
  (24, 'G'): 6,
  (24, 'H'): 6,
  (24, 'I'): 6,
  (24, 'J'): 6,
  (24, 'K'): 6,
  (24, 'L'): 6,
  (24, 'M'): 6,
  (24, 'N'): 6,
  (24, 'O'): 6,
  (24, 'P'): 6,
  (24, 'Q'): 6,
  (24, 'R'): 6,
  (24, 'S'): 6,
  (24, 'T'): 6,
  (24, 'U'): 6,
  (24, 'V'): 6,
  (24, 'W'): 6,
  (24, 'X'): 6,
  (24, 'Y'): 6,
  (24, 'Z'): 6,
  (24, '['): 6,
  (24, '\\'): 6,
  (24, ']'): 6,
  (24, '^'): 6,
  (24, '_'): 6,
  (24, '`'): 6,
  (24, 'a'): 6,
  (24, 'b'): 6,
  (24, 'c'): 6,
  (24, 'd'): 6,
  (24, 'e'): 6,
  (24, 'f'): 6,
  (24, 'g'): 6,
  (24, 'h'): 6,
  (24, 'i'): 6,
  (24, 'j'): 6,
  (24, 'k'): 6,
  (24, 'l'): 6,
  (24, 'm'): 6,
  (24, 'n'): 6,
  (24, 'o'): 6,
  (24, 'p'): 6,
  (24, 'q'): 6,
  (24, 'r'): 6,
  (24, 's'): 6,
  (24, 't'): 6,
  (24, 'u'): 6,
  (24, 'v'): 6,
  (24, 'w'): 6,
  (24, 'x'): 6,
  (24, 'y'): 6,
  (24, 'z'): 6,
  (24, '{'): 6,
  (24, '|'): 6,
  (24, '}'): 6,
  (24, '~'): 6,
  (24, '\x7f'): 6,
  (24, '\x80'): 6,
  (24, '\x81'): 6,
  (24, '\x82'): 6,
  (24, '\x83'): 6,
  (24, '\x84'): 6,
  (24, '\x85'): 6,
  (24, '\x86'): 6,
  (24, '\x87'): 6,
  (24, '\x88'): 6,
  (24, '\x89'): 6,
  (24, '\x8a'): 6,
  (24, '\x8b'): 6,
  (24, '\x8c'): 6,
  (24, '\x8d'): 6,
  (24, '\x8e'): 6,
  (24, '\x8f'): 6,
  (24, '\x90'): 6,
  (24, '\x91'): 6,
  (24, '\x92'): 6,
  (24, '\x93'): 6,
  (24, '\x94'): 6,
  (24, '\x95'): 6,
  (24, '\x96'): 6,
  (24, '\x97'): 6,
  (24, '\x98'): 6,
  (24, '\x99'): 6,
  (24, '\x9a'): 6,
  (24, '\x9b'): 6,
  (24, '\x9c'): 6,
  (24, '\x9d'): 6,
  (24, '\x9e'): 6,
  (24, '\x9f'): 6,
  (24, '\xa0'): 6,
  (24, '\xa1'): 6,
  (24, '\xa2'): 6,
  (24, '\xa3'): 6,
  (24, '\xa4'): 6,
  (24, '\xa5'): 6,
  (24, '\xa6'): 6,
  (24, '\xa7'): 6,
  (24, '\xa8'): 6,
  (24, '\xa9'): 6,
  (24, '\xaa'): 6,
  (24, '\xab'): 6,
  (24, '\xac'): 6,
  (24, '\xad'): 6,
  (24, '\xae'): 6,
  (24, '\xaf'): 6,
  (24, '\xb0'): 6,
  (24, '\xb1'): 6,
  (24, '\xb2'): 6,
  (24, '\xb3'): 6,
  (24, '\xb4'): 6,
  (24, '\xb5'): 6,
  (24, '\xb6'): 6,
  (24, '\xb7'): 6,
  (24, '\xb8'): 6,
  (24, '\xb9'): 6,
  (24, '\xba'): 6,
  (24, '\xbb'): 6,
  (24, '\xbc'): 6,
  (24, '\xbd'): 6,
  (24, '\xbe'): 6,
  (24, '\xbf'): 6,
  (24, '\xc0'): 6,
  (24, '\xc1'): 6,
  (24, '\xc2'): 6,
  (24, '\xc3'): 6,
  (24, '\xc4'): 6,
  (24, '\xc5'): 6,
  (24, '\xc6'): 6,
  (24, '\xc7'): 6,
  (24, '\xc8'): 6,
  (24, '\xc9'): 6,
  (24, '\xca'): 6,
  (24, '\xcb'): 6,
  (24, '\xcc'): 6,
  (24, '\xcd'): 6,
  (24, '\xce'): 6,
  (24, '\xcf'): 6,
  (24, '\xd0'): 6,
  (24, '\xd1'): 6,
  (24, '\xd2'): 6,
  (24, '\xd3'): 6,
  (24, '\xd4'): 6,
  (24, '\xd5'): 6,
  (24, '\xd6'): 6,
  (24, '\xd7'): 6,
  (24, '\xd8'): 6,
  (24, '\xd9'): 6,
  (24, '\xda'): 6,
  (24, '\xdb'): 6,
  (24, '\xdc'): 6,
  (24, '\xdd'): 6,
  (24, '\xde'): 6,
  (24, '\xdf'): 6,
  (24, '\xe0'): 6,
  (24, '\xe1'): 6,
  (24, '\xe2'): 6,
  (24, '\xe3'): 6,
  (24, '\xe4'): 6,
  (24, '\xe5'): 6,
  (24, '\xe6'): 6,
  (24, '\xe7'): 6,
  (24, '\xe8'): 6,
  (24, '\xe9'): 6,
  (24, '\xea'): 6,
  (24, '\xeb'): 6,
  (24, '\xec'): 6,
  (24, '\xed'): 6,
  (24, '\xee'): 6,
  (24, '\xef'): 6,
  (24, '\xf0'): 6,
  (24, '\xf1'): 6,
  (24, '\xf2'): 6,
  (24, '\xf3'): 6,
  (24, '\xf4'): 6,
  (24, '\xf5'): 6,
  (24, '\xf6'): 6,
  (24, '\xf7'): 6,
  (24, '\xf8'): 6,
  (24, '\xf9'): 6,
  (24, '\xfa'): 6,
  (24, '\xfb'): 6,
  (24, '\xfc'): 6,
  (24, '\xfd'): 6,
  (24, '\xfe'): 6,
  (24, '\xff'): 6},
 set([1, 2, 3, 4, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 23, 24, 25]),
 set([1, 2, 3, 4, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 23, 24, 25]),
 ['0, 0, 0, final*, start*, 0, 0, 1, final*, start*, 0, 0, 0, start|, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0',
  'IGNORE',
  'IGNORE',
  'SYMBOLNAME',
  'IGNORE',
  '1, 0, start|, 0, final*, start*, 0, 0, 1, final|, start|, 0, final*, start*, 0, 0, final|, start|, 0, 1, final*, start*, 0',
  '1, 0, final*, start*, start|, 0, final|, final*, start*, 0, 0, 0, start|, 0, 0, final*, final|, start|, 0, final|, final*, start*, 0, 0, 0, start|, 1, 0, start*, 0, final*, final|, start|, 0, 1, final*, start*, 0, 0, 0, final|, start|, 0, start*, 0, 1, final|, start|, 0, final*, start*, 0, final*, final*, 1, final|, final*, 0, start|, 0, final*, start*, final*, start*, 0, final|, start|, 0, 0, 0, final|, start|, 0, 1, final*, start*, 0, final*, final*, final|, 1, final*, 0, start|, 0, final*, start*, final*, start*, 0, final|, start|, 0, 0, 0, final*, start*, final*, start*, 0, final|, start|, 0, 0, final*, final*, 0, 1, final|, final*, 0, start|, 0, final*, start*, final*, start*, 0, final|, start|, 0, 0, final*, final*, 0, final|, 1, final*, 0, start|, 0, final*, start*, final*, start*, 0, final|, start|, 0, 0, final*, final*, 0, final*, 0, 1, final|, start|, 0, 1, final*, start*, final*, start*, 0, final|, start|, 0, 0, final*, final*, 0, final*, 0, final|, start|, 0, final*, start*, final*, start*, 0, final|, start|, 0, 0, final*, final*, 0, 1, final|, final*, 0, 1, final|, start|, 0, 1, final*, start*, final*, start*, 0, final|, start|, 0, 0, final*, final*, 0, final|, 1, final*, 0, final|, start|, 0, 1, final|, start|, 0, final*, start*, 0, final*, final*, 1, final|, final*, 0, 1, final|, start|, 0, final*, start*, final*, start*, 0, final|, start|, 0, 0, 0, final|, start|, 0, 1, final*, start*, 0, final*, final*, final|, 1, final*, 0, final|, start|, 0, 1, final*, start*, final*, start*, 0, final|, start|, 0, 0, 0, 1, final|, start|, 0, final*, start*, 0, final*, final*, final*, 0, 1, final|, start|, 0, final*, start*, final*, start*, 0, final|, start|, 0, 0, 0, final|, start|, 0, 1, final*, start*, 0, final*, final*, final*, 0, final|, start|, 0, 1, final*, start*, final*, start*, 0, final|, start|, 0, 0',
  '1',
  ')',
  '(',
  '*',
  ';',
  ':',
  '<',
  '>',
  '[',
  ']',
  'NONTERMINALNAME',
  'NONTERMINALNAME',
  '|',
  '2',
  'QUOTE',
  '0, 1, final*, 0, final|, start|, 0, final*, 0, final|, start|, 0, 1, final*, 0, final|, start|, 0, 1, final*, start*, final*, start*, 0, final|, start|, 0, 1, 0, 0, final|, start|, 0, 1, final*, start*, 0, 1, 0, final|, start|, 0, 0, start|, 0, final*, start*, 0, final|, start|, 0, 1, 0, 0, final|, start|, 0, 1, final*, start*, 0, 1, final*, 0, final|, start|, 0, final*, 0, start|, 0, final*, 0, final|, start|, 0, 1, final*, start*, final*, start*, 0, final|, start|, 0, 1, 0, 0, final|, start|, 0, 1, final*, start*, 0, 1, final*, 0, final|, start|, 0, final*, 0, final|, start|, 0, 1, final*, 0, start|, 0, final*, start*, final*, start*, 0, final|, start|, 0, 1, 0, 0, final|, start|, 0, 1, final*, start*, 0, 1, final*, 0, final|, start|, 0, final*, 0, final|, start|, 0, 1, final*, 0, final|, start|, 0, 1, final*, start*, final*, start*, 0, final|, start|, 0, 1, 0, 0, 1, final*, 0, final|, start|, 0, final*, 0, start|, 0, final*, 0, final|, start|, 0, 1, final*, start*, final*, start*, 0, final|, start|, 0, 1, 0',
  'QUOTE',
  'QUOTE',
  'IGNORE']), {'IGNORE': None})
# generated code between this line and its other occurence

if __name__ == '__main__':
    f = py.magic.autopath()
    oldcontent = f.read()
    s = "# GENERATED CODE BETWEEN THIS LINE AND ITS OTHER OCCURENCE\n".lower()
    pre, gen, after = oldcontent.split(s)

    parser, lexer, transformer = make_ebnf_parser()
    newcontent = "%s%s%s\nparser = %r\n%s\n%s%s" % (
            pre, s, transformer.replace("ToAST", "EBNFToAST"),
            parser, lexer.get_dummy_repr(), s, after)
    print newcontent
    f.write(newcontent)
