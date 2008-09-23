# XXX TypeErrors on calling handlers, or on bad return values from a
# handler, are obscure and unhelpful.

import StringIO, sys
import unittest, py

from pypy.lib import pyexpat
#from xml.parsers import expat
expat = pyexpat

from test.test_support import sortdict, run_unittest


class TestSetAttribute:
    def setup_method(self, meth):
        self.parser = expat.ParserCreate(namespace_separator='!')
        self.set_get_pairs = [
            [0, 0],
            [1, 1],
            [2, 1],
            [0, 0],
            ]

    def test_returns_unicode(self):
        for x, y in self.set_get_pairs:
            self.parser.returns_unicode = x
            assert self.parser.returns_unicode == y

    def test_ordered_attributes(self):
        for x, y in self.set_get_pairs:
            self.parser.ordered_attributes = x
            assert self.parser.ordered_attributes == y

    def test_specified_attributes(self):
        for x, y in self.set_get_pairs:
            self.parser.specified_attributes = x
            assert self.parser.specified_attributes == y


data = '''\
<?xml version="1.0" encoding="iso-8859-1" standalone="no"?>
<?xml-stylesheet href="stylesheet.css"?>
<!-- comment data -->
<!DOCTYPE quotations SYSTEM "quotations.dtd" [
<!ELEMENT root ANY>
<!ATTLIST root attr1 CDATA #REQUIRED attr2 CDATA #IMPLIED>
<!NOTATION notation SYSTEM "notation.jpeg">
<!ENTITY acirc "&#226;">
<!ENTITY external_entity SYSTEM "entity.file">
<!ENTITY unparsed_entity SYSTEM "entity.file" NDATA notation>
%unparsed_entity;
]>

<root attr1="value1" attr2="value2&#8000;">
<myns:subelement xmlns:myns="http://www.python.org/namespace">
     Contents of subelements
</myns:subelement>
<sub2><![CDATA[contents of CDATA section]]></sub2>
&external_entity;
&skipped_entity;
</root>
'''


