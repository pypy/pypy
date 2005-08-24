import parser, marshal, os

DUMPFILE = 'this_is_the_marshal_file'

def reallycompile(tuples, filename, mode, flag_names):
    # XXX : use the flags if possible
    return parser.compileast(parser.tuple2ast(tuples), filename)

if __name__ == '__main__':
    tuples, filename, mode, done, flag_names = marshal.load(file(DUMPFILE, "rb"))
    code = reallycompile(tuples, filename, mode, flag_names)
    done = True
    marshal.dump( (code, filename, mode, done ), file(DUMPFILE, "wb"), 1)
