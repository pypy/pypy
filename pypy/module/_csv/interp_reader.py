from rpython.rlib.rstring import StringBuilder
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.interpreter.typedef import interp_attrproperty_w, interp_attrproperty
from pypy.module._csv.interp_csv import _build_dialect
from pypy.module._csv.interp_csv import (QUOTE_MINIMAL, QUOTE_ALL,
                                         QUOTE_NONNUMERIC, QUOTE_NONE)

(START_RECORD, START_FIELD, ESCAPED_CHAR, IN_FIELD,
 IN_QUOTED_FIELD, ESCAPE_IN_QUOTED_FIELD, QUOTE_IN_QUOTED_FIELD,
 EAT_CRNL) = range(8)


class W_Reader(W_Root):

    def __init__(self, space, dialect, w_iter):
        self.space = space
        self.dialect = dialect
        self.w_iter = w_iter
        self.line_num = 0

    def iter_w(self):
        return self.space.wrap(self)

    def error(self, msg):
        space = self.space
        msg = 'line %d: %s' % (self.line_num, msg)
        w_module = space.getbuiltinmodule('_csv')
        w_error = space.getattr(w_module, space.wrap('Error'))
        raise OperationError(w_error, space.wrap(msg))
    error._dont_inline_ = True

    def add_char(self, field_builder, c):
        assert field_builder is not None
        if field_builder.getlength() >= field_limit.limit:
            raise self.error("field larger than field limit")
        field_builder.append(c)

    def save_field(self, field_builder):
        space = self.space
        field = field_builder.build()
        if self.numeric_field:
            from rpython.rlib.rstring import ParseStringError
            from rpython.rlib.rfloat import string_to_float
            self.numeric_field = False
            try:
                ff = string_to_float(field)
            except ParseStringError as e:
                from pypy.objspace.std.inttype import wrap_parsestringerror
                raise wrap_parsestringerror(space, e, space.wrap(field))
            w_obj = space.wrap(ff)
        else:
            w_obj = space.wrap(field)
        self.fields_w.append(w_obj)

    def next_w(self):
        space = self.space
        dialect = self.dialect
        self.fields_w = []
        self.numeric_field = False
        field_builder = None  # valid iff state not in [START_RECORD, EAT_CRNL]
        state = START_RECORD
        #
        while True:
            try:
                w_line = space.next(self.w_iter)
            except OperationError, e:
                if e.match(space, space.w_StopIteration):
                    if (field_builder is not None and
                            state != START_RECORD and state != EAT_CRNL and
                            (len(field_builder.build()) > 0 or
                             state == IN_QUOTED_FIELD)):
                        if dialect.strict:
                            raise self.error("newline inside string")
                        else:
                            self.save_field(field_builder)
                            break
                raise
            self.line_num += 1
            line = space.str_w(w_line)
            for c in line:
                if c == '\0':
                    raise self.error("line contains NULL byte")

                if state == START_RECORD:
                    if c == '\n' or c == '\r':
                        state = EAT_CRNL
                        continue
                    # normal character - handle as START_FIELD
                    state = START_FIELD
                    # fall-through to the next case

                if state == START_FIELD:
                    field_builder = StringBuilder(64)
                    # expecting field
                    if c == '\n' or c == '\r':
                        # save empty field
                        self.save_field(field_builder)
                        state = EAT_CRNL
                    elif (c == dialect.quotechar and
                              dialect.quoting != QUOTE_NONE):
                        # start quoted field
                        state = IN_QUOTED_FIELD
                    elif c == dialect.escapechar:
                        # possible escaped character
                        state = ESCAPED_CHAR
                    elif c == ' ' and dialect.skipinitialspace:
                        # ignore space at start of field
                        pass
                    elif c == dialect.delimiter:
                        # save empty field
                        self.save_field(field_builder)
                    else:
                        # begin new unquoted field
                        if dialect.quoting == QUOTE_NONNUMERIC:
                            self.numeric_field = True
                        self.add_char(field_builder, c)
                        state = IN_FIELD

                elif state == ESCAPED_CHAR:
                    self.add_char(field_builder, c)
                    state = IN_FIELD

                elif state == IN_FIELD:
                    # in unquoted field
                    if c == '\n' or c == '\r':
                        # end of line
                        self.save_field(field_builder)
                        state = EAT_CRNL
                    elif c == dialect.escapechar:
                        # possible escaped character
                        state = ESCAPED_CHAR
                    elif c == dialect.delimiter:
                        # save field - wait for new field
                        self.save_field(field_builder)
                        state = START_FIELD
                    else:
                        # normal character - save in field
                        self.add_char(field_builder, c)

                elif state == IN_QUOTED_FIELD:
                    # in quoted field
                    if c == dialect.escapechar:
                        # Possible escape character
                        state = ESCAPE_IN_QUOTED_FIELD
                    elif (c == dialect.quotechar and
                              dialect.quoting != QUOTE_NONE):
                        if dialect.doublequote:
                            # doublequote; " represented by ""
                            state = QUOTE_IN_QUOTED_FIELD
                        else:
                            # end of quote part of field
                            state = IN_FIELD
                    else:
                        # normal character - save in field
                        self.add_char(field_builder, c)

                elif state == ESCAPE_IN_QUOTED_FIELD:
                    self.add_char(field_builder, c)
                    state = IN_QUOTED_FIELD

                elif state == QUOTE_IN_QUOTED_FIELD:
                    # doublequote - seen a quote in an quoted field
                    if (dialect.quoting != QUOTE_NONE and
                            c == dialect.quotechar):
                        # save "" as "
                        self.add_char(field_builder, c)
                        state = IN_QUOTED_FIELD
                    elif c == dialect.delimiter:
                        # save field - wait for new field
                        self.save_field(field_builder)
                        state = START_FIELD
                    elif c == '\n' or c == '\r':
                        # end of line
                        self.save_field(field_builder)
                        state = EAT_CRNL
                    elif not dialect.strict:
                        self.add_char(field_builder, c)
                        state = IN_FIELD
                    else:
                        # illegal
                        raise self.error("'%s' expected after '%s'" % (
                            dialect.delimiter, dialect.quotechar))

                elif state == EAT_CRNL:
                    if not (c == '\n' or c == '\r'):
                        raise self.error("new-line character seen in unquoted "
                                        "field - do you need to open the file "
                                        "in universal-newline mode?")

            if state == IN_FIELD or state == QUOTE_IN_QUOTED_FIELD:
                self.save_field(field_builder)
                break
            elif state == ESCAPED_CHAR:
                self.add_char(field_builder, '\n')
                state = IN_FIELD
            elif state == IN_QUOTED_FIELD:
                pass
            elif state == ESCAPE_IN_QUOTED_FIELD:
                self.add_char(field_builder, '\n')
                state = IN_QUOTED_FIELD
            elif state == START_FIELD:
                # save empty field
                field_builder = StringBuilder(1)
                self.save_field(field_builder)
                break
            else:
                break
        #
        w_result = space.newlist(self.fields_w)
        self.fields_w = None
        return w_result