# Produce UTF-8 output
class TestParse:
    class Outputter:
        def __init__(self):
            self.out = []

        def StartElementHandler(self, name, attrs):
            self.out.append('Start element: ' + repr(name) + ' ' +
                            sortdict(attrs))

        def EndElementHandler(self, name):
            self.out.append('End element: ' + repr(name))

        def CharacterDataHandler(self, data):
            data = data.strip()
            if data:
                self.out.append('Character data: ' + repr(data))

        def ProcessingInstructionHandler(self, target, data):
            self.out.append('PI: ' + repr(target) + ' ' + repr(data))

        def StartNamespaceDeclHandler(self, prefix, uri):
            self.out.append('NS decl: ' + repr(prefix) + ' ' + repr(uri))

        def EndNamespaceDeclHandler(self, prefix):
            self.out.append('End of NS decl: ' + repr(prefix))

        def StartCdataSectionHandler(self):
            self.out.append('Start of CDATA section')

        def EndCdataSectionHandler(self):
            self.out.append('End of CDATA section')

        def CommentHandler(self, text):
            self.out.append('Comment: ' + repr(text))

        def NotationDeclHandler(self, *args):
            name, base, sysid, pubid = args
            self.out.append('Notation declared: %s' %(args,))

        def UnparsedEntityDeclHandler(self, *args):
            entityName, base, systemId, publicId, notationName = args
            self.out.append('Unparsed entity decl: %s' %(args,))

        def NotStandaloneHandler(self):
            self.out.append('Not standalone')
            return 1

        def ExternalEntityRefHandler(self, *args):
            context, base, sysId, pubId = args
            self.out.append('External entity ref: %s' %(args[1:],))
            return 1

        def StartDoctypeDeclHandler(self, *args):
            self.out.append(('Start doctype', args))
            return 1

        def EndDoctypeDeclHandler(self):
            self.out.append("End doctype")
            return 1

        def EntityDeclHandler(self, *args):
            self.out.append(('Entity declaration', args))
            return 1

        def XmlDeclHandler(self, *args):
            self.out.append(('XML declaration', args))
            return 1

        def ElementDeclHandler(self, *args):
            self.out.append(('Element declaration', args))
            return 1

        def AttlistDeclHandler(self, *args):
            self.out.append(('Attribute list declaration', args))
            return 1

        def SkippedEntityHandler(self, *args):
            self.out.append(("Skipped entity", args))
            return 1

        def DefaultHandler(self, userData):
            pass

        def DefaultHandlerExpand(self, userData):
            pass

    handler_names = [
        'StartElementHandler', 'EndElementHandler', 'CharacterDataHandler',
        'ProcessingInstructionHandler', 'UnparsedEntityDeclHandler',
        'NotationDeclHandler', 'StartNamespaceDeclHandler',
        'EndNamespaceDeclHandler', 'CommentHandler',
        'StartCdataSectionHandler', 'EndCdataSectionHandler', 'DefaultHandler',
        'DefaultHandlerExpand', 'NotStandaloneHandler',
        'ExternalEntityRefHandler', 'StartDoctypeDeclHandler',
        'EndDoctypeDeclHandler', 'EntityDeclHandler', 'XmlDeclHandler',
        'ElementDeclHandler', 'AttlistDeclHandler', 'SkippedEntityHandler',
        ]

    def test_utf8(self):

        out = self.Outputter()
        parser = expat.ParserCreate(namespace_separator='!')
        for name in self.handler_names:
            setattr(parser, name, getattr(out, name))
        parser.returns_unicode = 0
        parser.Parse(data, 1)

        # Verify output
        operations = out.out
        expected_operations = [
            ('XML declaration', (u'1.0', u'iso-8859-1', 0)),
            'PI: \'xml-stylesheet\' \'href="stylesheet.css"\'',
            "Comment: ' comment data '",
            "Not standalone",
            ("Start doctype", ('quotations', 'quotations.dtd', None, 1)),
            ('Element declaration', (u'root', (2, 0, None, ()))),
            ('Attribute list declaration', ('root', 'attr1', 'CDATA', None,
                1)),
            ('Attribute list declaration', ('root', 'attr2', 'CDATA', None,
                0)),
            "Notation declared: ('notation', None, 'notation.jpeg', None)",
            ('Entity declaration', ('acirc', 0, '\xc3\xa2', None, None, None, None)),
            ('Entity declaration', ('external_entity', 0, None, None,
                'entity.file', None, None)),
            "Unparsed entity decl: ('unparsed_entity', None, 'entity.file', None, 'notation')",
            "Not standalone",
            "End doctype",
            "Start element: 'root' {'attr1': 'value1', 'attr2': 'value2\\xe1\\xbd\\x80'}",
            "NS decl: 'myns' 'http://www.python.org/namespace'",
            "Start element: 'http://www.python.org/namespace!subelement' {}",
            "Character data: 'Contents of subelements'",
            "End element: 'http://www.python.org/namespace!subelement'",
            "End of NS decl: 'myns'",
            "Start element: 'sub2' {}",
            'Start of CDATA section',
            "Character data: 'contents of CDATA section'",
            'End of CDATA section',
            "End element: 'sub2'",
            "External entity ref: (None, 'entity.file', None)",
            ('Skipped entity', ('skipped_entity', 0)),
            "End element: 'root'",
        ]
        for operation, expected_operation in zip(operations, expected_operations):
            assert operation == expected_operation

    def test_unicode(self):
        # Try the parse again, this time producing Unicode output
        out = self.Outputter()
        parser = expat.ParserCreate(namespace_separator='!')
        parser.returns_unicode = 1
        for name in self.handler_names:
            setattr(parser, name, getattr(out, name))

        parser.Parse(data, 1)

        operations = out.out
        expected_operations = [
            ('XML declaration', (u'1.0', u'iso-8859-1', 0)),
            'PI: u\'xml-stylesheet\' u\'href="stylesheet.css"\'',
            "Comment: u' comment data '",
            "Not standalone",
            ("Start doctype", ('quotations', 'quotations.dtd', None, 1)),
            ('Element declaration', (u'root', (2, 0, None, ()))),
            ('Attribute list declaration', ('root', 'attr1', 'CDATA', None,
                1)),
            ('Attribute list declaration', ('root', 'attr2', 'CDATA', None,
                0)),
            "Notation declared: (u'notation', None, u'notation.jpeg', None)",
            ('Entity declaration', (u'acirc', 0, u'\xe2', None, None, None,
                None)),
            ('Entity declaration', (u'external_entity', 0, None, None,
                 u'entity.file', None, None)),
            "Unparsed entity decl: (u'unparsed_entity', None, u'entity.file', None, u'notation')",
            "Not standalone",
            "End doctype",
            "Start element: u'root' {u'attr1': u'value1', u'attr2': u'value2\\u1f40'}",
            "NS decl: u'myns' u'http://www.python.org/namespace'",
            "Start element: u'http://www.python.org/namespace!subelement' {}",
            "Character data: u'Contents of subelements'",
            "End element: u'http://www.python.org/namespace!subelement'",
            "End of NS decl: u'myns'",
            "Start element: u'sub2' {}",
            'Start of CDATA section',
            "Character data: u'contents of CDATA section'",
            'End of CDATA section',
            "End element: u'sub2'",
            "External entity ref: (None, u'entity.file', None)",
            ('Skipped entity', ('skipped_entity', 0)),
            "End element: u'root'",
        ]
        for operation, expected_operation in zip(operations, expected_operations):
            assert operation == expected_operation

    def test_parse_file(self):
        # Try parsing a file
        out = self.Outputter()
        parser = expat.ParserCreate(namespace_separator='!')
        parser.returns_unicode = 1
        for name in self.handler_names:
            setattr(parser, name, getattr(out, name))
        file = StringIO.StringIO(data)

        parser.ParseFile(file)

        operations = out.out
        expected_operations = [
            ('XML declaration', (u'1.0', u'iso-8859-1', 0)),
            'PI: u\'xml-stylesheet\' u\'href="stylesheet.css"\'',
            "Comment: u' comment data '",
            "Not standalone",
            ("Start doctype", ('quotations', 'quotations.dtd', None, 1)),
            ('Element declaration', (u'root', (2, 0, None, ()))),
            ('Attribute list declaration', ('root', 'attr1', 'CDATA', None,
                1)),
            ('Attribute list declaration', ('root', 'attr2', 'CDATA', None,
                0)),
            "Notation declared: (u'notation', None, u'notation.jpeg', None)",
            ('Entity declaration', ('acirc', 0, u'\xe2', None, None, None, None)),
            ('Entity declaration', (u'external_entity', 0, None, None, u'entity.file', None, None)),
            "Unparsed entity decl: (u'unparsed_entity', None, u'entity.file', None, u'notation')",
            "Not standalone",
            "End doctype",
            "Start element: u'root' {u'attr1': u'value1', u'attr2': u'value2\\u1f40'}",
            "NS decl: u'myns' u'http://www.python.org/namespace'",
            "Start element: u'http://www.python.org/namespace!subelement' {}",
            "Character data: u'Contents of subelements'",
            "End element: u'http://www.python.org/namespace!subelement'",
            "End of NS decl: u'myns'",
            "Start element: u'sub2' {}",
            'Start of CDATA section',
            "Character data: u'contents of CDATA section'",
            'End of CDATA section',
            "End element: u'sub2'",
            "External entity ref: (None, u'entity.file', None)",
            ('Skipped entity', ('skipped_entity', 0)),
            "End element: u'root'",
        ]
        for operation, expected_operation in zip(operations, expected_operations):
            assert operation == expected_operation


