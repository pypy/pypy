from __future__ import unicode_literals
from pyrepl.unix_eventqueue import EncodedQueue, Event


def test_simple():
    q = EncodedQueue({}, 'utf-8')

    a = u'\u1234'
    b = a.encode('utf-8')
    for c in b:
        q.push(c)

    event = q.get()
    assert q.get() is None
    assert event.data == a
    assert event.raw == b


def test_propagate_escape():
    def send(keys):
        for c in keys:
            q.push(c)

        events = []
        while True:
            event = q.get()
            if event is None:
                break
            events.append(event)
        return events        

    keymap = {
        b'\033': {b'U': 'up', b'D': 'down'},
        b'\xf7': 'backspace',
    }
    q = EncodedQueue(keymap, 'utf-8')

    # normal behaviour
    assert send(b'\033U') == [Event('key', 'up', bytearray(b'\033U'))]
    assert send(b'\xf7') == [Event('key', 'backspace', bytearray(b'\xf7'))]

    # escape propagation: simulate M-backspace
    events = send(b'\033\xf7')
    assert events == [
        Event('key', '\033', bytearray(b'\033')),
        Event('key', 'backspace', bytearray(b'\xf7'))
    ]
