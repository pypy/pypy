
def test_process_prompt():
    from pyrepl.reader import Reader
    r = Reader(None)
    assert r.process_prompt(u"hi!") == (u"hi!", 3)
    assert r.process_prompt(u"h\x01i\x02!") == (u"hi!", 2)
    assert r.process_prompt(u"hi\033[11m!") == (u"hi\033[11m!", 8)
    assert r.process_prompt(u"h\x01i\033[11m!\x02") == (u"hi\033[11m!", 1)
    assert r.process_prompt(u"h\033[11m\x01i\x02!") == (u"h\033[11mi!", 7)
