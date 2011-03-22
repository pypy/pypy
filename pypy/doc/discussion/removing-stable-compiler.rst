February 28th, 2006

While implementing conditional expressions from 2.5 we had to change
the stable compiler in order to keep tests from breaking.  While using
stable compiler as a baseline made sense when the ast compiler was
new, it is less and less true as new grammar changes are introduced.

Options include

1. Freezing the stable compiler at grammar 2.4.

2. Capture AST output from the stable compiler and use that explicitly
in current tests instead of regenerating them every time, primarily
because it allows us to change the grammar without changing the stable
compiler.


In either case, AST production tests for new grammar changes could be
written manually, which is less effort than fixing the stable
compiler (which itself isn't really tested anyway).

Discussion by Arre, Anders L., Stuart Williams
