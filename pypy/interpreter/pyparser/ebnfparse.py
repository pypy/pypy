#!/usr/bin/env python
from grammar import BaseGrammarBuilder, Alternative, Sequence, Token, \
     KleenStar, GrammarElement, build_first_sets, EmptyToken
from ebnflexer import GrammarSource
import pytoken
import pysymbol

import re
py_name = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*", re.M)

punct=['>=', '<>', '!=', '<', '>', '<=', '==', '\\*=',
       '//=', '%=', '^=', '<<=', '\\*\\*=', '\\', '=',
       '\\+=', '>>=', '=', '&=', '/=', '-=', '\n,', '^',
       '>>', '&', '\\+', '\\*', '-', '/', '\\.', '\\*\\*',
       '%', '<<', '//', '\\', '', '\n\\)', '\\(', ';', ':',
       '@', '\\[', '\\]', '`', '\\{', '\\}']

py_punct = re.compile(r"""
>=|<>|!=|<|>|<=|==|~|
\*=|//=|%=|\^=|<<=|\*\*=|\|=|\+=|>>=|=|&=|/=|-=|
,|\^|>>|&|\+|\*|-|/|\.|\*\*|%|<<|//|\||
\)|\(|;|:|@|\[|\]|`|\{|\}
""", re.M | re.X)


TERMINALS = [
    'NAME', 'NUMBER', 'STRING', 'NEWLINE', 'ENDMARKER',
    'INDENT', 'DEDENT' ]


## Grammar Visitors ##################################################
# FIXME: parsertools.py ? parser/__init__.py ?

class NameToken(Token):
    """A token that is not a keyword"""
    def __init__(self, keywords=None ):
        Token.__init__(self, pytoken.NAME)
        self.keywords = keywords

    def match(self, source, builder, level=0):
        """Matches a token.
        the default implementation is to match any token whose type
        corresponds to the object's name. You can extend Token
        to match anything returned from the lexer. for exemple
        type, value = source.next()
        if type=="integer" and int(value)>=0:
            # found
        else:
            # error unknown or negative integer
        """
        ctx = source.context()
        tk = source.next()
        if tk.codename==self.codename:
            if tk.value not in self.keywords:
                ret = builder.token( tk.codename, tk.value, source )
                return self.debug_return( ret, tk.codename, tk.value )
        source.restore( ctx )
        return 0
        
    def match_token(self, other):
        """special case of match token for tokens which are really keywords
        """
        if not isinstance(other, Token):
            raise RuntimeError("Unexpected token type %r" % other)
        if other is EmptyToken:
            return False
        if other.codename != self.codename:
            return False
        if other.value in self.keywords:
            return False
        return True


class EBNFVisitor(object):
    
    def __init__(self):
        self.rules = {}
        self.terminals = {}
        self.current_rule = None
        self.current_subrule = 0
        self.keywords = []
        self.items = []
        self.terminals['NAME'] = NameToken()

    def new_symbol(self):
        rule_name = ":%s_%s" % (self.current_rule, self.current_subrule)
        self.current_subrule += 1
        symval = pysymbol.add_anon_symbol( rule_name )
        return symval

    def new_item(self, itm):
        self.items.append(itm)
        return itm

    def visit_syntaxnode( self, node ):
        """NOT RPYTHON, used only at bootstrap time anyway"""
        name = sym_map[node.name]
        visit_meth = getattr(self, "handle_%s" % name, None)
        if visit_meth:
            return visit_meth(node)
        else:
            print "Unknown handler for %s" %name
        # helper function for nodes that have only one subnode:
        if len(node.nodes) == 1:
            return node.nodes[0].visit(visitor)
        raise RuntimeError("Unknown Visitor for %r" % name)

    def visit_tokennode( self, node ):
        return self.visit_syntaxnode( node )

    def visit_tempsyntaxnode( self, node ):
        return self.visit_syntaxnode( node )

    def handle_grammar(self, node):
        for rule in node.nodes:
            rule.visit(self)
        # the rules are registered already
        # we do a pass through the variables to detect
        # terminal symbols from non terminals
        for r in self.items:
            for i,a in enumerate(r.args):
                if a.codename in self.rules:
                    assert isinstance(a,Token)
                    r.args[i] = self.rules[a.codename]
                    if a.codename in self.terminals:
                        del self.terminals[a.codename]
        # XXX .keywords also contains punctuations
        self.terminals['NAME'].keywords = self.keywords

    def handle_rule(self, node):
        symdef = node.nodes[0].value
        self.current_rule = symdef
        self.current_subrule = 0
        alt = node.nodes[1]
        rule = alt.visit(self)
        if not isinstance(rule, Token):
            rule.codename = pysymbol.add_symbol( symdef )
        self.rules[rule.codename] = rule
        
    def handle_alternative(self, node):
        items = [node.nodes[0].visit(self)]
        items += node.nodes[1].visit(self)        
        if len(items) == 1 and not items[0].is_root():
            return items[0]
        alt = Alternative(self.new_symbol(), items)
        return self.new_item(alt)

    def handle_sequence( self, node ):
        """ """
        items = []
        for n in node.nodes:
            items.append( n.visit(self) )
        if len(items)==1:
            return items[0]
        elif len(items)>1:
            return self.new_item( Sequence( self.new_symbol(), items) )
        raise SyntaxError("Found empty sequence")

    def handle_sequence_cont( self, node ):
        """Returns a list of sequences (possibly empty)"""
        return [n.visit(self) for n in node.nodes]

    def handle_seq_cont_list(self, node):
        return node.nodes[1].visit(self)
    

    def handle_symbol(self, node):
        star_opt = node.nodes[1]
        sym = node.nodes[0].value
        terminal = self.terminals.get( sym )
        if not terminal:
            tokencode = pytoken.tok_values.get( sym )
            if tokencode is None:
                tokencode = pysymbol.add_symbol( sym )
                terminal = Token( tokencode )
            else:
                terminal = Token( tokencode )
                self.terminals[sym] = terminal

        return self.repeat( star_opt, terminal )

    def handle_option( self, node ):
        rule = node.nodes[1].visit(self)
        return self.new_item( KleenStar( self.new_symbol(), 0, 1, rule ) )

    def handle_group( self, node ):
        rule = node.nodes[1].visit(self)
        return self.repeat( node.nodes[3], rule )

    def handle_STRING( self, node ):
        value = node.value
        tokencode = pytoken.tok_punct.get( value )
        if tokencode is None:
            if not py_name.match( value ):
                raise SyntaxError("Unknown STRING value ('%s')" % value )
            # assume a keyword
            tok = Token( pytoken.NAME, value )
            if value not in self.keywords:
                self.keywords.append( value )
        else:
            # punctuation
            tok = Token( tokencode )
        return tok

    def handle_sequence_alt( self, node ):
        res = node.nodes[0].visit(self)
        assert isinstance( res, GrammarElement )
        return res

    def repeat( self, star_opt, myrule ):
        assert isinstance( myrule, GrammarElement )
        if star_opt.nodes:
            rule_name = self.new_symbol()
            tok = star_opt.nodes[0].nodes[0]
            if tok.value == '+':
                item = KleenStar(rule_name, _min=1, rule=myrule)
                return self.new_item(item)
            elif tok.value == '*':
                item = KleenStar(rule_name, _min=0, rule=myrule)
                return self.new_item(item)
            else:
                raise SyntaxError("Got symbol star_opt with value='%s'"
                                  % tok.value)
        return myrule

