from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.module._csv.interp_csv import (QUOTE_MINIMAL, QUOTE_ALL,
                                         QUOTE_NONNUMERIC, QUOTE_NONE)

(START_RECORD, START_FIELD, ESCAPED_CHAR, IN_FIELD,
 IN_QUOTED_FIELD, ESCAPE_IN_QUOTED_FIELD, QUOTE_IN_QUOTED_FIELD,
 EAT_CRNL) = range(8)


def error(space, msg):
    w_module = space.getbuiltinmodule('_csv')
    w_error = space.getattr(w_module, space.wrap('Error'))
    raise OperationError(w_error, space.wrap(msg))


class W_Reader(Wrappable):

    def __init__(self, space, dialect, w_iter):
        self.space = space
        self.dialect = dialect
        self.w_iter = w_iter
        self.line_num = 0

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        space = self.space
        dialect = self.dialect
        self.fields_w = []
        self.numeric_field = False
        field = ''
        state = START_RECORD
        #
        while True:
            try:
                w_line = space.next(self.w_iter)
            except OperationError, e:
                if e.match(space, space.w_StopIteration) and len(field) > 0:
                    raise error("newline inside string")
                raise
            self.line_num += 1
            line = space.str_w(w_line)
            for c in line:
                if state == START_RECORD:
                    if c == '\n' or c == '\r':
                        state = EAT_CRNL
                        continue
                    # normal character - handle as START_FIELD
                    state = START_FIELD
                if state == START_FIELD:
                    # expecting field
                    if c == '\n' or c == '\r':
                        # save empty field
                        assert len(field) == 0; self.save_field('')
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
                        assert len(field) == 0; self.save_field('')
                    else:
                        # begin new unquoted field
                        if dialect.quoting == QUOTE_NONNUMERIC:
                            self.numeric_field = True
                        field += .....
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
