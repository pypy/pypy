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
    CO_FUTURE_DIVISION, CO_FUTURE_WITH_STATEMENT, CO_FUTURE_ABSOLUTE_IMPORT
            
def getFutures(futureFlags, source):
    futures = FutureAutomaton(futureFlags, source)
    try:
        futures.start()
    except DoneException, e:
        pass
    return futures.flags, (futures.lineno, futures.col_offset)
    
class DoneException(Exception):
    pass

whitespace = ' \t\f'
whitespace_or_newline = whitespace + '\n\r'
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
    "division", "nested_scopes" and "with_statement", "absolute_import".
    "generators", "division" and "nested_scopes" are redundant
    in 2.5 because they are always enabled.

    This module parses the input until it encounters something that is
    not recognized as a valid future statement or something that may
    precede a future statement.
    """
    
    def __init__(self, futureFlags, string):
        self.futureFlags = futureFlags
        self.s = string
        self.pos = 0
        self.current_lineno = 1
        self.lineno = -1
        self.line_start_pos = 0
        self.col_offset = 0
        self.docstringConsumed = False
        self.flags = 0
        self.got_features = 0

    def getc(self, offset=0):
        try:
            return self.s[self.pos + offset]
        except IndexError:
            raise DoneException

    def start(self):
        c = self.getc()
        if c in ["'", '"'] and not self.docstringConsumed:
            self.consumeDocstring()
        elif c in whitespace_or_newline:
            self.consumeEmptyLine()
        elif c == '#':
            self.consumeComment()
        elif c == 'f':
            self.consumeFrom()
        else:
            return

    def atbol(self):
        self.current_lineno += 1
        self.line_start_pos = self.pos

    def consumeDocstring(self):
        self.docstringConsumed = True
        endchar = self.getc()
        if (self.getc() == self.getc(+1) and
            self.getc() == self.getc(+2)):
            self.pos += 3
            while 1: # Deal with a triple quoted docstring
                if self.getc() == '\\':
                    self.pos += 2
                else:
                    c = self.getc()
                    if c != endchar:
                        self.pos += 1
                        if c == '\n':
                            self.atbol()
                        elif c == '\r':
                            if self.getc() == '\n':
                                self.pos += 1
                                self.atbol()
                    else:
                        self.pos += 1
                        if (self.getc() == endchar and
                            self.getc(+1) == endchar):
                            self.pos += 2
                            self.consumeEmptyLine()
                            break

        else: # Deal with a single quoted docstring
            self.pos += 1
            while 1:
                c = self.getc()
                self.pos += 1
                if c == endchar:
                    self.consumeEmptyLine()
                    return
                elif c == '\\':
                    # Deal with linefeeds
                    if self.getc() != '\r':
                        self.pos += 1
                    else:
                        self.pos += 1
                        if self.getc() == '\n':
                            self.pos += 1
                elif c in '\r\n':
                    # Syntax error
                    return

    def consumeEmptyLine(self):
        """
        Called when the remainder of the line can only contain whitespace
        and comments.
        """
        while self.getc() in whitespace:
            self.pos += 1
        if self.getc() == '#':
            self.consumeComment()
        elif self.getc() == ';':
            self.pos += 1
            self.consumeWhitespace()
            self.start()
        elif self.getc() in '\r\n':
            c = self.getc()
            self.pos += 1
            if c == '\r':
                if self.getc() == '\n':
                    self.pos += 1
                    self.atbol()
            else:
                self.atbol()
            self.start()

    def consumeComment(self):
        self.pos += 1
        while self.getc() not in '\r\n':
            self.pos += 1
        self.consumeEmptyLine()

    def consumeFrom(self):
        col_offset = self.pos - self.line_start_pos
        line = self.current_lineno
        self.pos += 1
        if self.getc() == 'r' and self.getc(+1) == 'o' and self.getc(+2) == 'm':
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
            old_got = self.got_features
            try:
                if self.getc() == '(':
                    self.pos += 1
                    self.consumeWhitespace()
                    self.setFlag(self.getName())
                    # Set flag corresponding to name
                    self.getMore(parenList=True)
                else:
                    self.setFlag(self.getName())
                    self.getMore()
            finally:
                if self.got_features > old_got:
                    self.col_offset = col_offset
                    self.lineno = line
            self.consumeEmptyLine()
        else:
            return
        
    def consumeMandatoryWhitespace(self):
        if self.getc() not in whitespace + '\\':
            raise DoneException
        self.consumeWhitespace()
        
    def consumeWhitespace(self):
        while 1:
            c = self.getc()
            if c in whitespace:
                self.pos += 1
                continue
            elif c == '\\':
                self.pos += 1
                c = self.getc()
                if c == '\n':
                    self.pos += 1
                    self.atbol()
                    continue
                elif c == '\r':
                    self.pos += 1
                    if self.getc() == '\n':
                        self.pos += 1
                        self.atbol()
                else:
                    raise DoneException
            else:
                return

    def getName(self):
        if self.getc() not in letters:
            raise DoneException
        p = self.pos
        while 1:
            self.pos += 1
            if self.getc() not in alphanumerics:
                break
        name = self.s[p:self.pos]
        self.consumeWhitespace()
        return name

    def getMore(self, parenList=False):
        if parenList and self.getc() == ')':
            self.pos += 1
            return
        
        if (self.getc() == 'a' and
            self.getc(+1) == 's' and
            self.getc(+2) in whitespace):
            self.getName()
            self.getName()
            self.getMore(parenList=parenList)
            return
        elif self.getc() != ',':
            return
        else:
            self.pos += 1
            self.consumeWhitespace()
            if parenList and self.getc() == ')':
                self.pos += 1
                return # Handles trailing comma inside parenthesis
            self.setFlag(self.getName())
            self.getMore(parenList=parenList)

    def setFlag(self, feature):
        self.got_features += 1
        try:
            self.flags |= self.futureFlags.compiler_features[feature]
        except KeyError:
            pass

from codeop import PyCF_DONT_IMPLY_DEDENT
from pypy.interpreter.error import OperationError

from pypy.tool import stdlib___future__ as future

class FutureFlags(object):
    def __init__(self, version):
        compiler_flags = 0
        self.compiler_features = {}
        self.mandatory_flags = 0
        for fname in future.all_feature_names:
            feature = getattr(future, fname)
            if version >= feature.getOptionalRelease():
                flag = feature.compiler_flag
                compiler_flags |= flag
                self.compiler_features[fname] = flag
            if version >= feature.getMandatoryRelease():
                self.mandatory_flags |= feature.compiler_flag
        self.allowed_flags = compiler_flags

    def get_flag_names(self, space, flags):
        flag_names = []
        for name, value in self.compiler_features.items():
            if flags & value:
                flag_names.append(name)
        return flag_names

futureFlags_2_4 = FutureFlags((2, 4, 4, 'final', 0))
futureFlags_2_5 = FutureFlags((2, 5, 0, 'final', 0))