class TestNamespaceSeparator:
    def test_legal(self):
        # Tests that make sure we get errors when the namespace_separator value
        # is illegal, and that we don't for good values:
        expat.ParserCreate()
        expat.ParserCreate(namespace_separator=None)
        expat.ParserCreate(namespace_separator=' ')

    def test_illegal(self):
        try:
            expat.ParserCreate(namespace_separator=42)
            raise AssertionError
        except TypeError, e:
            assert str(e) == (
                'ParserCreate() argument 2 must be string or None, not int')

        try:
            expat.ParserCreate(namespace_separator='too long')
            raise AssertionError
        except ValueError, e:
            assert str(e) == (
                'namespace_separator must be at most one character, omitted, or None')

    def test_zero_length(self):
        # ParserCreate() needs to accept a namespace_separator of zero length
        # to satisfy the requirements of RDF applications that are required
        # to simply glue together the namespace URI and the localname.  Though
        # considered a wart of the RDF specifications, it needs to be supported.
        #
        # See XML-SIG mailing list thread starting with
        # http://mail.python.org/pipermail/xml-sig/2001-April/005202.html
        #
        expat.ParserCreate(namespace_separator='') # too short


class TestInterning:
    def test(self):
        py.test.skip("Not working")
        # Test the interning machinery.
        p = expat.ParserCreate()
        L = []
        def collector(name, *args):
            L.append(name)
        p.StartElementHandler = collector
        p.EndElementHandler = collector
        p.Parse("<e> <e/> <e></e> </e>", 1)
        tag = L[0]
        assert len(L) == 6
        for entry in L:
            # L should have the same string repeated over and over.
            assert tag is entry