rules = None

sym_map = {}
sym_rmap = {}
sym_count = 0

def g_add_symbol( name ):
    global sym_count
    if name in sym_rmap:
        return sym_rmap[name]
    val = sym_count
    sym_count += 1
    sym_map[val] = name
    sym_rmap[name] = val
    return val

g_add_symbol( 'EOF' )

def grammar_grammar():
    """Builds the grammar for the grammar file

    Here's the description of the grammar's grammar ::

      grammar: rule+
      rule: SYMDEF alternative
      
      alternative: sequence ( '|' sequence )+
      star: '*' | '+'
      sequence: (SYMBOL star? | STRING | option | group star? )+
      option: '[' alternative ']'
      group: '(' alternative ')' star?    
    """
    global rules, sym_map
    S = g_add_symbol
    # star: '*' | '+'
    star          = Alternative( S("star"), [Token(S('*')), Token(S('+'))] )
    star_opt      = KleenStar  ( S("star_opt"), 0, 1, rule=star )

    # rule: SYMBOL ':' alternative
    symbol        = Sequence(    S("symbol"), [Token(S('SYMBOL')), star_opt] )
    symboldef     = Token(       S("SYMDEF") )
    alternative   = Sequence(    S("alternative"), [])
    rule          = Sequence(    S("rule"), [symboldef, alternative] )

    # grammar: rule+
    grammar       = KleenStar(   S("grammar"), _min=1, rule=rule )

    # alternative: sequence ( '|' sequence )*
    sequence      = KleenStar(   S("sequence"), 1 )
    seq_cont_list = Sequence(    S("seq_cont_list"), [Token(S('|')), sequence] )
    sequence_cont = KleenStar(   S("sequence_cont"),0, rule=seq_cont_list )
    
    alternative.args = [ sequence, sequence_cont ]

    # option: '[' alternative ']'
    option        = Sequence(    S("option"), [Token(S('[')), alternative, Token(S(']'))] )

    # group: '(' alternative ')'
    group         = Sequence(    S("group"),  [Token(S('(')), alternative, Token(S(')')), star_opt] )

    # sequence: (SYMBOL | STRING | option | group )+
    string = Token(S('STRING'))
    alt           = Alternative( S("sequence_alt"), [symbol, string, option, group] ) 
    sequence.args = [ alt ]


    rules = [ star, star_opt, symbol, alternative, rule, grammar, sequence,
              seq_cont_list, sequence_cont, option, group, alt ]
    build_first_sets( rules )
    return grammar


def parse_grammar(stream):
    """parses the grammar file

    stream : file-like object representing the grammar to parse
    """
    source = GrammarSource(stream.read(), sym_rmap)
    rule = grammar_grammar()
    builder = BaseGrammarBuilder()
    result = rule.match(source, builder)
    node = builder.stack[-1]
    vis = EBNFVisitor()
    node.visit(vis)
    return vis


from pprint import pprint
if __name__ == "__main__":
    grambuild = parse_grammar(file('data/Grammar2.3'))
    for i,r in enumerate(grambuild.items):
        print "%  3d : %s" % (i, r)
    pprint(grambuild.terminals.keys())
    pprint(grambuild.tokens)
    print "|".join(grambuild.tokens.keys() )

