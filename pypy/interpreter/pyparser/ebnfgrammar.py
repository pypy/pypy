# This module contains the grammar parser
# and the symbol mappings

from grammar import BaseGrammarBuilder, Alternative, Sequence, Token, \
     KleeneStar, GrammarElement, build_first_sets, EmptyToken


sym_map = {}
sym_rmap = {}
_count = 0

def g_add_symbol( name ):
    global _count
    if name in sym_rmap:
        return sym_rmap[name]
    val = _count
    _count += 1
    sym_map[val] = name
    sym_rmap[name] = val
    return val


tok_map = {}
tok_rmap = {}

def g_add_token( **kwargs ):
    global _count
    assert len(kwargs) == 1
    sym, name = kwargs.popitem()
    if name in tok_rmap:
        return tok_rmap[name]
    val = _count
    _count += 1
    tok_map[val] = name
    tok_rmap[name] = val
    sym_map[val] = sym
    sym_rmap[sym] = val
    return val

g_add_token( EOF='EOF' )


def grammar_grammar():
    """NOT RPYTHON  (mostly because of g_add_token I suppose)
    Builds the grammar for the grammar file

    Here's the description of the grammar's grammar ::

      grammar: rule+
      rule: SYMDEF alternative
      
      alternative: sequence ( '|' sequence )+
      star: '*' | '+'
      sequence: (SYMBOL star? | STRING | option | group star? )+
      option: '[' alternative ']'
      group: '(' alternative ')' star?
    """
    global sym_map
    S = g_add_symbol
    T = g_add_token
    # star: '*' | '+'
    star          = Alternative( S("star"), [Token(T(TOK_STAR='*')), Token(T(TOK_ADD='+'))] )
    star_opt      = KleeneStar ( S("star_opt"), 0, 1, rule=star )

    # rule: SYMBOL ':' alternative
    symbol        = Sequence(    S("symbol"), [Token(T(TOK_SYMBOL='SYMBOL')), star_opt] )
    symboldef     = Token(       T(TOK_SYMDEF="SYMDEF") )
    alternative   = Sequence(    S("alternative"), [])
    rule          = Sequence(    S("rule"), [symboldef, alternative] )

    # grammar: rule+
    grammar       = KleeneStar(   S("grammar"), _min=1, rule=rule )

    # alternative: sequence ( '|' sequence )*
    sequence      = KleeneStar(   S("sequence"), 1 )
    seq_cont_list = Sequence(    S("seq_cont_list"), [Token(T(TOK_BAR='|')), sequence] )
    sequence_cont = KleeneStar(   S("sequence_cont"),0, rule=seq_cont_list )
    
    alternative.args = [ sequence, sequence_cont ]

    # option: '[' alternative ']'
    option        = Sequence(    S("option"), [Token(T(TOK_LBRACKET='[')), alternative, Token(T(TOK_RBRACKET=']'))] )

    # group: '(' alternative ')'
    group         = Sequence(    S("group"),  [Token(T(TOK_LPAR='(')), alternative, Token(T(TOK_RPAR=')')), star_opt] )

    # sequence: (SYMBOL | STRING | option | group )+
    string = Token(T(TOK_STRING='STRING'))
    alt           = Alternative( S("sequence_alt"), [symbol, string, option, group] ) 
    sequence.args = [ alt ]


    rules = [ star, star_opt, symbol, alternative, rule, grammar, sequence,
              seq_cont_list, sequence_cont, option, group, alt ]
    build_first_sets( rules )
    return grammar


GRAMMAR_GRAMMAR = grammar_grammar()

for _sym, _value in sym_rmap.items():
    globals()[_sym] = _value

# cleanup
del _sym
del _value
del grammar_grammar
del g_add_symbol
del g_add_token
