from rpython.translator.interactive import Translation



def compile(entry_point):
    t = Translation(entry_point, backend='c', rsandbox=True)
    return str(t.compile())


def test_empty():
    def entry_point(argv):
        return 0

    print compile(entry_point)
