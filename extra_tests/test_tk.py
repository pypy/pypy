from _tkinter.tclobj import FromTclString, AsObj
import pytest

def test_encoding_mess_from_tcl_string():
    # cesu-8 mess
    assert FromTclString(b'string\xed\xa0\xbd\xed\xb2\xbb') == 'string\U0001f4bb'


@pytest.mark.pypy_only
def test_image_adds_memory_pressure(monkeypatch):
    import tkinter

    class FakeTk:
        # Supply image dimensions without requiring a display server.
        def call(self, *args):
            if args == ('image', 'width', 'test_image'):
                return '23'
            if args == ('image', 'height', 'test_image'):
                return '17'
            return ''

        getint = staticmethod(int)

    pressures = []
    monkeypatch.setattr(tkinter, 'add_memory_pressure', pressures.append,
                        raising=False)
    image = tkinter.PhotoImage(name='test_image', master=FakeTk())
    assert pressures == [23 * 17 * 3]
