import parser, marshal, os

DUMPFILE = 'this_is_the_marshal_file'

def fakeapplevelcompile(tuples, filename, mode):
    done = False
    data = marshal.dumps( (tuples, filename, mode, done) )
    file(DUMPFILE, "wb").write(data)
    os.system('%s fakecompiler.py' % get_python())
    data = file(DUMPFILE, "rb").read()
    code, filename, mode, done = marshal.loads(data)
    if not done:
        raise ValueError, "could not fake compile!"
    return code

def reallycompile(tuples, filename, mode):
    return parser.compileast(parser.tuple2ast(tuples), filename)

def get_python():
    try:
        return file('pythonname').read().strip()
    except IOError:
        raise ValueError, "I need a local file 'pythonname'"

if __name__ == '__main__':
    tuples, filename, mode, done = marshal.load(file(DUMPFILE, "rb"))
    code = reallycompile(tuples, filename, mode)
    done = True
    marshal.dump( (code, filename, mode, done), file(DUMPFILE, "wb"), 1)