class TestBufferText:
    def setup_method(self, meth):
        self.stuff = []
        self.parser = expat.ParserCreate()
        self.parser.buffer_text = 1
        self.parser.CharacterDataHandler = self.CharacterDataHandler

    def check(self, expected, label):
        assert self.stuff == expected, (
                "%s\nstuff    = %r\nexpected = %r"
                % (label, self.stuff, map(unicode, expected)))

    def CharacterDataHandler(self, text):
        self.stuff.append(text)

    def StartElementHandler(self, name, attrs):
        self.stuff.append("<%s>" % name)
        bt = attrs.get("buffer-text")
        if bt == "yes":
            self.parser.buffer_text = 1
        elif bt == "no":
            self.parser.buffer_text = 0

    def EndElementHandler(self, name):
        self.stuff.append("</%s>" % name)

    def CommentHandler(self, data):
        self.stuff.append("<!--%s-->" % data)

    def setHandlers(self, handlers=[]):
        for name in handlers:
            setattr(self.parser, name, getattr(self, name))

    def test_default_to_disabled(self):
        parser = expat.ParserCreate()
        assert not parser.buffer_text

    def test_buffering_enabled(self):
        # Make sure buffering is turned on
        assert self.parser.buffer_text
        self.parser.Parse("<a>1<b/>2<c/>3</a>", 1)
        assert self.stuff == ['123'], (
                          "buffered text not properly collapsed")

    def test1(self):
        # XXX This test exposes more detail of Expat's text chunking than we
        # XXX like, but it tests what we need to concisely.
        self.setHandlers(["StartElementHandler"])
        self.parser.Parse("<a>1<b buffer-text='no'/>2\n3<c buffer-text='yes'/>4\n5</a>", 1)
        assert self.stuff == (
                          ["<a>", "1", "<b>", "2", "\n", "3", "<c>", "4\n5"]), (
                          "buffering control not reacting as expected")

    def test2(self):
        self.parser.Parse("<a>1<b/>&lt;2&gt;<c/>&#32;\n&#x20;3</a>", 1)
        assert self.stuff == ["1<2> \n 3"], (
                          "buffered text not properly collapsed")

    def test3(self):
        self.setHandlers(["StartElementHandler"])
        self.parser.Parse("<a>1<b/>2<c/>3</a>", 1)
        assert self.stuff == ["<a>", "1", "<b>", "2", "<c>", "3"], (
                          "buffered text not properly split")

    def test4(self):
        self.setHandlers(["StartElementHandler", "EndElementHandler"])
        self.parser.CharacterDataHandler = None
        self.parser.Parse("<a>1<b/>2<c/>3</a>", 1)
        assert self.stuff == (
                          ["<a>", "<b>", "</b>", "<c>", "</c>", "</a>"])

    def test5(self):
        self.setHandlers(["StartElementHandler", "EndElementHandler"])
        self.parser.Parse("<a>1<b></b>2<c/>3</a>", 1)
        assert self.stuff == (
            ["<a>", "1", "<b>", "</b>", "2", "<c>", "</c>", "3", "</a>"])

    def test6(self):
        self.setHandlers(["CommentHandler", "EndElementHandler",
                    "StartElementHandler"])
        self.parser.Parse("<a>1<b/>2<c></c>345</a> ", 1)
        assert self.stuff == (
            ["<a>", "1", "<b>", "</b>", "2", "<c>", "</c>", "345", "</a>"]), (
            "buffered text not properly split")

    def test7(self):
        self.setHandlers(["CommentHandler", "EndElementHandler",
                    "StartElementHandler"])
        self.parser.Parse("<a>1<b/>2<c></c>3<!--abc-->4<!--def-->5</a> ", 1)
        assert self.stuff == (
                          ["<a>", "1", "<b>", "</b>", "2", "<c>", "</c>", "3",
                           "<!--abc-->", "4", "<!--def-->", "5", "</a>"]), (
                          "buffered text not properly split")


