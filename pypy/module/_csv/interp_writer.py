from rpython.rlib.rutf8 import Utf8StringIterator, Utf8StringBuilder
from rpython.rlib import objectmodel
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, interp2app
from pypy.interpreter.typedef import interp_attrproperty_w
from pypy.module._csv.interp_csv import _build_dialect, NOT_SET
from pypy.module._csv.interp_csv import (QUOTE_STRINGS, QUOTE_ALL, QUOTE_NOTNULL,
                                         QUOTE_NONNUMERIC, QUOTE_NONE)


class W_Writer(W_Root):
    def __init__(self, space, dialect, w_fileobj):
        self.space = space
        self.dialect = dialect
        self.w_filewrite = space.getattr(w_fileobj, space.newtext('write'))
        # precompute this
        special = [dialect.delimiter, ord('\r'), ord('\n')]
        for c in Utf8StringIterator(dialect.lineterminator):
            special.append(c)
        if dialect.escapechar != 0:
            special.append(dialect.escapechar)
        if dialect.quotechar != 0:
            special.append(dialect.quotechar)
        self.special_characters = special

    @objectmodel.dont_inline
    def error(self, msg):
        space = self.space
        w_module = space.getbuiltinmodule('_csv')
        w_error = space.getattr(w_module, space.newtext('Error'))
        return OperationError(w_error, space.newtext(msg))

    def field_needs_quoting(self, field, quoted):
        # First pass over the field data (CPython's join_append_data called
        # with copy_phase=0): decide whether the field must be quoted.  This
        # has to happen before the opening quote is written, because a special
        # character anywhere in the field can force quoting of the whole field.
        dialect = self.dialect
        if quoted:
            # already known to need quoting (QUOTE_ALL, QUOTE_NONNUMERIC of a
            # non-number, ...); the scan below can only ever set quoted=True,
            # so there is nothing to discover - skip the extra pass.
            return quoted
        if dialect.quoting == QUOTE_NONE:
            return quoted
        special_characters = self.special_characters
        for c in Utf8StringIterator(field):
            if c in special_characters:
                if c == dialect.quotechar:
                    if not dialect.doublequote:
                        continue    # want_escape, does not force quoting
                elif c == dialect.escapechar:
                    continue        # want_escape, does not force quoting
                quoted = True
                break
        return quoted

    def writerow(self, w_fields):
        """Construct and write a CSV record from a sequence of fields.
        Non-string elements will be converted to string."""
        space = self.space
        try:
            fields_w = space.listview(w_fields)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                raise self.error("iterable expected, not %s" % space.repr(w_fields))
            raise e
            
        dialect = self.dialect
        rec = Utf8StringBuilder(80)
        # remember whether the last field was None, for the single empty
        # field record check below (CPython's null_field)
        null_field = False
        #
        for field_index in range(len(fields_w)):
            w_field = fields_w[field_index]
            if dialect.quoting == QUOTE_NONNUMERIC:
                quoted = not space.is_number_w(w_field)
            elif dialect.quoting == QUOTE_ALL:
                quoted = True
            elif dialect.quoting == QUOTE_STRINGS:
                quoted = space.isinstance_w(w_field, space.w_text)
            elif dialect.quoting == QUOTE_NOTNULL:
                quoted = not space.is_none(w_field)
            else:
                quoted = False
            null_field = space.is_w(w_field, space.w_None)
            if null_field:
                field = ""
                length = 0
            elif space.isinstance_w(w_field, space.w_float):
                field, length = space.utf8_len_w(space.repr(w_field))
            else:
                field, length = space.utf8_len_w(space.str(w_field))
            #
            if len(field) == 0:
                if dialect.delimiter == ord(' ') and dialect.skipinitialspace:
                    if (dialect.quoting == QUOTE_NONE or
                            (null_field and dialect.quoting in
                                 (QUOTE_STRINGS, QUOTE_NOTNULL))):
                        raise self.error(
                             "empty field must be quoted if delimiter is a space "
                             "and skipinitialspace is true")
                    quoted = True

            # Decide whether the field must be quoted before writing the
            # opening quote: a special character anywhere in the field forces
            # quoting (CPython does this in join_append_data's copy_phase=0).
            quoted = self.field_needs_quoting(field, quoted)

            # If this is not the first field we need a field separator
            if field_index > 0:
                rec.append_code(dialect.delimiter)

            # Handle preceding quote
            if quoted:
                rec.append_code(dialect.quotechar)

            # Copy/count field data
            # If field is null just pass over
            special_characters = self.special_characters
            for c in Utf8StringIterator(field):
                want_escape = False
                if c in special_characters:
                    if dialect.quoting == QUOTE_NONE:
                        want_escape = True
                    else:
                        if c == dialect.quotechar:
                            if dialect.doublequote:
                                rec.append_code(dialect.quotechar)
                            else:
                                want_escape = True
                        elif c == dialect.escapechar:
                            want_escape = True
                        if not want_escape:
                            quoted = True
                    if want_escape:
                        if dialect.escapechar == NOT_SET:
                            raise self.error("need to escape, "
                                             "but no escapechar set")
                        rec.append_code(dialect.escapechar)
                # Copy field character into record buffer
                rec.append_code(c)

            # Handle final quote
            if quoted:
                rec.append_code(dialect.quotechar)

        # If the record consists of a single empty field, it must be quoted
        # (CPython csv_writerow); otherwise it would be indistinguishable from
        # an empty record.
        if len(fields_w) > 0 and rec.getlength() == 0:
            if (dialect.quoting == QUOTE_NONE or
                    (null_field and dialect.quoting in
                         (QUOTE_STRINGS, QUOTE_NOTNULL))):
                raise self.error("single empty field record must be quoted")
            rec.append_code(dialect.quotechar)
            rec.append_code(dialect.quotechar)

        # Add line terminator
        rec.append(dialect.lineterminator)

        line = rec.build()
        return space.call_function(self.w_filewrite, space.newutf8(line, rec.getlength()))

    def writerows(self, w_seqseq):
        """Construct and write a series of sequences to a csv file.
        Non-string elements will be converted to string."""
        space = self.space
        w_iter = space.iter(w_seqseq)
        while True:
            try:
                w_seq = space.next(w_iter)
            except OperationError as e:
                if e.match(space, space.w_StopIteration):
                    break
                raise
            self.writerow(w_seq)


def csv_writer(space, w_fileobj, w_dialect=None,
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
    csv_writer = csv.writer(fileobj [, dialect='excel']
                            [optional keyword args])
    for row in sequence:
        csv_writer.writerow(row)

    [or]

    csv_writer = csv.writer(fileobj [, dialect='excel']
                            [optional keyword args])
    csv_writer.writerows(rows)

    The \"fileobj\" argument can be any object that supports the file API."""
    dialect = _build_dialect(space, w_dialect, w_delimiter, w_doublequote,
                             w_escapechar, w_lineterminator, w_quotechar,
                             w_quoting, w_skipinitialspace, w_strict)
    return W_Writer(space, dialect, w_fileobj)

W_Writer.typedef = TypeDef(
        '_csv.writer',
        dialect = interp_attrproperty_w('dialect', W_Writer),
        writerow = interp2app(W_Writer.writerow),
        writerows = interp2app(W_Writer.writerows),
        __doc__ = """CSV writer

Writer objects are responsible for generating tabular data
in CSV format from sequence input.""")
W_Writer.typedef.acceptable_as_base_class = False
