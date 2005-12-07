#
# Generate a Python Syntax analyser from the Python's grammar
# The grammar comes from the Grammar file in Python source tree
# 
from pylexer import PythonSource
import pylexer
DEBUG=0

class BuilderToken(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return "%s=(%s)" % (self.name, self.value)

    def display(self, indent=""):
        print indent,self.name,"=",self.value,
        
class BuilderRule(object):
    def __init__(self, name, values):
        self.name = name
        self.values = values

    def __str__(self):
        return "%s=(%s)" % (self.name, self.values)

    def display(self, indent=""):
        print indent,self.name,'('
        for v in self.values:
            v.display(indent+"|  ")
            print ","
        print indent,')',

class SimpleBuilder(object):
    """Default builder class (print output)"""
    def __init__(self):
        self.gramrules = {}

    def alternative( self, name, value, source ):
        print "alt:", self.gramrules.get(name, name), "   --", source.debug()
        #print "Alternative", name
        return BuilderRule( name, [value] )

    def sequence( self, name, values, source ):
        print "seq:", self.gramrules.get(name, name), "   --", source.debug()
        #print "Sequence", name
        return BuilderRule( name, values)
    
    def token( self, name, value, source ):
        print "tok:", self.gramrules.get(name, name), "   --", source.debug()
        #print "Token", name, value
        return BuilderToken( name, value )
        

import re
import grammar
from grammar import Token, Alternative, KleeneStar, Sequence, TokenSource, BaseGrammarBuilder, Proxy, Pgen

g_symdef = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*:",re.M)
g_symbol = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*",re.M)
g_string = re.compile(r"'[^']+'",re.M)
g_tok = re.compile(r"\[|\]|\(|\)|\*|\+|\|",re.M)
g_skip = re.compile(r"\s*(#.*$)?",re.M)

class GrammarSource(TokenSource):
    """The grammar tokenizer"""
    def __init__(self, inpstream ):
        TokenSource.__init__(self)
        self.input = inpstream.read()
        self.pos = 0

    def context(self):
        return self.pos

    def restore(self, ctx ):
        self.pos = ctx

    def next(self):
        pos = self.pos
        inp = self.input
        m = g_skip.match(inp, pos)
        while m and pos!=m.end():
            pos = m.end()
            if pos==len(inp):
                self.pos = pos
                return None, None
            m = g_skip.match(inp, pos)
        m = g_symdef.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return 'SYMDEF',tk[:-1]
        m = g_tok.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return tk,tk
        m = g_string.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return 'STRING',tk[1:-1]
        m = g_symbol.match(inp,pos)
        if m:
            tk = m.group(0)
            self.pos = m.end()
            return 'SYMBOL',tk
        raise ValueError("Unknown token at pos=%d context='%s'" % (pos,inp[pos:pos+20]) )

    def debug(self):
        return self.input[self.pos:self.pos+20]

def debug_rule( rule ):
    nm = rule.__class__.__name__
    print nm, rule.name, "->",
    if nm=='KleeneStar':
        print "(%d,%d,%s)" % (rule.min, rule.max, rule.star),
    for x in rule.args:
        print x.name,
    print

def debug_rule( *args ):
    pass


class GrammarBuilder(BaseGrammarBuilder):
    """Builds a grammar from a grammar desc"""
    def __init__(self):
        self.rules = {}
        self.terminals = {}
        self.rule_idx = 0
        self.items = []
        self.tokens = {}

    def alternative( self, name, source ):
        pass
    
    def sequence( self, name, source, N ):
        #print "seq:", name, "->", source.debug()
        #print "Sequence", name
        meth = getattr(self, "build_%s" % name, None)
        if meth:
            return meth(values)
        raise RuntimeError( "symbol %s unhandled" % name )
    
    def token( self, name, value, source ):
        #print "tok:", name, "->", source.debug()
        #print "Token", name, value
        if name=="SYMDEF":
            return value
        elif name=="STRING":
            tok = self.tokens.get(value)
            if not tok:
                tok = Token(value)
                self.tokens[value] = tok
            return tok
        elif name=="SYMBOL":
            sym = self.terminals.get(value)
            if not sym:
                sym = Token(value)
                self.terminals[value] = sym
            return sym
        elif name in ('*','+','(','[',']',')','|',):
            return name
        return BuilderToken( name, value )

    def build_sequence( self, values ):
        """sequence: sequence_alt+
        sequence_alt: symbol | STRING | option | group star?
        """
        if len(values)==1:
            return values[0]
        if len(values)>1:
            seq = Sequence( self.get_name(), *values )
            self.items.append(seq)
            debug_rule( seq )
            return seq
        return True

    def get_name(self):
        s = "Rule_%03d" % self.rule_idx
        self.rule_idx += 1
        return s
    
    def build_rule( self, values ):
        rule_def = values[0]
        rule_alt = values[1]
        if not isinstance(rule_alt,Token):
            rule_alt.name = rule_def
        self.rules[rule_def] = rule_alt
        return True

    def build_alternative( self, values ):
        if len(values[1])>0:
            alt = Alternative( self.get_name(), values[0], *values[1] )
            debug_rule( alt )
            self.items.append(alt)
            return alt
        else:
            return values[0]

    def build_star_opt( self, values ):
        """star_opt: star?"""
        if values:
            return values[0]
        else:
            return True

    def build_seq_cont_list( self, values ):
        """seq_cont_list: '|' sequence """
        return values[1]

    def build_symbol( self, values ):
        """symbol: SYMBOL star?"""
        sym = values[0]
        star = values[1]
        if star is True:
            return sym
        _min = 0
        _max = -1
        if star=='*':
            _min = 0
        elif star=='+':
            _min = 1
        sym = KleeneStar( self.get_name(), _min, _max, rule=sym )
        sym.star = star
        debug_rule( sym )
        self.items.append(sym)
        return sym
    
    def build_group( self, values ):
        """group:  '(' alternative ')' star?"""
        return self.build_symbol( [ values[1], values[3] ] )
     
    def build_option( self, values ):
        """option: '[' alternative ']'"""
        sym = KleeneStar( self.get_name(), 0, 1, rule=values[1] )
        debug_rule( sym )
        self.items.append(sym)
        return sym

    def build_sequence_cont( self, values ):
        """sequence_cont: seq_cont_list*"""
        return values

    def build_grammar( self, values ):
        """ grammar: rules+"""
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


class GrammarVisitor(object):
    def __init__(self):
        self.rules = {}
        self.terminals = {}
        self.current_rule = None
        self.current_subrule = 0
        self.tokens = {}
        self.items = []

    def new_name( self ):
        rule_name = ":%s_%s" % (self.current_rule, self.current_subrule)
        self.current_subrule += 1
        return rule_name

    def new_item( self, itm ):
        self.items.append( itm )
        return itm
    
    def visit_grammar( self, node ):
        print "Grammar:"
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
        if len(items)==1:
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
        L = []
        for n in node.nodes:
            L.append( n.visit(self) )
        return L

    def visit_seq_cont_list( self, node ):
        return node.nodes[1].visit(self)
    

    def visit_symbol( self, node ):
        star_opt = node.nodes[1]
        sym = node.nodes[0].value
        terminal = self.terminals.get( sym )
        if not terminal:
            terminal = Token( sym )
            self.terminals[sym] = terminal

        return self.repeat( star_opt, terminal )

    def visit_option( self, node ):
        rule = node.nodes[1].visit(self)
        return self.new_item( KleeneStar( self.new_name(), 0, 1, rule ) )

    def visit_group( self, node ):
        rule = node.nodes[1].visit(self)
        return self.repeat( node.nodes[3], rule )

    def visit_STRING( self, node ):
        value = node.value
        tok = self.tokens.get(value)
        if not tok:
            if pylexer.py_punct.match( value ):
                tok = Token( value )
            elif pylexer.py_name.match( value ):
                tok = Token('NAME',value)
            else:
                raise SyntaxError("Unknown STRING value ('%s')" % value )
            self.tokens[value] = tok
        return tok

    def visit_sequence_alt( self, node ):
        res = node.nodes[0].visit(self)
        assert isinstance( res, Pgen )
        return res

    def repeat( self, star_opt, myrule ):
        if star_opt.nodes:
            rule_name = self.new_name()
            tok = star_opt.nodes[0].nodes[0]
            if tok.value == '+':
                return self.new_item( KleeneStar( rule_name, _min=1, rule = myrule ) )
            elif tok.value == '*':
                return self.new_item( KleeneStar( rule_name, _min=0, rule = myrule ) )
            else:
                raise SyntaxError("Got symbol star_opt with value='%s'" % tok.value )
        return myrule
        
    
_grammar = """
grammar: rule+
rule: SYMDEF alternative

alternative: sequence ( '|' sequence )+
star: '*' | '+'
sequence: (SYMBOL star? | STRING | option | group star? )+
option: '[' alternative ']'
group: '(' alternative ')' star?
"""
def grammar_grammar():
    """Builds the grammar for the grammar file
    """
    # star: '*' | '+'
    star          = Alternative( "star", Token('*'), Token('+') )
    star_opt      = KleeneStar  ( "star_opt", 0, 1, rule=star )

    # rule: SYMBOL ':' alternative
    symbol        = Sequence(    "symbol", Token('SYMBOL'), star_opt )
    symboldef     = Token(       "SYMDEF" )
    alternative   = Sequence(    "alternative" )
    rule          = Sequence(    "rule", symboldef, alternative )

    # grammar: rule+
    grammar       = KleeneStar(   "grammar", _min=1, rule=rule )

    # alternative: sequence ( '|' sequence )*
    sequence      = KleeneStar(   "sequence", 1 )
    seq_cont_list = Sequence(    "seq_cont_list", Token('|'), sequence )
    sequence_cont = KleeneStar(   "sequence_cont",0, rule=seq_cont_list )
    
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


def parse_python( pyf, gram ):
    target = gram.rules['file_input']
    src = PythonSource( pyf.read() )
    builder = BaseGrammarBuilder(debug=False, rules=gram.rules)
    #    for r in gram.items:
    #        builder.gramrules[r.name] = rg
    result = target.match( src, builder )
    print result, builder.stack
    if not result:
        print src.debug()
        raise SyntaxError("at %s" % src.debug() )
    return builder
    

from pprint import pprint
def parse_grammar( fic ):
    src = GrammarSource( fic )
    rule = grammar_grammar()
    builder = BaseGrammarBuilder()
    result = rule.match( src, builder )
    node = builder.stack[-1]
    vis = GrammarVisitor()
    node.visit(vis)

    return vis


if __name__ == "__main__":
    grammar.DEBUG = False
    import sys
    fic = file('Grammar','r')
    grambuild = parse_grammar( fic )
    if len(sys.argv)>1:
        print "-"*20
        print
        pyf = file(sys.argv[1],'r')
        DEBUG = 0
        builder = parse_python( pyf, grambuild )
        #print "**", builder.stack
        if builder.stack:
            print builder.stack[-1].dumpstr()
            tp1 = builder.stack[-1]
            import parser
            tp2 = parser.suite( file(sys.argv[1]).read() )
        
    else:
        for i,r in enumerate(grambuild.items):
            print "%  3d : %s" % (i, r)
        pprint(grambuild.terminals.keys())
        pprint(grambuild.tokens)
        print "|".join(grambuild.tokens.keys() )