# Test handling of exception from callback:
class TestHandlerException:
    def StartElementHandler(self, name, attrs):
        raise RuntimeError(name)

    def test(self):
        parser = expat.ParserCreate()
        parser.StartElementHandler = self.StartElementHandler
        try:
            parser.Parse("<a><b><c/></b></a>", 1)
            raise AssertionError
        except RuntimeError, e:
            assert e.args[0] == 'a', (
                              "Expected RuntimeError for element 'a', but" + \
                              " found %r" % e.args[0])


# Test Current* members:
class TestPosition:
    def StartElementHandler(self, name, attrs):
        self.check_pos('s')

    def EndElementHandler(self, name):
        self.check_pos('e')

    def check_pos(self, event):
        pos = (event,
               self.parser.CurrentByteIndex,
               self.parser.CurrentLineNumber,
               self.parser.CurrentColumnNumber)
        assert self.upto < len(self.expected_list)
        expected = self.expected_list[self.upto]
        assert pos == expected, (
                'Expected position %s, got position %s' %(pos, expected))
        self.upto += 1

    def test(self):
        self.parser = expat.ParserCreate()
        self.parser.StartElementHandler = self.StartElementHandler
        self.parser.EndElementHandler = self.EndElementHandler
        self.upto = 0
        self.expected_list = [('s', 0, 1, 0), ('s', 5, 2, 1), ('s', 11, 3, 2),
                              ('e', 15, 3, 6), ('e', 17, 4, 1), ('e', 22, 5, 0)]

        xml = '<a>\n <b>\n  <c/>\n </b>\n</a>'
        self.parser.Parse(xml, 1)


class Testsf1296433:
    def test_parse_only_xml_data(self):
        # http://python.org/sf/1296433
        #
        xml = "<?xml version='1.0' encoding='iso8859'?><s>%s</s>" % ('a' * 1025)
        # this one doesn't crash
        #xml = "<?xml version='1.0'?><s>%s</s>" % ('a' * 10000)

        class SpecificException(Exception):
            pass

        def handler(text):
            raise SpecificException

        parser = expat.ParserCreate()
        parser.CharacterDataHandler = handler

        raises(Exception, parser.Parse, xml)

