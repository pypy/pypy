from pypy.rlib.rstring import StringBuilder
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.interpreter.typedef import interp_attrproperty_w, interp_attrproperty
from pypy.module._csv.interp_csv import _build_dialect
from pypy.module._csv.interp_csv import (QUOTE_MINIMAL, QUOTE_ALL,
                                         QUOTE_NONNUMERIC, QUOTE_NONE)

(START_RECORD, START_FIELD, ESCAPED_CHAR, IN_FIELD,
 IN_QUOTED_FIELD, ESCAPE_IN_QUOTED_FIELD, QUOTE_IN_QUOTED_FIELD,
 EAT_CRNL) = range(8)


class W_Reader(Wrappable):

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

    def save_field(self, field_builder):
        field = field_builder.build()
        if self.numeric_field:
            from pypy.objspace.std.strutil import ParseStringError
            from pypy.objspace.std.strutil import string_to_float
            self.numeric_field = False
            try:
                ff = string_to_float(field)
            except ParseStringError, e:
                raise OperationError(self.space.w_ValueError,
                                     self.space.wrap(e.msg))
            w_obj = self.space.wrap(ff)
        else:
            w_obj = self.space.wrap(field)
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
                    if field_builder is not None:
                        raise self.error("newline inside string")
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
                        field_builder.append(c)
                        state = IN_FIELD

                elif state == ESCAPED_CHAR:
                    field_builder.append(c)
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
                        field_builder.append(c)

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
                        field_builder.append(c)

                elif state == ESCAPE_IN_QUOTED_FIELD:
                    field_builder.append(c)
                    state = IN_QUOTED_FIELD

                elif state == QUOTE_IN_QUOTED_FIELD:
                    # doublequote - seen a quote in an quoted field
                    if (dialect.quoting != QUOTE_NONE and
                            c == dialect.quotechar):
                        # save "" as "
                        field_builder.append(c)
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
                        field_builder.append(c)
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

            if (state == START_FIELD or
                  state == IN_FIELD or
                  state == QUOTE_IN_QUOTED_FIELD):
                self.save_field(field_builder)
                break
            elif state == ESCAPED_CHAR:
                field_builder.append('\n')
                state = IN_FIELD
            elif state == IN_QUOTED_FIELD:
                pass
            elif state == ESCAPE_IN_QUOTED_FIELD:
                field_builder.append('\n')
                state = IN_QUOTED_FIELD
            else:
                break
        #
        w_result = space.newlist(self.fields_w)
        self.fields_w = None
        return w_result


def csv_reader(space, w_iterator, w_dialect=NoneNotWrapped,
                  w_delimiter        = NoneNotWrapped,
                  w_doublequote      = NoneNotWrapped,
                  w_escapechar       = NoneNotWrapped,
                  w_lineterminator   = NoneNotWrapped,
                  w_quotechar        = NoneNotWrapped,
                  w_quoting          = NoneNotWrapped,
                  w_skipinitialspace = NoneNotWrapped,
                  w_strict           = NoneNotWrapped,
                  ):
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
