from rpython.rlib.unicodedata.dawg import encode_varint_unsigned, decode_varint_unsigned

def encode_positions(l, firstlineno):
    # l is a list of four-tuples (lineno, end_lineno, col_offset,
    # end_col_offset) coming out of the AST nodes

    # this is really inefficient for now. we can always change it though

    # three formats:
    # (1) 0:
    #     no info at all
    # (2) varint lineno_delta:
    #     just a line number no further info, the lineno_delta is 1 too big and
    #     is relative to co_firstlineno
    # (3) varint lineno_delta, char col_offset char end_col_offset, char end_lineno_delta
    #     full info, col_offset and end_col_offset are 1 too big to distinguish
    #     from case (2)


    # XXX clarify what missing values are, 0 or -1?
    # XXX what about missing lineno?
    table = []
    for position_info in l:
        lineno, end_lineno, col_offset, end_col_offset = position_info
        if lineno == -1:
            table.append(chr(0))
            continue # case (1)
        lineno_delta = lineno - firstlineno + 1
        end_line_delta = end_lineno - lineno
        # encode lineno_delta as a varsized int
        encode_varint_unsigned(lineno_delta, table)

        # the rest gets one byte each (or a single 0 for 'everything invalid')
        if (
            col_offset >= 255
            or end_col_offset >= 255
            or col_offset == -1
            or end_col_offset == -1
            or end_line_delta < 0
            or end_line_delta > 255
        ):
            #
            table.append(chr(0))
        else:
            table.append(chr(col_offset + 1))
            table.append(chr(end_col_offset + 1))
            table.append(chr(end_line_delta))


    return ''.join(table)

def _decode_entry(table, firstlineno, position):
    lineno, position = decode_varint_unsigned(table, position)
    if lineno == 0:
        return (-1, -1, -1, -1, position)
    lineno -= 1
    lineno += firstlineno
    col_offset = ord(table[position]) - 1
    position += 1
    if col_offset == -1: # was a single 0, no more bytes
        end_col_offset = -1
        end_lineno = -1
    else:
        end_col_offset = ord(table[position]) - 1
        end_line_delta = ord(table[position + 1])
        position += 2
        end_lineno = lineno + end_line_delta
    return lineno, end_lineno, col_offset, end_col_offset, position


def decode_positions(table, firstlineno):
    res = []
    position = 0
    while position < len(table):
        lineno, end_lineno, col_offset, end_col_offset, position = _decode_entry(table, firstlineno, position)
        res.append((lineno, end_lineno, col_offset, end_col_offset))
    return res

def offset2lineno(c, stopat):
    return _offset2lineno(c.co_linetable, c.co_firstlineno, stopat // 2)

def _offset2lineno(linetable, firstlineno, stopat):
    position = 0
    for i in range(stopat + 1):
        tup = _decode_entry(linetable, firstlineno, position)
        position = tup[4]
        if i == stopat:
            return tup[0]


# converting back to lnotab

def _encode_lnotab_pair(addr, line, table):
    while addr > 255:
        table.append(chr(255))
        table.append(chr(0))
        addr -= 255
    while line < -128:
        table.append(chr(addr))
        table.append(chr(-128 + 256))
        line += 128
        addr = 0
    while line > 127:
        table.append(chr(addr))
        table.append(chr(127))
        line -= 127
        addr = 0
    table.append(chr(addr))

    # store as signed char
    assert -128 <= line <= 127
    if line < 0:
        line += 256
    table.append(chr(line))

def linetable2lnotab(linetable, firstlineno):
    position = 0
    res = []
    line = firstlineno
    start_pc = pc = 0
    while position < len(linetable):
        lineno, _, _, _, position = _decode_entry(linetable, firstlineno, position)
        if lineno != line:
            bdelta = pc - start_pc
            ldelta = lineno - line
            _encode_lnotab_pair(bdelta, ldelta, res)
            line = lineno
            start_pc = pc
        pc += 2
    return b"".join(res)



