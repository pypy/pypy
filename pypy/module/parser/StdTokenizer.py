#! /usr/bin/env python
# ______________________________________________________________________
"""Module StdTokenizer

Implements the StdTokenizer class, which serves as a wrapper for Ping's
tokenizer in the Python distribution.

XXX While decoupling from Basil, I now assume this module can see every
submodule in the basil.common.python module.

$Id: StdTokenizer.py,v 1.2 2003/10/02 17:37:17 jriehl Exp $
"""
# ______________________________________________________________________

import tokenize
from TokenUtils import AbstractTokenizer

# ______________________________________________________________________

class StdTokenizer (AbstractTokenizer):
    """Class StdTokenizer
    Wrapper class (along with maintaining state and whatnot) for the
    Python tokenizer in the standard library.

    This is targetted as being an acceptable tokenizer for the DFAParser,
    and therefore is a callable object that returns tuples containing
    the following token information: (type, name, lineno)
    Note that some information is lost, as the token generator returns
    more information than the parser needs (XXX should this change?)
    """
    # ____________________________________________________________
    def __init__ (self, filename = None, linereader = None):
        """StdTokenizer.__init__()
        Args:
        self - Object instance
        linereader - Callable readline()-compatible object that can be passed
        directly to the generate_tokens() function.
        """
        AbstractTokenizer.__init__(self, tokenize, filename, linereader)

# ______________________________________________________________________

def main ():
    """main()
    Run the tokenizer on stdin input, printing any tokens that are recognized.
    """
    from TokenUtils import testTokenizer
    testTokenizer(StdTokenizer)

# ______________________________________________________________________

if __name__ == "__main__":
    main()

# ______________________________________________________________________
# End of StdTokenizer.py
