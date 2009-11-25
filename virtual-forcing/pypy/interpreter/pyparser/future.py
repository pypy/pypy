"""
This automaton is designed to be invoked on a Python source string
before the real parser starts working, in order to find all legal
'from __future__ import blah'. As soon as something is encountered that
would prevent more future imports, the analysis is aborted.
The resulting legal futures are avaliable in self.flags after the
pass has ended.

Invocation is through get_futures(src), which returns a field of flags, one per
found correct future import.

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
            
def get_futures(future_flags, source):
    futures = FutureAutomaton(future_flags, source)
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
    
    def __init__(self, future_flags, string):
        self.future_flags = future_flags
        self.s = string
        self.pos = 0
        self.current_lineno = 1
        self.lineno = -1
        self.line_start_pos = 0
        self.col_offset = 0
        self.docstring_consumed = False
        self.flags = 0
        self.got_features = 0

    def getc(self, offset=0):
        try:
            return self.s[self.pos + offset]
        except IndexError:
            raise DoneException

    def start(self):
        c = self.getc()
        if c in ["'", '"'] and not self.docstring_consumed:
            self.consume_docstring()
        elif c in whitespace_or_newline:
            self.consume_empty_line()
        elif c == '#':
            self.consume_comment()
        elif c == 'f':
            self.consume_from()
        else:
            return

    def atbol(self):
        self.current_lineno += 1
        self.line_start_pos = self.pos

    def consume_docstring(self):
        self.docstring_consumed = True
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
                            self.consume_empty_line()
                            break

        else: # Deal with a single quoted docstring
            self.pos += 1
            while 1:
                c = self.getc()
                self.pos += 1
                if c == endchar:
                    self.consume_empty_line()
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

    def consume_empty_line(self):
        """
        Called when the remainder of the line can only contain whitespace
        and comments.
        """
        while self.getc() in whitespace:
            self.pos += 1
        if self.getc() == '#':
            self.consume_comment()
        elif self.getc() == ';':
            self.pos += 1
            self.consume_whitespace()
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

    def consume_comment(self):
        self.pos += 1
        while self.getc() not in '\r\n':
            self.pos += 1
        self.consume_empty_line()

    def consume_from(self):
        col_offset = self.pos - self.line_start_pos
        line = self.current_lineno
        self.pos += 1
        if self.getc() == 'r' and self.getc(+1) == 'o' and self.getc(+2) == 'm':
            self.docstring_consumed = True
            self.pos += 3
            self.consume_mandatory_whitespace()
            if self.s[self.pos:self.pos+10] != '__future__':
                raise DoneException
            self.pos += 10
            self.consume_mandatory_whitespace()
            if self.s[self.pos:self.pos+6] != 'import':
                raise DoneException
            self.pos += 6
            self.consume_whitespace()
            old_got = self.got_features
            try:
                if self.getc() == '(':
                    self.pos += 1
                    self.consume_whitespace()
                    self.set_flag(self.get_name())
                    # Set flag corresponding to name
                    self.get_more(paren_list=True)
                else:
                    self.set_flag(self.get_name())
                    self.get_more()
            finally:
                if self.got_features > old_got:
                    self.col_offset = col_offset
                    self.lineno = line
            self.consume_empty_line()

    def consume_mandatory_whitespace(self):
        if self.getc() not in whitespace + '\\':
            raise DoneException
        self.consume_whitespace()
        
    def consume_whitespace(self):
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

    def get_name(self):
        if self.getc() not in letters:
            raise DoneException
        p = self.pos
        try:
            while self.getc() in alphanumerics:
                self.pos += 1
        except DoneException:
            # If there's any name at all, we want to call self.set_flag().
            # Something else while get the DoneException again.
            if self.pos == p:
                raise
            end = self.pos
        else:
            end = self.pos
            self.consume_whitespace()
        return self.s[p:end]

    def get_more(self, paren_list=False):
        if paren_list and self.getc() == ')':
            self.pos += 1
            return
        
        if (self.getc() == 'a' and
            self.getc(+1) == 's' and
            self.getc(+2) in whitespace):
            self.get_name()
            self.get_name()
            self.get_more(paren_list=paren_list)
            return
        elif self.getc() != ',':
            return
        else:
            self.pos += 1
            self.consume_whitespace()
            if paren_list and self.getc() == ')':
                self.pos += 1
                return # Handles trailing comma inside parenthesis
            self.set_flag(self.get_name())
            self.get_more(paren_list=paren_list)

    def set_flag(self, feature):
        self.got_features += 1
        try:
            self.flags |= self.future_flags.compiler_features[feature]
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
