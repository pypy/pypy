#! /usr/bin/env python
# ______________________________________________________________________
"""Module PyTokenizer

Another Python tokenizer, but implemented without using the regex module.
(This is more folly than anything else, please use tokenize in the standard
library, or at least my wrapper class, StdTokenizer.)

XXX This now assumes that the basil.common.python submodules may be imported
directly.

$Id: PyTokenizer.py,v 1.2 2003/10/02 17:37:17 jriehl Exp $
"""
# ______________________________________________________________________

import pytokenize
from TokenUtils import AbstractTokenizer

# ______________________________________________________________________

class PyTokenizer (AbstractTokenizer):
    """Class PyTokenizer
    """
    # ____________________________________________________________
    def __init__ (self, filename = None, linereader = None):
        """PyTokenizer.__init__
        """
        AbstractTokenizer.__init__(self, pytokenize, filename, linereader)

# ______________________________________________________________________

def main ():
    """main()
    Tokenize an input file or stdin, if no file given in script arguments.
    """
    from TokenUtils import testTokenizer
    testTokenizer(PyTokenizer)

# ______________________________________________________________________

if __name__ == "__main__":
    main()

# ______________________________________________________________________
# End of PyTokenizer.py
