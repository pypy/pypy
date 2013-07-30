import _curses

lib = _curses.lib


def test_color_content(monkeypatch):
    def lib_color_content(color, r, g, b):
        r[0], g[0], b[0] = 42, 43, 44
        return lib.OK

    monkeypatch.setattr(_curses, '_ensure_initialised_color', lambda: None)
    monkeypatch.setattr(lib, 'color_content', lib_color_content)

    assert _curses.color_content(None) == (42, 43, 44)
