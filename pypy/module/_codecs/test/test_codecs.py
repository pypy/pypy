import autopath

class AppTestCodecs:

    def test_indexerror(self):
        test =   "\\"     # trailing backslash
             
        raises (ValueError, test.decode,'string-escape')

    def test_insecure_pickle(self):
        import pickle
        insecure = ["abc", "2 + 2", # not quoted
                    #"'abc' + 'def'", # not a single quoted string
                    "'abc", # quote is not closed
                    "'abc\"", # open quote and close quote don't match
                    "'abc'   ?", # junk after close quote
                    "'\\'", # trailing backslash
                    # some tests of the quoting rules
                    #"'abc\"\''",
                    #"'\\\\a\'\'\'\\\'\\\\\''",
                    ]
        for s in insecure:
            buf = "S" + s + "\012p0\012."
            print s
            raises (ValueError, pickle.loads, buf)

    def test_partial_utf8(self):
        class Queue(object):
            """     
            queue: write bytes at one end, read bytes from the other end
            """ 
            def __init__(self):
                self._buffer = ""
            
            def write(self, chars):
                self._buffer += chars
    
            def read(self, size=-1):
                if size<0:
                    s = self._buffer
                    self._buffer = ""
                    return s
                else: 
                    s = self._buffer[:size]
                    self._buffer = self._buffer[size:]
                    return s
        def check_partial(encoding, input, partialresults):
            import codecs
            
            # get a StreamReader for the encoding and feed the bytestring version
            # of input to the reader byte by byte. Read every available from
            # the StreamReader and check that the results equal the appropriate
            # entries from partialresults.
            q = Queue()
            r = codecs.getreader(encoding)(q)
            result = u""
            for (c, partialresult) in zip(input.encode(encoding), partialresults):
                q.write(c)
                result += r.read()
                assert result == partialresult
            # check that there's nothing left in the buffers
            assert  r.read() == u"" 
            assert  r.bytebuffer ==  "" 
            assert  r.charbuffer == u""
        encoding = 'utf-8'
        check_partial(encoding, 
                u"\x00\xff\u07ff\u0800\uffff",
                [
                    u"\x00",
                    u"\x00",
                    u"\x00\xff",
                    u"\x00\xff",
                    u"\x00\xff\u07ff",
                    u"\x00\xff\u07ff",
                    u"\x00\xff\u07ff",
                    u"\x00\xff\u07ff\u0800",
                    u"\x00\xff\u07ff\u0800",
                    u"\x00\xff\u07ff\u0800",
                    u"\x00\xff\u07ff\u0800\uffff",
                ]
            )

    def test_partial_utf16(self):
        class Queue(object):
            """     
            queue: write bytes at one end, read bytes from the other end
            """ 
            def __init__(self):
                self._buffer = ""
            
            def write(self, chars):
                self._buffer += chars
    
            def read(self, size=-1):
                if size<0:
                    s = self._buffer
                    self._buffer = ""
                    return s
                else: 
                    s = self._buffer[:size]
                    self._buffer = self._buffer[size:]
                    return s
        def check_partial(encoding, input, partialresults):
            import codecs
            
            # get a StreamReader for the encoding and feed the bytestring version
            # of input to the reader byte by byte. Read every available from
            # the StreamReader and check that the results equal the appropriate
            # entries from partialresults.
            q = Queue()
            r = codecs.getreader(encoding)(q)
            result = u""
            for (c, partialresult) in zip(input.encode(encoding), partialresults):
                q.write(c)
                result += r.read()
                assert result == partialresult
            # check that there's nothing left in the buffers
            assert  r.read() == u"" 
            assert  r.bytebuffer ==  "" 
            assert  r.charbuffer == u""
        encoding = 'utf-16'
        check_partial(encoding, 
                u"\x00\xff\u0100\uffff",
                [
                    u"", # first byte of BOM read
                    u"", # second byte of BOM read => byteorder known
                    u"",
                    u"\x00",
                    u"\x00",
                    u"\x00\xff",
                    u"\x00\xff",
                    u"\x00\xff\u0100",
                    u"\x00\xff\u0100",
                    u"\x00\xff\u0100\uffff",
                ])
    def test_bug1098990_a(self):
        import codecs, StringIO
        self.encoding = 'utf-8'
        s1 = u"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy\r\n"
        s2 = u"offending line: ladfj askldfj klasdj fskla dfzaskdj fasklfj laskd fjasklfzzzzaa%whereisthis!!!\r\n"
        s3 = u"next line.\r\n"
       
        s = (s1+s2+s3).encode(self.encoding)
        stream = StringIO.StringIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        assert reader.readline() == s1
        assert reader.readline() == s2
        assert reader.readline() == s3
        assert reader.readline() == u""

    def test_bug1098990_b(self):
        import codecs, StringIO
        self.encoding = 'utf-8'
        s1 = u"aaaaaaaaaaaaaaaaaaaaaaaa\r\n"
        s2 = u"bbbbbbbbbbbbbbbbbbbbbbbb\r\n"
        s3 = u"stillokay:bbbbxx\r\n"
        s4 = u"broken!!!!badbad\r\n"
        s5 = u"againokay.\r\n"

        s = (s1+s2+s3+s4+s5).encode(self.encoding)
        stream = StringIO.StringIO(s)
        reader = codecs.getreader(self.encoding)(stream)
        assert reader.readline() == s1
        assert reader.readline() == s2
        assert reader.readline() == s3
        assert reader.readline() == s4
        assert reader.readline() == s5
        assert reader.readline() == u""    
    
    def test_seek_utf16le(self):
        # all codecs should be able to encode these
        import codecs, StringIO
        encoding = 'utf-16-le'
        s = u"%s\n%s\n" % (10*u"abc123", 10*u"def456")
        reader = codecs.getreader(encoding)(StringIO.StringIO(s.encode(encoding)))
        for t in xrange(5):
            # Test that calling seek resets the internal codec state and buffers
            reader.seek(0, 0)
            line = reader.readline()
            assert s[:len(line)] == line


    def test_unicode_internal_encode(self):
        import sys
        enc = u"a".encode("unicode_internal")
        if sys.maxunicode == 65535: # UCS2 build
            if sys.byteorder == "big":
                assert enc == "\x00a"
            else:
                assert enc == "a\x00"
        else: # UCS4 build
            enc2 = u"\U00010098".encode("unicode_internal")
            if sys.byteorder == "big":
                assert enc == "\x00\x00\x00a"
                assert enc2 == "\x00\x01\x00\x98"
            else:
                assert enc == "a\x00\x00\x00"
                assert enc2 == "\x98\x00\x01\x00"

    def test_unicode_internal_decode(self):
        import sys
        if sys.maxunicode == 65535: # UCS2 build
            if sys.byteorder == "big":
                bytes = "\x00a"
            else:
                bytes = "a\x00"
        else: # UCS4 build
            if sys.byteorder == "big":
                bytes = "\x00\x00\x00a"
                bytes2 = "\x00\x01\x00\x98"
            else:
                bytes = "a\x00\x00\x00"
                bytes2 = "\x98\x00\x01\x00"
            assert bytes2.decode("unicode_internal") == u"\U00010098"
        assert bytes.decode("unicode_internal") == u"a"

    def test_raw_unicode_escape(self):
        assert unicode("\u0663", "raw-unicode-escape") == u"\u0663"
        assert u"\u0663".encode("raw-unicode-escape") == "\u0663"

    def test_escape_decode(self):
        
        test = 'a\n\\b\x00c\td\u2045'.encode('string_escape')
        assert test.decode('string_escape') =='a\n\\b\x00c\td\u2045'
        assert '\\077'.decode('string_escape') == '?'
        assert '\\100'.decode('string_escape') == '@'
        assert '\\253'.decode('string_escape') == chr(0253)
        assert '\\312'.decode('string_escape') == chr(0312)