class TestChardataBuffer:
    """
    test setting of chardata buffer size
    """

    def test_1025_bytes(self):
        assert self.small_buffer_test(1025) == 2

    def test_1000_bytes(self):
        assert self.small_buffer_test(1000) == 1

    def test_wrong_size(self):
        parser = expat.ParserCreate()
        parser.buffer_text = 1
        def f(size):
            parser.buffer_size = size

        raises(TypeError, f, sys.maxint+1)
        raises(ValueError, f, -1)
        raises(ValueError, f, 0)

    def test_unchanged_size(self):
        xml1 = ("<?xml version='1.0' encoding='iso8859'?><s>%s" % ('a' * 512))
        xml2 = 'a'*512 + '</s>'
        parser = expat.ParserCreate()
        parser.CharacterDataHandler = self.counting_handler
        parser.buffer_size = 512
        parser.buffer_text = 1

        # Feed 512 bytes of character data: the handler should be called
        # once.
        self.n = 0
        parser.Parse(xml1)
        assert self.n == 1

        # Reassign to buffer_size, but assign the same size.
        parser.buffer_size = parser.buffer_size
        assert self.n == 1

        # Try parsing rest of the document
        parser.Parse(xml2)
        assert self.n == 2


    def test_disabling_buffer(self):
        xml1 = "<?xml version='1.0' encoding='iso8859'?><a>%s" % ('a' * 512)
        xml2 = ('b' * 1024)
        xml3 = "%s</a>" % ('c' * 1024)
        parser = expat.ParserCreate()
        parser.CharacterDataHandler = self.counting_handler
        parser.buffer_text = 1
        parser.buffer_size = 1024
        assert parser.buffer_size == 1024

        # Parse one chunk of XML
        self.n = 0
        parser.Parse(xml1, 0)
        assert parser.buffer_size == 1024
        assert self.n == 1

        # Turn off buffering and parse the next chunk.
        parser.buffer_text = 0
        assert not parser.buffer_text
        assert parser.buffer_size == 1024
        for i in range(10):
            parser.Parse(xml2, 0)
        assert self.n == 11

        parser.buffer_text = 1
        assert parser.buffer_text
        assert parser.buffer_size == 1024
        parser.Parse(xml3, 1)
        assert self.n == 12



    def make_document(self, bytes):
        return ("<?xml version='1.0'?><tag>" + bytes * 'a' + '</tag>')

    def counting_handler(self, text):
        self.n += 1

    def small_buffer_test(self, buffer_len):
        xml = "<?xml version='1.0' encoding='iso8859'?><s>%s</s>" % ('a' * buffer_len)
        parser = expat.ParserCreate()
        parser.CharacterDataHandler = self.counting_handler
        parser.buffer_size = 1024
        parser.buffer_text = 1

        self.n = 0
        parser.Parse(xml)
        return self.n

    def test_change_size_1(self):
        xml1 = "<?xml version='1.0' encoding='iso8859'?><a><s>%s" % ('a' * 1024)
        xml2 = "aaa</s><s>%s</s></a>" % ('a' * 1025)
        parser = expat.ParserCreate()
        parser.CharacterDataHandler = self.counting_handler
        parser.buffer_text = 1
        parser.buffer_size = 1024
        assert parser.buffer_size == 1024

        self.n = 0
        parser.Parse(xml1, 0)
        parser.buffer_size *= 2
        assert parser.buffer_size == 2048
        parser.Parse(xml2, 1)
        assert self.n == 2

    def test_change_size_2(self):
        xml1 = "<?xml version='1.0' encoding='iso8859'?><a>a<s>%s" % ('a' * 1023)
        xml2 = "aaa</s><s>%s</s></a>" % ('a' * 1025)
        parser = expat.ParserCreate()
        parser.CharacterDataHandler = self.counting_handler
        parser.buffer_text = 1
        parser.buffer_size = 2048
        assert parser.buffer_size == 2048

        self.n=0
        parser.Parse(xml1, 0)
        parser.buffer_size /= 2
        assert parser.buffer_size == 1024
        parser.Parse(xml2, 1)
        assert self.n == 4

    def test_segfault(self):
        py.test.raises(TypeError, expat.ParserCreate, 1234123123)

def test_invalid_data():
    parser = expat.ParserCreate()
    parser.Parse('invalid.xml', 0)
    try:
        parser.Parse("", 1)
    except expat.ExpatError, e:
        assert e.code == 2 # XXX is this reliable?
        assert e.lineno == 1
        assert e.message.startswith('syntax error')
    else:
        py.test.fail("Did not raise")

