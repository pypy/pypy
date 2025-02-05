
def test_django_bug():
    xml_str = '<?xml version="1.0" standalone="no"?><!DOCTYPE example SYSTEM "http://example.com/example.dtd"><root/>'

    from xml.dom import pulldom
    from xml.sax import handler
    from xml.sax.expatreader import ExpatParser as _ExpatParser
    from _io import StringIO

    class DefusedExpatParser(_ExpatParser):
        def start_doctype_decl(self, name, sysid, pubid, has_internal_subset):
            raise DTDForbidden(name, sysid, pubid)

        def external_entity_ref_handler(self, context, base, sysid, pubid):
            raise ExternalReferenceForbidden(context, base, sysid, pubid)

        def reset(self):
            _ExpatParser.reset(self)
            parser = self._parser
            parser.StartDoctypeDeclHandler = self.start_doctype_decl
            parser.ExternalEntityRefHandler = self.external_entity_ref_handler


    class DTDForbidden(ValueError):
        pass


    class ExternalReferenceForbidden(ValueError):
        pass

    stream = pulldom.parse(StringIO(xml_str), DefusedExpatParser())

    try:
        for event, node in stream:
            print(event, node)
    except DTDForbidden:
        pass
    else:
        raise Exception("should raise DTDForbidden")


