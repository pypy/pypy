from pypy.interpreter.unicodehelper import _str_decode_utf8_slowpath

def wrap_pos(space, num):
    if num <= 0:
        return space.w_None
    return space.newint(num)

def replace_error_handler(errors, encoding, msg, s, startpos, endpos):
    return b'\xef\xbf\xbd', endpos, 'b', s

def _adjust_offset(offset, text, unilength):
    if offset > len(text):
        offset = unilength
    elif offset >= 1:
        offset = offset - 1 # 1-based to 0-based
        assert offset >= 0
        # slightly inefficient, call the decoder for text[:offset] too
        _, offset, _ = _str_decode_utf8_slowpath(
                text[:offset], 'replace', False, replace_error_handler,
                True)
        offset += 1 # convert to 1-based
    else:
        offset = 0
    return offset

class SyntaxError(Exception):
    """Base class for exceptions raised by the parser."""

    def __init__(self, msg, lineno=0, offset=0, text=None, filename=None,
                 end_lineno=0, end_offset=0):
        self.msg = msg
        self.lineno = lineno
        # NB: offset and end_offset are 1-based indexes into the bytes source
        self.offset = offset
        self.text = text
        self.filename = filename
        self.end_lineno = end_lineno
        self.end_offset = end_offset

    @staticmethod
    def fromast(msg, node, filename=None):
        return SyntaxError(msg, node.lineno, node.col_offset + 1,
                           filename=filename,
                           end_lineno=node.end_lineno,
                           end_offset=node.end_col_offset + 1)

    def find_sourceline_and_wrap_info(self, space, source=None, filename=None):
        """ search for the line of input that caused the error and then return
        a wrapped tuple that can be used to construct a wrapped SyntaxError.
        Optionally pass source, to get better error messages for the case where
        this instance was constructed without a source line (.text
        attribute)"""
        text = self.text
        if text is None and source is not None and self.lineno:
            lines = source.splitlines(True)
            text = lines[self.lineno - 1]
        w_text = w_filename = space.w_None
        w_lineno = space.newint(self.lineno)
        if filename is None:
            filename = self.filename
        if filename is not None:
            w_filename = space.newfilename(filename)
            if text is None:
                w_text = space.appexec([w_filename, w_lineno],
                    """(filename, lineno):
                    try:
                        with open(filename) as f:
                            for _ in range(lineno - 1):
                                f.readline()
                            return f.readline()
                    except:  # we can't allow any exceptions here!
                        return None""")
        offset = self.offset
        end_offset = self.end_offset
        if text is not None:
            # text may not be UTF-8 in case of decoding errors.
            # adjust the encoded text offset to a decoded offset
            # XXX do the right thing about continuation lines, which
            # XXX are their own fun, sometimes giving offset >
            # XXX len(text) for example (right now, avoid crashing)

            # this also converts the byte-based self.offset to a
            # codepoint-based index into the decoded unicode-version of
            # self.text

            replacedtext, unilength, _ = _str_decode_utf8_slowpath(
                    text, 'replace', False, replace_error_handler, True)
            offset = _adjust_offset(offset, text, unilength)
            # XXX this is wrong if end_lineno != lineno
            end_offset = _adjust_offset(end_offset, text, unilength)
            w_text = space.newutf8(replacedtext, unilength)
        return space.newtuple([
            space.newtext(self.msg),
            space.newtuple([
                w_filename, w_lineno, wrap_pos(space, offset),
                w_text, wrap_pos(space, self.end_lineno),
                wrap_pos(space, end_offset)])])

    def __str__(self):
        return "%s at pos (%d, %d) in %r" % (
            self.__class__.__name__, self.lineno, self.offset, self.text)

class IndentationError(SyntaxError):
    pass

class TabError(IndentationError):
    def __init__(self, lineno=0, offset=0, text=None, filename=None,
                 end_lineno=0, end_offset=0):
        msg = "inconsistent use of tabs and spaces in indentation"
        IndentationError.__init__(
            self, msg, lineno, offset, text, filename, end_lineno, end_offset)

class ASTError(Exception):
    def __init__(self, msg, ast_node):
        self.msg = msg
        self.ast_node = ast_node


class TokenError(SyntaxError):

    def __init__(self, msg, line, lineno, column, tokens, end_lineno=0, end_offset=0):
        SyntaxError.__init__(self, msg, lineno, column, line,
                             end_lineno=end_lineno, end_offset=end_offset)
        self.tokens = tokens

class TokenIndentationError(IndentationError):

    def __init__(self, msg, line, lineno, column, tokens):
        SyntaxError.__init__(self, msg, lineno, column, line)
        self.tokens = tokens
