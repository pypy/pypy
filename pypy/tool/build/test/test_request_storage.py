import path
import py
from pypybuilder.server.server import RequestStorage

def test_request_storage():
    s = RequestStorage()

    assert s._id_to_info == {}
    assert s._id_to_emails == {}
    assert s._id_to_path == {}

    info = {'foo': 1}
    infoid = s.get_info_id(info)
    
    path = s.request('foo@bar.com', info)
    assert path is None
    assert s._id_to_info == {infoid: info}
    assert s._id_to_emails == {infoid: ['foo@bar.com']}
    assert s._id_to_path == {}

    path = s.request('bar@bar.com', info)
    assert path is None
    assert s._id_to_info == {infoid: info}
    assert s._id_to_emails == {infoid: ['foo@bar.com', 'bar@bar.com']}
    assert s._id_to_path == {}

    emails = s.add_build(info, 'foobar')
    assert emails == ['foo@bar.com', 'bar@bar.com']
    assert s._id_to_info == {infoid: info}
    assert s._id_to_emails == {}
    assert s._id_to_path == {infoid: 'foobar'}

    info2 = {'foo': 2, 'bar': [1,2]}
    infoid2 = s.get_info_id(info2)
    
    path = s.request('foo@baz.com', info2)
    assert path is None
    assert s._id_to_info == {infoid: info, infoid2: info2}
    assert s._id_to_emails == {infoid2: ['foo@baz.com']}
    assert s._id_to_path == {infoid: 'foobar'}

    emails = s.add_build(info2, 'foobaz')
    assert emails == ['foo@baz.com']
    assert s._id_to_info == {infoid: info, infoid2: info2}
    assert s._id_to_emails == {}
    assert s._id_to_path == {infoid: 'foobar', infoid2: 'foobaz'}

    path = s.request('foo@qux.com', info)
    assert path == 'foobar'

def test__build_initial():
    s = RequestStorage([({'foo': 1}, 'foo'), ({'foo': 2}, 'bar'),])

    id1 = s.get_info_id({'foo': 1})
    id2 = s.get_info_id({'foo': 2})

    assert s._id_to_info == {id1: {'foo': 1}, id2: {'foo': 2}}
    assert s._id_to_emails == {}
    assert s._id_to_path == {id1: 'foo', id2: 'bar'}

def test__normalize():
    s = RequestStorage()
    assert (s._normalize({'foo': ['bar', 'baz']}) == 
            s._normalize({'foo': ['baz', 'bar']}))
