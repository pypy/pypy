# spaceconfig = {"usemodules" : ["_csv"]}


import _csv as csv

class DummyFile:

    def __init__(self):
        self._parts = []
        self.write = self._parts.append

    def getvalue(self):
        return ''.join(self._parts)

def _write_test(fields, expect, **kwargs):
    fileobj = DummyFile()
    writer = csv.writer(fileobj, **kwargs)
    if hasattr(fields, '__len__') and len(fields) > 0 and type(fields[0]) is list:
        writer.writerows(fields)
    else:
        writer.writerow(fields)
    result = fileobj.getvalue()
    expect += writer.dialect.lineterminator
    assert result == expect, 'result: %r\nexpect: %r' % (
        result, expect)

def test_write_arg_valid():
    raises(csv.Error, _write_test, None, '')    # xxx different API!
    _write_test((), '')
    _write_test([None], '""')
    raises(csv.Error, _write_test,
                      [None], None, quoting = csv.QUOTE_NONE)
    # Check that exceptions are passed up the chain
    class BadList:
        def __len__(self):
            return 10;
        def __getitem__(self, i):
            if i > 2:
                raise IOError

    raises(IOError, _write_test, BadList(), '')

    class BadItem:
        def __str__(self):
            raise IOError
    raises(IOError, _write_test, [BadItem()], '')

def test_write_quoting():
    import _csv as csv
    _write_test(['a',1,'p,q'], 'a,1,"p,q"')
    raises(csv.Error, _write_test,
                      ['a',1,'p,q'], 'a,1,p,q',
                      quoting = csv.QUOTE_NONE)
    _write_test(['a',1,'p,q'], 'a,1,"p,q"',
                     quoting = csv.QUOTE_MINIMAL)
    _write_test(['a',1,'p,q'], '"a",1,"p,q"',
                     quoting = csv.QUOTE_NONNUMERIC)
    _write_test(['a',1,'p,q'], '"a","1","p,q"',
                     quoting = csv.QUOTE_ALL)
    _write_test(['a\nb',1], '"a\nb","1"',
                     quoting = csv.QUOTE_ALL)

def test_write_escape():
    import _csv as csv
    _write_test(['a',1,'p,q'], 'a,1,"p,q"',
                     escapechar='\\')
    raises(csv.Error, _write_test,
                      ['a',1,'p,"q"'], 'a,1,"p,\\"q\\""',
                      escapechar=None, doublequote=False)
    _write_test(['a',1,'p,"q"'], 'a,1,"p,\\"q\\""',
                     escapechar='\\', doublequote = False)
    _write_test(['"'], '""""',
                     escapechar='\\', quoting = csv.QUOTE_MINIMAL)
    _write_test(['"'], '\\"',
                     escapechar='\\', quoting = csv.QUOTE_MINIMAL,
                     doublequote = False)
    _write_test(['\\', 'a'], '\\\\,a',
                     escapechar='\\', quoting=csv.QUOTE_MINIMAL)
    _write_test(['\\', 'a'], '"\\\\","a"',
                     escapechar='\\', quoting=csv.QUOTE_ALL)
    _write_test(['"'], '\\"',
                     escapechar='\\', quoting = csv.QUOTE_NONE)
    _write_test(['a',1,'p,q'], 'a,1,p\\,q',
                     escapechar='\\', quoting = csv.QUOTE_NONE)

def test_writerows():
    _write_test([['a'],['b','c']], 'a\r\nb,c')

def test_write_lineterminator():
    r"""
    from io import StringIO
    import csv
    for lineterminator in '\r\n', '\n', '\r', '!@#', '\0':
            with StringIO() as sio:
                writer = csv.writer(sio, lineterminator=lineterminator)
                writer.writerow(['a', 'b'])
                writer.writerow([1, 2])
                writer.writerow(['\r', '\n'])
                assert (sio.getvalue() ==
                                 f'a,b{lineterminator}'
                                 f'1,2{lineterminator}'
                                 f'"\r","\n"{lineterminator}'
                                 )
    """

def test_write_empty_fields_space_delimiter():
        _write_test(['', ''], '"" ""', delimiter=' ', skipinitialspace=True)