def csv_reader(space, w_iterator, w_dialect=None,
                  w_delimiter        = None,
                  w_doublequote      = None,
                  w_escapechar       = None,
                  w_lineterminator   = None,
                  w_quotechar        = None,
                  w_quoting          = None,
                  w_skipinitialspace = None,
                  w_strict           = None,
                  ):
    """
    csv_reader = reader(iterable [, dialect='excel']
                       [optional keyword args])
    for row in csv_reader:
        process(row)

    The "iterable" argument can be any object that returns a line
    of input for each iteration, such as a file object or a list.  The
    optional \"dialect\" parameter is discussed below.  The function
    also accepts optional keyword arguments which override settings
    provided by the dialect.

    The returned object is an iterator.  Each iteration returns a row
    of the CSV file (which can span multiple input lines)"""
    w_iter = space.iter(w_iterator)
    dialect = _build_dialect(space, w_dialect, w_delimiter, w_doublequote,
                             w_escapechar, w_lineterminator, w_quotechar,
                             w_quoting, w_skipinitialspace, w_strict)
    return W_Reader(space, dialect, w_iter)

W_Reader.typedef = TypeDef(
        'reader',
        __module__ = '_csv',
        dialect = interp_attrproperty_w('dialect', W_Reader),
        line_num = interp_attrproperty('line_num', W_Reader),
        __iter__ = interp2app(W_Reader.iter_w),
        next = interp2app(W_Reader.next_w),
        __doc__ = """CSV reader

Reader objects are responsible for reading and parsing tabular data
in CSV format.""")
W_Reader.typedef.acceptable_as_base_class = False

# ____________________________________________________________

class FieldLimit:
    limit = 128 * 1024   # max parsed field size
field_limit = FieldLimit()

@unwrap_spec(new_limit=int)
def csv_field_size_limit(space, new_limit=-1):
    old_limit = field_limit.limit
    if new_limit >= 0:
        field_limit.limit = new_limit
    return space.wrap(old_limit)
