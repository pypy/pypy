

from pgen import grammar_grammar, GrammarSource, GrammarVisitor
from grammar import BaseGrammarBuilder




def parse_grammar( fic ):
    src = GrammarSource( fic )
    rule = grammar_grammar()
    builder = BaseGrammarBuilder()
    result = rule.match( src, builder )
    if not result:
        print src.debug()
        raise SyntaxError("at %s" % src.debug() )
    return builder

if __name__ == "__main__":
    import sys
    fic = file('Grammar','r')
    grambuild = parse_grammar( fic )
    print grambuild.stack
    node = grambuild.stack[-1]
    vis = GrammarVisitor()
    node.visit(vis)
    for i,r in enumerate(vis.items):
        print "%  3d : %s" % (i, r)

