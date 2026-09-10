from email import feedparser
from unittest import mock

import pytest


@pytest.mark.pypy_only
def test_multipart_boundaries_do_not_compile_regexes():
    # A regex per boundary causes the JIT to compile more traces as messages
    # with different boundaries arrive (issue #3961).
    with mock.patch.object(feedparser, 're', wraps=feedparser.re) as regex:
        for boundary in ('BOUNDARY-0', 'BOUNDARY-1', 'boundary.+[2]'):
            source = (
                'Content-Type: multipart/mixed; boundary="{0}"\r\n'
                '\r\n'
                '--{0}\r\n'
                'Content-Type: text/plain\r\n'
                '\r\n'
                'hello\r\n'
                '--{0}--\r\n'
            ).format(boundary)
            parser = feedparser.FeedParser()
            parser.feed(source)
            message = parser.close()
            assert message.is_multipart()
            assert len(message.get_payload()) == 1
            assert message.get_payload(0).get_payload() == 'hello'
            assert message.defects == []
        regex.compile.assert_not_called()
