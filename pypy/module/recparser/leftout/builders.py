"""DEPRECATED"""

raise DeprecationWarning("This module is broken and out of date. Don't use it !")
from grammar import BaseGrammarBuilder, Alternative, Token, Sequence, KleeneStar

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

