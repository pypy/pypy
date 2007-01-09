#!/usr/bin/env python
from grammar import BaseGrammarBuilder, Alternative, Sequence, Token, \
     KleeneStar, GrammarElement, build_first_sets, EmptyToken
from ebnflexer import GrammarSource
import ebnfgrammar
from ebnfgrammar import GRAMMAR_GRAMMAR, sym_map
from syntaxtree import AbstractSyntaxVisitor
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
            if tk.value not in builder.keywords:
                ret = builder.token( tk.codename, tk.value, source )
                return self.debug_return( ret, tk.codename, tk.value )
        source.restore( ctx )
        return 0
        
    def match_token(self, builder, other):
        """special case of match token for tokens which are really keywords
        """
        if not isinstance(other, Token):
            raise RuntimeError("Unexpected token type %r" % other)
        if other is EmptyToken:
            return False
        if other.codename != self.codename:
            return False
        if other.value in builder.keywords:
            return False
        return True



def ebnf_handle_grammar(self, node):
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

def ebnf_handle_rule(self, node):
    symdef = node.nodes[0].value
    self.current_rule = symdef
    self.current_subrule = 0
    alt = node.nodes[1]
    rule = alt.visit(self)
    if not isinstance(rule, Token):
        rule.codename = self.symbols.add_symbol( symdef )
    self.rules[rule.codename] = rule

def ebnf_handle_alternative(self, node):
    items = [node.nodes[0].visit(self)]
    items += node.nodes[1].visit(self)        
    if len(items) == 1 and not items[0].is_root():
        return items[0]
    alt = Alternative(self.new_symbol(), items)
    return self.new_item(alt)

def ebnf_handle_sequence( self, node ):
    """ """
    items = []
    for n in node.nodes:
        items.append( n.visit(self) )
    if len(items)==1:
        return items[0]
    elif len(items)>1:
        return self.new_item( Sequence( self.new_symbol(), items) )
    raise RuntimeError("Found empty sequence")

def ebnf_handle_sequence_cont( self, node ):
    """Returns a list of sequences (possibly empty)"""
    return [n.visit(self) for n in node.nodes]

def ebnf_handle_seq_cont_list(self, node):
    return node.nodes[1].visit(self)


def ebnf_handle_symbol(self, node):
    star_opt = node.nodes[1]
    sym = node.nodes[0].value
    terminal = self.terminals.get( sym, None )
    if not terminal:
        tokencode = pytoken.tok_values.get( sym, None )
        if tokencode is None:
            tokencode = self.symbols.add_symbol( sym )
            terminal = Token( tokencode )
        else:
            terminal = Token( tokencode )
            self.terminals[sym] = terminal

    return self.repeat( star_opt, terminal )

def ebnf_handle_option( self, node ):
    rule = node.nodes[1].visit(self)
    return self.new_item( KleeneStar( self.new_symbol(), 0, 1, rule ) )

def ebnf_handle_group( self, node ):
    rule = node.nodes[1].visit(self)
    return self.repeat( node.nodes[3], rule )

def ebnf_handle_TOK_STRING( self, node ):
    value = node.value
    tokencode = pytoken.tok_punct.get( value, None )
    if tokencode is None:
        if not py_name.match( value ):
            raise RuntimeError("Unknown STRING value ('%s')" % value )
        # assume a keyword
        tok = Token( pytoken.NAME, value )
        if value not in self.keywords:
            self.keywords.append( value )
    else:
        # punctuation
        tok = Token( tokencode )
    return tok

def ebnf_handle_sequence_alt( self, node ):
    res = node.nodes[0].visit(self)
    assert isinstance( res, GrammarElement )
    return res

# This will setup a mapping between
# ebnf_handle_xxx functions and ebnfgrammar.xxx
ebnf_handles = {}
for name, value in globals().items():
    if name.startswith("ebnf_handle_"):
        name = name[12:]
        key = getattr(ebnfgrammar, name )
        ebnf_handles[key] = value

def handle_unknown( self, node ):
    raise RuntimeError("Unknown Visitor for %r" % node.name)
    

class EBNFVisitor(AbstractSyntaxVisitor):
    
    def __init__(self):
        self.rules = {}
        self.terminals = {}
        self.current_rule = None
        self.current_subrule = 0
        self.keywords = []
        self.items = []
        self.terminals['NAME'] = NameToken()
        self.symbols = pysymbol.SymbolMapper( pysymbol._cpython_symbols.sym_name )

    def new_symbol(self):
        rule_name = ":%s_%s" % (self.current_rule, self.current_subrule)
        self.current_subrule += 1
        symval = self.symbols.add_anon_symbol( rule_name )
        return symval

    def new_item(self, itm):
        self.items.append(itm)
        return itm

    def visit_syntaxnode( self, node ):
        visit_func = ebnf_handles.get( node.name, handle_unknown )
        return visit_func( self, node )

    def visit_tokennode( self, node ):
        return self.visit_syntaxnode( node )

    def visit_tempsyntaxnode( self, node ):
        return self.visit_syntaxnode( node )


    def repeat( self, star_opt, myrule ):
        assert isinstance( myrule, GrammarElement )
        if star_opt.nodes:
            rule_name = self.new_symbol()
            tok = star_opt.nodes[0].nodes[0]
            if tok.value == '+':
                item = KleeneStar(rule_name, _min=1, rule=myrule)
                return self.new_item(item)
            elif tok.value == '*':
                item = KleeneStar(rule_name, _min=0, rule=myrule)
                return self.new_item(item)
            else:
                raise RuntimeError("Got symbol star_opt with value='%s'"
                                  % tok.value)
        return myrule



def parse_grammar(stream):
    """parses the grammar file

    stream : file-like object representing the grammar to parse
    """
    source = GrammarSource(stream.read())
    builder = BaseGrammarBuilder()
    result = GRAMMAR_GRAMMAR.match(source, builder)
    node = builder.stack[-1]
    vis = EBNFVisitor()
    node.visit(vis)
    return vis

def parse_grammar_text(txt):
    """parses a grammar input

    stream : file-like object representing the grammar to parse
    """
    source = GrammarSource(txt)
    builder = BaseGrammarBuilder()
    result = GRAMMAR_GRAMMAR.match(source, builder)
    node = builder.stack[-1]
    vis = EBNFVisitor()
    node.visit(vis)
    return vis

def target_parse_grammar_text(txt):
    vis = parse_grammar_text(txt)
    # do nothing

from pprint import pprint
if __name__ == "__main__":
    grambuild = parse_grammar(file('data/Grammar2.4'))
    for i,r in enumerate(grambuild.items):
        print "%  3d : %s" % (i, r)
    pprint(grambuild.terminals.keys())
    pprint(grambuild.tokens)
    print "|".join(grambuild.tokens.keys() )

