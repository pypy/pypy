from pypy.interpreter.error import OperationError
from pypy.interpreter.pyparser import future, parser, pytokenizer, pygram, error
from pypy.interpreter.astcompiler import consts

def recode_to_utf8(space, bytes, encoding):
    w_text = space.call_method(space.newbytes(bytes), "decode",
                               space.newtext(encoding))
    if not space.isinstance_w(w_text, space.w_unicode):
        raise error.SyntaxError("codec did not return a unicode object")
    w_recoded = space.call_method(w_text, "encode", space.newtext("utf-8"))
    return space.bytes_w(w_recoded)

def _normalize_encoding(encoding):
    """returns normalized name for <encoding>

    see dist/src/Parser/tokenizer.c 'get_normal_name()'
    for implementation details / reference

    NOTE: for now, parser.suite() raises a MemoryError when
          a bad encoding is used. (SF bug #979739)
    """
    if encoding is None:
        return None
    # lower() + '_' / '-' conversion
    encoding = encoding.replace('_', '-').lower()
    if encoding == 'utf-8' or encoding.startswith('utf-8-'):
        return 'utf-8'
    for variant in ['latin-1', 'iso-latin-1', 'iso-8859-1']:
        if (encoding == variant or
            encoding.startswith(variant + '-')):
            return 'iso-8859-1'
    return encoding

def _check_for_encoding(s):
    eol = s.find('\n')
    if eol < 0:
        return _check_line_for_encoding(s)[0]
    enc, again = _check_line_for_encoding(s[:eol])
    if enc or not again:
        return enc
    eol2 = s.find('\n', eol + 1)
    if eol2 < 0:
        return _check_line_for_encoding(s[eol + 1:])[0]
    return _check_line_for_encoding(s[eol + 1:eol2])[0]


def _check_line_for_encoding(line):
    """returns the declared encoding or None"""
    i = 0
    for i in range(len(line)):
        if line[i] == '#':
            break
        if line[i] not in ' \t\014':
            return None, False  # Not a comment, don't read the second line.
    return pytokenizer.match_encoding_declaration(line[i:]), True


class CompileInfo(object):
    """Stores information about the source being compiled.

    * filename: The filename of the source.
    * mode: The parse mode to use. ('exec', 'eval', or 'single')
    * flags: Parser and compiler flags.
    * encoding: The source encoding.
    * last_future_import: The line number and offset of the last __future__
      import.
    * hidden_applevel: Will this code unit and sub units be hidden at the
      applevel?
    """

    def __init__(self, filename, mode="exec", flags=0, future_pos=(0, 0),
                 hidden_applevel=False):
        self.filename = filename
        self.mode = mode
        self.encoding = None
        self.flags = flags
        self.last_future_import = future_pos
        self.hidden_applevel = hidden_applevel


_targets = {
'eval' : pygram.syms.eval_input,
'single' : pygram.syms.single_input,
'exec' : pygram.syms.file_input,
}

class PythonParser(parser.Parser):

    def __init__(self, space, future_flags=future.futureFlags_2_7,
                 grammar=pygram.python_grammar):
        parser.Parser.__init__(self, grammar)
        self.space = space
        self.future_flags = future_flags

    def parse_source(self, textsrc, compile_info):
        """Main entry point for parsing Python source.

        Everything from decoding the source to tokenizing to building the parse
        tree is handled here.
        """
        # Detect source encoding.
        enc = None
        if textsrc.startswith("\xEF\xBB\xBF"):
            textsrc = textsrc[3:]
            enc = 'utf-8'
            # If an encoding is explicitly given check that it is utf-8.
            decl_enc = _check_for_encoding(textsrc)
            if decl_enc and decl_enc != "utf-8":
                raise error.SyntaxError("UTF-8 BOM with %s coding cookie" % decl_enc,
                                        filename=compile_info.filename)
        elif compile_info.flags & consts.PyCF_SOURCE_IS_UTF8:
            enc = 'utf-8'
            if _check_for_encoding(textsrc) is not None:
                raise error.SyntaxError("coding declaration in unicode string",
                                        filename=compile_info.filename)
        else:
            enc = _normalize_encoding(_check_for_encoding(textsrc))
            if enc is not None and enc not in ('utf-8', 'iso-8859-1'):
                try:
                    textsrc = recode_to_utf8(self.space, textsrc, enc)
                except OperationError as e:
                    # if the codec is not found, LookupError is raised.  we
                    # check using 'is_w' not to mask potential IndexError or
                    # KeyError
                    space = self.space
                    if e.match(space, space.w_LookupError):
                        raise error.SyntaxError("Unknown encoding: %s" % enc,
                                                filename=compile_info.filename)
                    # Transform unicode errors into SyntaxError
                    if e.match(space, space.w_UnicodeDecodeError):
                        e.normalize_exception(space)
                        w_message = space.str(e.get_w_value(space))
                        raise error.SyntaxError(space.text_w(w_message))
                    raise

        flags = compile_info.flags

        # The tokenizer is very picky about how it wants its input.
        source_lines = textsrc.splitlines(True)
        if source_lines and not source_lines[-1].endswith("\n"):
            source_lines[-1] += '\n'
        if textsrc and textsrc[-1] == "\n":
            flags &= ~consts.PyCF_DONT_IMPLY_DEDENT

        self.prepare(_targets[compile_info.mode])
        tp = 0
        try:
            try:
                # Note: we no longer pass the CO_FUTURE_* to the tokenizer,
                # which is expected to work independently of them.  It's
                # certainly the case for all futures in Python <= 2.7.
                tokens = pytokenizer.generate_tokens(source_lines, flags)

                newflags, last_future_import = (
                    future.add_future_flags(self.future_flags, tokens))
                compile_info.last_future_import = last_future_import
                compile_info.flags |= newflags

                if compile_info.flags & consts.CO_FUTURE_PRINT_FUNCTION:
                    self.grammar = pygram.python_grammar_no_print
                else:
                    self.grammar = pygram.python_grammar

                for tp, value, lineno, column, line in tokens:
                    if self.add_token(tp, value, lineno, column, line):
                        break
            except error.TokenError as e:
                e.filename = compile_info.filename
                raise
            except parser.ParseError as e:
                # Catch parse errors, pretty them up and reraise them as a
                # SyntaxError.
                new_err = error.IndentationError
                if tp == pygram.tokens.INDENT:
                    msg = "unexpected indent"
                elif e.expected == pygram.tokens.INDENT:
                    msg = "expected an indented block"
                else:
                    new_err = error.SyntaxError
                    msg = "invalid syntax"
                raise new_err(msg, e.lineno, e.column, e.line,
                              compile_info.filename)
            else:
                tree = self.root
        finally:
            # Avoid hanging onto the tree.
            self.root = None
        if enc is not None:
            compile_info.encoding = enc
        return tree
