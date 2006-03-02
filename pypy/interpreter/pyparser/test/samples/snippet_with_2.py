# EXPECT: Module(None, Stmt([From('__future__', [('with_statement', None)]), With(Name('acontext'), Stmt([Pass()]), AssName('avariable', OP_ASSIGN))]))
from __future__ import with_statement
with acontext as avariable:
   pass

