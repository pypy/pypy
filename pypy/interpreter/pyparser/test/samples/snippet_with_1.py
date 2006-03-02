# EXPECT: Module(None, Stmt([From('__future__', [('with_statement', None)]), With(Name('acontext'), Stmt([Pass()]), None)]))
from __future__ import with_statement
with acontext:
   pass

