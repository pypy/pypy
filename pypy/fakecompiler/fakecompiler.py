import parser, marshal, os, __future__

DUMPFILE = 'this_is_the_marshal_file'

def reallycompile(tuples_or_src, filename, mode, flag_names):
    if type(tuples_or_src) is str:
        flags = 0
        if 'nested_scopes' in flag_names:
            flags |= __future__.CO_NESTED
        if 'generators' in flag_names:
            flags |= __future__.CO_GENERATOR_ALLOWED
        if 'division' in flag_names:
            flags |= __future__.CO_FUTURE_DIVISION
        return compile(tuples_or_src, filename, mode, flags)
    return parser.compileast(parser.tuple2ast(tuples_or_src), filename)

if __name__ == '__main__':
    s = file(DUMPFILE, "rb").read()
    tup = marshal.loads(s)
    tuples_or_src, filename, mode, done, flag_names = tup
    try:
        code = reallycompile(tuples_or_src, filename, mode, flag_names)
    except SyntaxError, e:
        code = e.msg, (e.filename, e.lineno, e.offset, e.text)
    done = True
    tup = (code, filename, mode, done, flag_names)
    marshal.dump( tup, file(DUMPFILE, "wb"))
