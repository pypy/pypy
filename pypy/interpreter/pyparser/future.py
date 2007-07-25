"""
This automaton is designed to be invoked on a Python source string
before the real parser starts working, in order to find all legal
'from __future__ import blah'. As soon as something is encountered that
would prevent more future imports, the analysis is aborted.
The resulting legal futures are avaliable in self.flags after the
pass has ended.

Invocation is through getFutures(src), which returns a field of flags,
one per found correct future import.

The flags can then be used to set up the parser.
All error detection is left to the parser.

The reason we are not using the regular lexer/parser toolchain is that
we do not want the overhead of generating tokens for entire files just
to find information that resides in the first few lines of the file.
Neither do we require sane error messages, as this job is handled by
the parser.

To make the parsing fast, especially when the module is translated to C,
the code has been written in a very serial fashion, using an almost
assembler like style. A further speedup could be achieved by replacing
the "in" comparisons with explicit numeric comparisons.
"""

from pypy.interpreter.astcompiler.consts import CO_GENERATOR_ALLOWED, \
    CO_FUTURE_DIVISION, CO_FUTURE_WITH_STATEMENT
            
def getFutures(source):
    futures = FutureAutomaton(source)
    try:
        futures.start()
    except (IndexError, DoneException), e:
        pass
    return futures.flags
    
class DoneException(Exception):
    pass

whitespace = ' \t\f'
letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYabcdefghijklmnopqrstuvwxyz_'
alphanumerics = letters + '1234567890'

class FutureAutomaton(object):
    """
    A future statement must appear near the top of the module.
    The only lines that can appear before a future statement are:

        * the module docstring (if any),
        * comments,
        * blank lines, and
        * other future statements.

    The features recognized by Python 2.5 are "generators",
    "division", "nested_scopes" and "with_statement".
    "generators", "division" and "nested_scopes" are redundant
    in 2.5 because they are always enabled.

    This module parses the input until it encounters something that is
    not recognized as a valid future statement or something that may
    precede a future statement.
    """
    
    def __init__(self, string):
        self.s = string
        self.end = len(string)
        self.pos = 0
        self.docstringConsumed = False
        self.flags = 0
        
    def start(self):
        c = self.s[self.pos]
        if c in ["'", '"'] and not self.docstringConsumed:
            self.consumeDocstring()
        elif c in whitespace:
            self.consumeEmptyLine()
        elif c == '#':
            self.consumeComment()
        elif c == 'f':
            self.consumeFrom()
        else:
            return

    def consumeDocstring(self):
        self.docstringConsumed = True
        endchar = self.s[self.pos]
        if (self.s[self.pos] == self.s[self.pos+1] and
            self.s[self.pos] == self.s[self.pos+2]):
            self.pos += 3
            while 1: # Deal with a triple quoted docstring
                if self.s[self.pos] != endchar:
                    self.pos += 1
                else:
                    self.pos += 1
                    if (self.s[self.pos] == endchar and
                        self.s[self.pos+1] == endchar):
                        self.pos += 2
                        self.consumeEmptyLine()
                        break

        else: # Deal with a single quoted docstring
            self.pos += 1
            while 1:
                c = self.s[self.pos]
                self.pos += 1
                if c == endchar:
                    self.consumeEmptyLine()
                    return
                elif c == '\\':
                    # Deal with linefeeds
                    if self.s[self.pos] not in ['\r', '\n']:
                        self.pos += 1
                        continue
                    elif self.s[self.pos] == '\r':
                        self.pos += 1
                        if self.s[self.pos] == '\n':
                            self.pos += 1
                        continue
                    else: # '\n' is the only option left
                        self.pos += 1
                        continue
                elif c in ['\r', '\n']:
                    # Syntax error
                    return

    def consumeEmptyLine(self):
        """
        Called when the remainder of the line can only contain whitespace
        and comments.
        """
        while self.s[self.pos] in whitespace:
            self.pos += 1
        if self.s[self.pos] == '#':
            self.consumeComment()
        elif self.s[self.pos] == ';':
            self.pos += 1
            self.consumeWhitespace()
            self.start()
        elif self.s[self.pos] in ['\r', '\n']:
            self.pos += 1
            if self.s[self.pos] == '\n':
                self.pos += 1
            self.start()
            
    def consumeComment(self):
        self.pos += 1
        while self.s[self.pos] not in ['\r', '\n']:
            self.pos += 1
        self.consumeEmptyLine()

    def consumeFrom(self):
        self.pos += 1
        p = self.pos
        s = self.s
        if s[p] == 'r' and s[p+1] == 'o' and s[p+2] == 'm':
            self.docstringConsumed = True
            self.pos += 3
            self.consumeMandatoryWhitespace()
            if self.s[self.pos:self.pos+10] != '__future__':
                raise DoneException
            self.pos += 10
            self.consumeMandatoryWhitespace()
            if self.s[self.pos:self.pos+6] != 'import':
                raise DoneException
            self.pos += 6
            self.consumeWhitespace()
            if self.s[self.pos] == '(':
                self.pos += 1
                self.consumeWhitespace()
                self.setFlag(self.getName())
                # Set flag corresponding to name
                self.getMore(parenList=True)
            else:
                self.setFlag(self.getName())
                self.getMore()
            self.consumeEmptyLine()
        else:
            return
        
    def consumeMandatoryWhitespace(self):
        if self.s[self.pos] not in whitespace + '\\':
            raise DoneException
        self.consumeWhitespace()
        
    def consumeWhitespace(self):
        while 1:
            c = self.s[self.pos]
            if c in whitespace:
                self.pos += 1
                continue
            elif c == '\\':
                self.pos += 1
                c = self.s[self.pos]
                if c == '\n':
                    self.pos += 1
                    continue
                elif c == '\r':
                    self.pos += 1
                    if self.s[self.pos] == '\n':
                        self.pos += 1
                else:
                    raise DoneException
            else:
                return

    def getName(self):
        if self.s[self.pos] not in letters:
            raise DoneException
        p = self.pos
        while 1:
            self.pos += 1
            if self.s[self.pos] not in alphanumerics:
                break
        name = self.s[p:self.pos]
        self.consumeWhitespace()
        return name

    def getMore(self, parenList=False):
        if parenList and self.s[self.pos] == ')':
            self.pos += 1
            return
        
        if (self.s[self.pos] == 'a' and
            self.s[self.pos+1] == 's' and
            self.s[self.pos+2] in whitespace):
            self.getName()
            self.getName()
            self.getMore(parenList=parenList)
            return
        elif self.s[self.pos] != ',':
            return
        else:
            self.pos += 1
            self.consumeWhitespace()
            if parenList and self.s[self.pos] == ')':
                self.pos += 1
                return # Handles trailing comma inside parenthesis
            self.setFlag(self.getName())
            self.getMore(parenList=parenList)

    def setFlag(self, feature):
        if feature == "division":
            self.flags |= CO_FUTURE_DIVISION
        elif feature == "generators":
            self.flags |= CO_GENERATOR_ALLOWED
        elif feature == "with_statement":
            self.flags |= CO_FUTURE_WITH_STATEMENT

