#!/usr/bin/env python
from grammar import BaseGrammarBuilder, Alternative, Sequence, Token, \
     KleenStar, GrammarElement
from lexer import GrammarSource

import re
py_name = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*", re.M)

punct=['>=', '<>', '!=', '<', '>', '<=', '==', '\\*=',
       '//=', '%=', '^=', '<<=', '\\*\\*=', '\\', '=',
       '\\+=', '>>=', '=', '&=', '/=', '-=', '\n,', '^', '>>', '&', '\\+', '\\*', '-', '/', '\\.', '\\*\\*', '%', '<<', '//', '\\', '', '\n\\)', '\\(', ';', ':', '@', '\\[', '\\]', '`', '\\{', '\\}']

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
        Token.__init__(self, "NAME")
        self.keywords = keywords

    def match(self, source, builder):
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
        tk_type, tk_value = source.next()
        if tk_type==self.name:
            if tk_value not in self.keywords:
                ret = builder.token( tk_type, tk_value, source )
                return self.debug_return( ret, tk_type, tk_value )
        source.restore( ctx )
        return None
        

class EBNFVisitor(object):
    def __init__(self):
        self.rules = {}
        self.terminals = {}
        self.current_rule = None
        self.current_subrule = 0
        self.tokens = {}
        self.items = []
        self.terminals['NAME'] = NameToken()

    def new_name( self ):
        rule_name = ":%s_%s" % (self.current_rule, self.current_subrule)
        self.current_subrule += 1
        return rule_name

    def new_item( self, itm ):
        self.items.append( itm )
        return itm
    
    def visit_grammar( self, node ):
        # print "Grammar:"
        for rule in node.nodes:
            rule.visit(self)
        # the rules are registered already
        # we do a pass through the variables to detect
        # terminal symbols from non terminals
        for r in self.items:
            for i,a in enumerate(r.args):
                if a.name in self.rules:
                    assert isinstance(a,Token)
                    r.args[i] = self.rules[a.name]
                    if a.name in self.terminals:
                        del self.terminals[a.name]
        # XXX .keywords also contains punctuations
        self.terminals['NAME'].keywords = self.tokens.keys()

    def visit_rule( self, node ):
        symdef = node.nodes[0].value
        self.current_rule = symdef
        self.current_subrule = 0
        alt = node.nodes[1]
        rule = alt.visit(self)
        if not isinstance( rule, Token ):
            rule.name = symdef
        self.rules[symdef] = rule
        
    def visit_alternative( self, node ):
        items = [ node.nodes[0].visit(self) ]
        items+= node.nodes[1].visit(self)        
        if len(items)==1 and items[0].name.startswith(':'):
            return items[0]
        alt = Alternative( self.new_name(), *items )
        return self.new_item( alt )

    def visit_sequence( self, node ):
        """ """
        items = []
        for n in node.nodes:
            items.append( n.visit(self) )
        if len(items)==1:
            return items[0]
        elif len(items)>1:
            return self.new_item( Sequence( self.new_name(), *items) )
        raise SyntaxError("Found empty sequence")

    def visit_sequence_cont( self, node ):
        """Returns a list of sequences (possibly empty)"""
        return [n.visit(self) for n in node.nodes]
##         L = []
##         for n in node.nodes:
##             L.append( n.visit(self) )
##         return L

    def visit_seq_cont_list(self, node):
        return node.nodes[1].visit(self)
    

    def visit_symbol(self, node):
        star_opt = node.nodes[1]
        sym = node.nodes[0].value
        terminal = self.terminals.get( sym )
        if not terminal:
            terminal = Token( sym )
            self.terminals[sym] = terminal

        return self.repeat( star_opt, terminal )

    def visit_option( self, node ):
        rule = node.nodes[1].visit(self)
        return self.new_item( KleenStar( self.new_name(), 0, 1, rule ) )

    def visit_group( self, node ):
        rule = node.nodes[1].visit(self)
        return self.repeat( node.nodes[3], rule )

    def visit_STRING( self, node ):
        value = node.value
        tok = self.tokens.get(value)
        if not tok:
            if py_punct.match( value ):
                tok = Token( value )
            elif py_name.match( value ):
                tok = Token('NAME', value)
            else:
                raise SyntaxError("Unknown STRING value ('%s')" % value )
            self.tokens[value] = tok
        return tok

    def visit_sequence_alt( self, node ):
        res = node.nodes[0].visit(self)
        assert isinstance( res, GrammarElement )
        return res

    def repeat( self, star_opt, myrule ):
        if star_opt.nodes:
            rule_name = self.new_name()
            tok = star_opt.nodes[0].nodes[0]
            if tok.value == '+':
                return self.new_item( KleenStar( rule_name, _min=1, rule = myrule ) )
            elif tok.value == '*':
                return self.new_item( KleenStar( rule_name, _min=0, rule = myrule ) )
            else:
                raise SyntaxError("Got symbol star_opt with value='%s'" % tok.value )
        return myrule


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
    # star: '*' | '+'
    star          = Alternative( "star", Token('*'), Token('+') )
    star_opt      = KleenStar  ( "star_opt", 0, 1, rule=star )

    # rule: SYMBOL ':' alternative
    symbol        = Sequence(    "symbol", Token('SYMBOL'), star_opt )
    symboldef     = Token(       "SYMDEF" )
    alternative   = Sequence(    "alternative" )
    rule          = Sequence(    "rule", symboldef, alternative )

    # grammar: rule+
    grammar       = KleenStar(   "grammar", _min=1, rule=rule )

    # alternative: sequence ( '|' sequence )*
    sequence      = KleenStar(   "sequence", 1 )
    seq_cont_list = Sequence(    "seq_cont_list", Token('|'), sequence )
    sequence_cont = KleenStar(   "sequence_cont",0, rule=seq_cont_list )
    
    alternative.args = [ sequence, sequence_cont ]

    # option: '[' alternative ']'
    option        = Sequence(    "option", Token('['), alternative, Token(']') )

    # group: '(' alternative ')'
    group         = Sequence(    "group",  Token('('), alternative, Token(')'), star_opt )

    # sequence: (SYMBOL | STRING | option | group )+
    string = Token('STRING')
    alt           = Alternative( "sequence_alt", symbol, string, option, group ) 
    sequence.args = [ alt ]
    
    return grammar


def parse_grammar(stream):
    """parses the grammar file

    stream : file-like object representing the grammar to parse
    """
    source = GrammarSource(stream.read())
    rule = grammar_grammar()
    builder = BaseGrammarBuilder()
    result = rule.match(source, builder)
    node = builder.stack[-1]
    vis = EBNFVisitor()
    node.visit(vis)
    return vis


from pprint import pprint
if __name__ == "__main__":
    grambuild = parse_grammar(file('../python/Grammar'))
    for i,r in enumerate(grambuild.items):
        print "%  3d : %s" % (i, r)
    pprint(grambuild.terminals.keys())
    pprint(grambuild.tokens)
    print "|".join(grambuild.tokens.keys() )

