from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.objspace.descroperation import object_setattr
from pypy.rlib import rgc
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.platform import platform

import sys
import weakref
import py

if sys.platform == "win32":
    libname = 'libexpat'
else:
    libname = 'expat'
eci = ExternalCompilationInfo(
    libraries=[libname],
    library_dirs=platform.preprocess_library_dirs([]),
    includes=['expat.h'],
    include_dirs=platform.preprocess_include_dirs([]),
    )

eci = rffi_platform.configure_external_library(
    libname, eci,
    [dict(prefix='expat-',
          include_dir='lib', library_dir='win32/bin/release'),
     ])

XML_Content_Ptr = lltype.Ptr(lltype.ForwardReference())
XML_Parser = rffi.COpaquePtr(typedef='XML_Parser')

xml_error_list = [
    "XML_ERROR_NO_MEMORY",
    "XML_ERROR_SYNTAX",
    "XML_ERROR_NO_ELEMENTS",
    "XML_ERROR_INVALID_TOKEN",
    "XML_ERROR_UNCLOSED_TOKEN",
    "XML_ERROR_PARTIAL_CHAR",
    "XML_ERROR_TAG_MISMATCH",
    "XML_ERROR_DUPLICATE_ATTRIBUTE",
    "XML_ERROR_JUNK_AFTER_DOC_ELEMENT",
    "XML_ERROR_PARAM_ENTITY_REF",
    "XML_ERROR_UNDEFINED_ENTITY",
    "XML_ERROR_RECURSIVE_ENTITY_REF",
    "XML_ERROR_ASYNC_ENTITY",
    "XML_ERROR_BAD_CHAR_REF",
    "XML_ERROR_BINARY_ENTITY_REF",
    "XML_ERROR_ATTRIBUTE_EXTERNAL_ENTITY_REF",
    "XML_ERROR_MISPLACED_XML_PI",
    "XML_ERROR_UNKNOWN_ENCODING",
    "XML_ERROR_INCORRECT_ENCODING",
    "XML_ERROR_UNCLOSED_CDATA_SECTION",
    "XML_ERROR_EXTERNAL_ENTITY_HANDLING",
    "XML_ERROR_NOT_STANDALONE",
    "XML_ERROR_UNEXPECTED_STATE",
    "XML_ERROR_ENTITY_DECLARED_IN_PE",
    "XML_ERROR_FEATURE_REQUIRES_XML_DTD",
    "XML_ERROR_CANT_CHANGE_FEATURE_ONCE_PARSING",
    # Added in Expat 1.95.7.
    "XML_ERROR_UNBOUND_PREFIX",
    # Added in Expat 1.95.8.
    "XML_ERROR_UNDECLARING_PREFIX",
    "XML_ERROR_INCOMPLETE_PE",
    "XML_ERROR_XML_DECL",
    "XML_ERROR_TEXT_DECL",
    "XML_ERROR_PUBLICID",
    "XML_ERROR_SUSPENDED",
    "XML_ERROR_NOT_SUSPENDED",
    "XML_ERROR_ABORTED",
    "XML_ERROR_FINISHED",
    "XML_ERROR_SUSPEND_PE",
    ]
xml_model_list = [
    "XML_CTYPE_EMPTY",
    "XML_CTYPE_ANY",
    "XML_CTYPE_MIXED",
    "XML_CTYPE_NAME",
    "XML_CTYPE_CHOICE",
    "XML_CTYPE_SEQ",
    "XML_CQUANT_NONE",
    "XML_CQUANT_OPT",
    "XML_CQUANT_REP",
    "XML_CQUANT_PLUS",
    ]

class CConfigure:
    _compilation_info_ = eci
    XML_Content = rffi_platform.Struct('XML_Content', [
        ('numchildren', rffi.UINT),
        ('children', XML_Content_Ptr),
        ('name', rffi.CCHARP),
        ('type', rffi.INT),
        ('quant', rffi.INT),
    ])
    XML_Encoding = rffi_platform.Struct('XML_Encoding', [
        ('map', rffi.CFixedArray(rffi.INT, 1)),
        ('data', rffi.VOIDP),
        ('convert', rffi.VOIDP),
        ('release', rffi.VOIDP),
    ])
    for name in ['XML_PARAM_ENTITY_PARSING_NEVER',
                 'XML_PARAM_ENTITY_PARSING_UNLESS_STANDALONE',
                 'XML_PARAM_ENTITY_PARSING_ALWAYS']:
        locals()[name] = rffi_platform.ConstantInteger(name)
    XML_MAJOR_VERSION = rffi_platform.ConstantInteger('XML_MAJOR_VERSION')
    XML_MINOR_VERSION = rffi_platform.ConstantInteger('XML_MINOR_VERSION')
    XML_MICRO_VERSION = rffi_platform.ConstantInteger('XML_MICRO_VERSION')
    XML_FALSE = rffi_platform.ConstantInteger('XML_FALSE')
    XML_TRUE = rffi_platform.ConstantInteger('XML_TRUE')

    for name in xml_error_list:
        locals()[name] = rffi_platform.ConstantInteger(name)
    for name in xml_model_list:
        locals()[name] = rffi_platform.ConstantInteger(name)
    for name in xml_model_list:
        locals()[name] = rffi_platform.ConstantInteger(name)
    for name in xml_model_list:
        locals()[name] = rffi_platform.ConstantInteger(name)
    for name in xml_model_list:
        locals()[name] = rffi_platform.ConstantInteger(name)
    for name in xml_model_list:
        locals()[name] = rffi_platform.ConstantInteger(name)
    for name in xml_model_list:
        locals()[name] = rffi_platform.ConstantInteger(name)
    for name in xml_model_list:
        locals()[name] = rffi_platform.ConstantInteger(name)
    XML_Parser_SIZE = rffi_platform.SizeOf("XML_Parser")

for k, v in rffi_platform.configure(CConfigure).items():
    globals()[k] = v

XML_COMBINED_VERSION = 10000*XML_MAJOR_VERSION+100*XML_MINOR_VERSION+XML_MICRO_VERSION

XML_Content_Ptr.TO.become(rffi.CArray(XML_Content))
XML_Encoding_Ptr = lltype.Ptr(XML_Encoding)


def expat_external(*a, **kw):
    kw['compilation_info'] = eci
    return rffi.llexternal(*a, **kw)

INTERNED_CCHARP = "INTERNED"

HANDLERS = dict(
    StartElementHandler = [INTERNED_CCHARP, rffi.CCHARPP],
    EndElementHandler = [INTERNED_CCHARP],
    ProcessingInstructionHandler = [INTERNED_CCHARP, INTERNED_CCHARP],
    CharacterDataHandler = [rffi.CCHARP, rffi.INT],
    UnparsedEntityDeclHandler = [INTERNED_CCHARP] * 5,
    NotationDeclHandler = [INTERNED_CCHARP] * 4,
    StartNamespaceDeclHandler = [INTERNED_CCHARP, INTERNED_CCHARP],
    EndNamespaceDeclHandler = [INTERNED_CCHARP],
    CommentHandler = [rffi.CCHARP],
    StartCdataSectionHandler = [],
    EndCdataSectionHandler = [],
    DefaultHandler = [rffi.CCHARP, rffi.INT],
    DefaultHandlerExpand = [rffi.CCHARP, rffi.INT],
    NotStandaloneHandler = [],
    ExternalEntityRefHandler = [rffi.CCHARP] + [INTERNED_CCHARP] * 3,
    StartDoctypeDeclHandler = [INTERNED_CCHARP, INTERNED_CCHARP,
                               INTERNED_CCHARP, rffi.INT],
    EndDoctypeDeclHandler = [],
    EntityDeclHandler = [INTERNED_CCHARP, rffi.INT, rffi.CCHARP, rffi.INT,
                         INTERNED_CCHARP, INTERNED_CCHARP, INTERNED_CCHARP,
                         INTERNED_CCHARP],
    XmlDeclHandler = [rffi.CCHARP, rffi.CCHARP, rffi.INT],
    ElementDeclHandler = [INTERNED_CCHARP, lltype.Ptr(XML_Content)],
    AttlistDeclHandler = [INTERNED_CCHARP, INTERNED_CCHARP,
                          rffi.CCHARP, rffi.CCHARP, rffi.INT],
    )
if XML_COMBINED_VERSION >= 19504:
    HANDLERS['SkippedEntityHandler'] = [INTERNED_CCHARP, rffi.INT]
NB_HANDLERS = len(HANDLERS)

class Storage:
    "Store objects under a non moving ID"
    def __init__(self):
        self.clear()

    def clear(self):
        self.next_id = 0
        self.storage = {}

    @staticmethod
    def get_nonmoving_id(obj, id=-1):
        if id < 0:
            id = global_storage.next_id
            global_storage.next_id += 1
        global_storage.storage[id] = obj
        return id

    @staticmethod
    def get_object(id):
        return global_storage.storage[id]

    @staticmethod
    def free_nonmoving_id(id):
        del global_storage.storage[id]

global_storage = Storage()

class CallbackData(Wrappable):
    def __init__(self, space, parser):
        self.space = space
        self.parser = weakref.ref(parser)

SETTERS = {}
for index, (name, params) in enumerate(HANDLERS.items()):
    arg_names = ['arg%d' % (i,) for i in range(len(params))]
    warg_names = ['w_arg%d' % (i,) for i in range(len(params))]

    converters = []
    real_params = []

    for i, ARG in enumerate(params):
        # Some custom argument conversions
        if name == "StartElementHandler" and i == 1:
            converters.append(
                'w_arg%d = parser.w_convert_attributes(space, arg%d)' % (i, i))
        elif name in ["CharacterDataHandler", "DefaultHandlerExpand", "DefaultHandler"] and i == 0:
            converters.append(
                'w_arg%d = parser.w_convert_charp_n(space, arg%d, arg%d)' % (i, i, i+1))
            del warg_names[i+1]
        elif name in ["EntityDeclHandler"] and i == 2:
            converters.append(
                'w_arg%d = parser.w_convert_charp_n(space, arg%d, arg%d)' % (i, i, i+1))
            del warg_names[i+1]

        # the standard conversions
        elif ARG == rffi.CCHARP:
            converters.append(
                'w_arg%d = parser.w_convert_charp(space, arg%d)' % (i, i))
        elif ARG == INTERNED_CCHARP:
            converters.append(
                'w_arg%d = parser.w_convert_interned(space, arg%d)' % (i, i))
            ARG = rffi.CCHARP
        elif ARG == lltype.Ptr(XML_Content):
            converters.append(
                'w_arg%d = parser.w_convert_model(space, arg%d)' % (i, i))
            converters.append(
                'XML_FreeContentModel(parser.itself, arg%d)' % (i,))
        else:
            converters.append(
                'w_arg%d = space.wrap(arg%d)' % (i, i))
        real_params.append(ARG)
    converters = '; '.join(converters)

    args = ', '.join(arg_names)
    wargs = ', '.join(warg_names)

    if name in ['ExternalEntityRefHandler',
                'NotStandaloneHandler']:
        result_type = rffi.INT
        result_converter = "rffi.cast(rffi.INT, space.int_w(w_result))"
        result_error = "rffi.cast(rffi.INT, 0)"
    else:
        result_type = lltype.Void
        result_converter = "None"
        result_error = "None"

    if name == 'CharacterDataHandler':
        pre_code = 'if parser.buffer_string(space, w_arg0, arg1): return'
    else:
        pre_code = 'parser.flush_character_buffer(space)'

    if name == 'ExternalEntityRefHandler':
        first_arg = 'll_parser'
        first_lltype = XML_Parser
        ll_id = 'XML_GetUserData(ll_parser)'
        post_code = 'if space.is_w(w_result, space.w_None): return 0'
    else:
        first_arg = 'll_userdata'
        first_lltype = rffi.VOIDP
        ll_id = 'll_userdata'
        post_code = ''

    src = py.code.Source("""
    def %(name)s_callback(%(first_arg)s, %(args)s):
        id = rffi.cast(lltype.Signed, %(ll_id)s)
        userdata = global_storage.get_object(id)
        space = userdata.space
        parser = userdata.parser()

        handler = parser.handlers[%(index)s]
        if not handler:
            return %(result_error)s

        try:
            %(converters)s
            %(pre_code)s
            w_result = space.call_function(handler, %(wargs)s)
            %(post_code)s
        except OperationError, e:
            parser._exc_info = e
            XML_StopParser(parser.itself, XML_FALSE)
            return %(result_error)s
        return %(result_converter)s
    callback = %(name)s_callback
    """ % locals())

    exec str(src)

    c_name = 'XML_Set' + name
    callback_type = lltype.Ptr(lltype.FuncType(
        [first_lltype] + real_params, result_type))
    func = expat_external(c_name,
                          [XML_Parser, callback_type], lltype.Void)
    SETTERS[name] = (index, func, callback)

# special case for UnknownEncodingHandlerData:
# XML_SetUnknownEncodingHandler() needs an additional argument,
# and it's not modifiable via user code anyway
def UnknownEncodingHandlerData_callback(ll_userdata, name, info):
    id = rffi.cast(lltype.Signed, ll_userdata)
    userdata = global_storage.get_object(id)
    space = userdata.space
    parser = userdata.parser()

    name = rffi.charp2str(name)

    try:
        parser.UnknownEncodingHandler(space, name, info)
    except OperationError, e:
        parser._exc_info = e
        XML_StopParser(parser.itself, XML_FALSE)
        result = 0
    else:
        result = 1
    return rffi.cast(rffi.INT, result)
callback_type = lltype.Ptr(lltype.FuncType(
    [rffi.VOIDP, rffi.CCHARP, XML_Encoding_Ptr], rffi.INT))
XML_SetUnknownEncodingHandler = expat_external(
    'XML_SetUnknownEncodingHandler',
    [XML_Parser, callback_type, rffi.VOIDP], lltype.Void)

ENUMERATE_SETTERS = unrolling_iterable(SETTERS.items())

# Declarations of external functions

XML_ParserCreate = expat_external(
    'XML_ParserCreate', [rffi.CCHARP], XML_Parser)
XML_ParserCreateNS = expat_external(
    'XML_ParserCreateNS', [rffi.CCHARP, rffi.CHAR], XML_Parser)
XML_ParserFree = expat_external(
    'XML_ParserFree', [XML_Parser], lltype.Void, threadsafe=False)
XML_SetUserData = expat_external(
    'XML_SetUserData', [XML_Parser, rffi.VOIDP], lltype.Void)
def XML_GetUserData(parser):
    # XXX is this always true?
    return rffi.cast(rffi.VOIDPP, parser)[0]
XML_Parse = expat_external(
    'XML_Parse', [XML_Parser, rffi.CCHARP, rffi.INT, rffi.INT], rffi.INT)
XML_StopParser = expat_external(
    'XML_StopParser', [XML_Parser, rffi.INT], lltype.Void)

XML_SetReturnNSTriplet = expat_external(
    'XML_SetReturnNSTriplet', [XML_Parser, rffi.INT], lltype.Void)
XML_GetSpecifiedAttributeCount = expat_external(
    'XML_GetSpecifiedAttributeCount', [XML_Parser], rffi.INT)
XML_SetParamEntityParsing = expat_external(
    'XML_SetParamEntityParsing', [XML_Parser, rffi.INT], lltype.Void)
XML_SetBase = expat_external(
    'XML_SetBase', [XML_Parser, rffi.CCHARP], lltype.Void)
if XML_COMBINED_VERSION >= 19505:
    XML_UseForeignDTD = expat_external(
        'XML_UseForeignDTD', [XML_Parser, rffi.INT], lltype.Void)

XML_GetErrorCode = expat_external(
    'XML_GetErrorCode', [XML_Parser], rffi.INT)
XML_ErrorString = expat_external(
    'XML_ErrorString', [rffi.INT],
    rffi.CCHARP)
XML_GetCurrentLineNumber = expat_external(
    'XML_GetCurrentLineNumber', [XML_Parser], rffi.INT)
XML_GetErrorLineNumber = XML_GetCurrentLineNumber
XML_GetCurrentColumnNumber = expat_external(
    'XML_GetCurrentColumnNumber', [XML_Parser], rffi.INT)
XML_GetErrorColumnNumber = XML_GetCurrentColumnNumber
XML_GetCurrentByteIndex = expat_external(
    'XML_GetCurrentByteIndex', [XML_Parser], rffi.INT)
XML_GetErrorByteIndex = XML_GetCurrentByteIndex

XML_FreeContentModel = expat_external(
    'XML_FreeContentModel', [XML_Parser, lltype.Ptr(XML_Content)], lltype.Void)
XML_ExternalEntityParserCreate = expat_external(
    'XML_ExternalEntityParserCreate', [XML_Parser, rffi.CCHARP, rffi.CCHARP],
    XML_Parser)

XML_ExpatVersion = expat_external(
    'XML_ExpatVersion', [], rffi.CCHARP)

def get_expat_version(space):
    return space.wrap(rffi.charp2str(XML_ExpatVersion()))

def get_expat_version_info(space):
    return space.newtuple([
        space.wrap(XML_MAJOR_VERSION),
        space.wrap(XML_MINOR_VERSION),
        space.wrap(XML_MICRO_VERSION)])

class Cache:
    def __init__(self, space):
        self.w_error = space.new_exception_class("pyexpat.ExpatError")

class W_XMLParserType(Wrappable):

    def __init__(self, space, parser, w_intern):
        self.itself = parser

        self.w_intern = w_intern

        self.returns_unicode = True
        self.ordered_attributes = False
        self.specified_attributes = False

        self.handlers = [None] * NB_HANDLERS

        self.buffer_w = None
        self.buffer_size = 8192
        self.buffer_used = 0
        self.w_character_data_handler = None

        self._exc_info = None

        # Set user data for callback function
        self.id = global_storage.get_nonmoving_id(
            CallbackData(space, self))
        XML_SetUserData(self.itself, rffi.cast(rffi.VOIDP, self.id))

    def __del__(self):
        if XML_ParserFree: # careful with CPython interpreter shutdown
            XML_ParserFree(self.itself)
        if global_storage:
            global_storage.free_nonmoving_id(self.id)

    @unwrap_spec(flag=int)
    def SetParamEntityParsing(self, space, flag):
        """SetParamEntityParsing(flag) -> success
Controls parsing of parameter entities (including the external DTD
subset). Possible flag values are XML_PARAM_ENTITY_PARSING_NEVER,
XML_PARAM_ENTITY_PARSING_UNLESS_STANDALONE and
XML_PARAM_ENTITY_PARSING_ALWAYS. Returns true if setting the flag
was successful."""
        XML_SetParamEntityParsing(self.itself, flag)

    def UseForeignDTD(self, space, w_flag=True):
        """UseForeignDTD([flag])
Allows the application to provide an artificial external subset if one is
not specified as part of the document instance.  This readily allows the
use of a 'default' document type controlled by the application, while still
getting the advantage of providing document type information to the parser.
'flag' defaults to True if not provided."""
        flag = space.is_true(w_flag)
        XML_UseForeignDTD(self.itself, flag)

    # Handlers management

    def w_convert(self, space, s):
        if self.returns_unicode:
            from pypy.interpreter.unicodehelper import PyUnicode_DecodeUTF8
            return space.wrap(PyUnicode_DecodeUTF8(space, s))
        else:
            return space.wrap(s)

    def w_convert_charp(self, space, data):
        if data:
            return self.w_convert(space, rffi.charp2str(data))
        else:
            return space.w_None

    def w_convert_interned(self, space, data):
        if not data:
            return space.w_None
        w_data = self.w_convert_charp(space, data)
        if not self.w_intern:
            return w_data

        try:
            return space.getitem(self.w_intern, w_data)
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
        space.setitem(self.w_intern, w_data, w_data)
        return w_data

    def w_convert_charp_n(self, space, data, length):
        ll_length = rffi.cast(lltype.Signed, length)
        if data:
            return self.w_convert(space, rffi.charp2strn(data, ll_length))
        else:
            return space.w_None

    def w_convert_attributes(self, space, attrs):
        if self.specified_attributes:
            maxindex = XML_GetSpecifiedAttributeCount(self.itself)
        else:
            maxindex = 0
        while attrs[maxindex]:
            maxindex += 2 # copied

        if self.ordered_attributes:
            w_attrs = space.newlist([
                self.w_convert_charp(space, attrs[i])
                for i in range(maxindex)])
        else:
            w_attrs = space.newdict()
            for i in range(0, maxindex, 2):
                space.setitem(
                    w_attrs,
                    self.w_convert_charp(space, attrs[i]),
                    self.w_convert_charp(space, attrs[i + 1]))

        return w_attrs

    def w_convert_model(self, space, model):
        children = [self.w_convert_model(space, model.c_children[i])
                    for i in range(model.c_numchildren)]
        return space.newtuple([
            space.wrap(model.c_type),
            space.wrap(model.c_quant),
            self.w_convert_charp(space, model.c_name),
            space.newtuple(children)])

    def buffer_string(self, space, w_string, length):
        ll_length = rffi.cast(lltype.Signed, length)
        if self.buffer_w is not None:
            if self.buffer_used + ll_length > self.buffer_size:
                self.flush_character_buffer(space)
                # handler might have changed; drop the rest on the floor
                # if there isn't a handler anymore
                if self.w_character_data_handler is None:
                    return True
            if ll_length <= self.buffer_size:
                self.buffer_w.append(w_string)
                self.buffer_used += ll_length
                return True
            else:
                self.buffer_w = []
                self.buffer_used = 0
        return False

    def sethandler(self, space, name, w_handler, index, setter, handler):

        if name == 'CharacterDataHandler':
            self.flush_character_buffer(space)
            if space.is_w(w_handler, space.w_None):
                self.w_character_data_handler = None
            else:
                self.w_character_data_handler = w_handler

        self.handlers[index] = w_handler
        setter(self.itself, handler)

    sethandler._annspecialcase_ = 'specialize:arg(2)'

    all_chars = ''.join(chr(i) for i in range(256))

    def UnknownEncodingHandler(self, space, name, info):
        # Yes, supports only 8bit encodings
        translationmap = space.unicode_w(
            space.call_method(
                space.wrap(self.all_chars), "decode",
                space.wrap(name), space.wrap("replace")))

        for i in range(256):
            c = translationmap[i]
            if c == u'\ufffd':
                info.c_map[i] = rffi.cast(rffi.INT, -1)
            else:
                info.c_map[i] = rffi.cast(rffi.INT, c)
        info.c_data = lltype.nullptr(rffi.VOIDP.TO)
        info.c_convert = lltype.nullptr(rffi.VOIDP.TO)
        info.c_release = lltype.nullptr(rffi.VOIDP.TO)
        return True


    @unwrap_spec(name=str)
    def setattr(self, space, name, w_value):
        if name == "namespace_prefixes":
            XML_SetReturnNSTriplet(self.itself, space.int_w(w_value))
            return

        for handler_name, (index, setter, handler) in ENUMERATE_SETTERS:
            if name == handler_name:
                return self.sethandler(space, handler_name, w_value,
                                       index, setter, handler)

        # fallback to object.__setattr__()
        return space.call_function(
            object_setattr(space),
            space.wrap(self), space.wrap(name), w_value)

    # Parse methods

    @unwrap_spec(data=str, isfinal=bool)
    def Parse(self, space, data, isfinal=False):
        """Parse(data[, isfinal])
Parse XML data.  `isfinal' should be true at end of input."""

        res = XML_Parse(self.itself, data, len(data), isfinal)
        if self._exc_info:
            e = self._exc_info
            self._exc_info = None
            raise e
        elif res == 0:
            exc = self.set_error(space, XML_GetErrorCode(self.itself))
            raise exc
        self.flush_character_buffer(space)
        return space.wrap(res)

    def ParseFile(self, space, w_file):
        """ParseFile(file)
Parse XML data from file-like object."""
        # XXX not the more efficient method
        w_data = space.call_method(w_file, 'read')
        data = space.str_w(w_data)
        return self.Parse(space, data, isfinal=True)

    @unwrap_spec(base=str)
    def SetBase(self, space, base):
        XML_SetBase(self.itself, base)

    def ExternalEntityParserCreate(self, space, w_context, w_encoding=None):
        """ExternalEntityParserCreate(context[, encoding])
Create a parser for parsing an external entity based on the
information passed to the ExternalEntityRefHandler."""
        if space.is_w(w_context, space.w_None):
            context = None
        else:
            context = space.str_w(w_context)

        if space.is_w(w_encoding, space.w_None):
            encoding = None
        else:
            encoding = space.str_w(w_encoding)

        xmlparser = XML_ExternalEntityParserCreate(
            self.itself, context, encoding)
        if not xmlparser:
            raise MemoryError

        parser = W_XMLParserType(space, xmlparser, self.w_intern)

        # copy handlers from self
        for i in range(NB_HANDLERS):
            parser.handlers[i] = self.handlers[i]

        return space.wrap(parser)

    def flush_character_buffer(self, space):
        if not self.buffer_w:
            return
        w_data = space.call_function(
            space.getattr(space.wrap(''), space.wrap('join')),
            space.newlist(self.buffer_w))
        self.buffer_w = []
        self.buffer_used = 0

        if self.w_character_data_handler:
            space.call_function(self.w_character_data_handler, w_data)

    # Error management

    def set_error(self, space, code):
        err = rffi.charp2strn(XML_ErrorString(code), 200)
        lineno = XML_GetCurrentLineNumber(self.itself)
        colno = XML_GetCurrentColumnNumber(self.itself)
        msg = "%s: line %d, column %d" % (err, lineno, colno)
        w_errorcls = space.fromcache(Cache).w_error
        w_error = space.call_function(w_errorcls, space.wrap(msg))
        space.setattr(w_error, space.wrap("code"), space.wrap(code))
        space.setattr(w_error, space.wrap("offset"), space.wrap(colno))
        space.setattr(w_error, space.wrap("lineno"), space.wrap(lineno))

        self.w_error = w_error
        return OperationError(w_errorcls, w_error)

    def descr_ErrorCode(self, space):
        return space.wrap(XML_GetErrorCode(self.itself))

    def descr_ErrorLineNumber(self, space):
        return space.wrap(XML_GetErrorLineNumber(self.itself))

    def descr_ErrorColumnNumber(self, space):
        return space.wrap(XML_GetErrorColumnNumber(self.itself))

    def descr_ErrorByteIndex(self, space):
        return space.wrap(XML_GetErrorByteIndex(self.itself))

    def get_buffer_size(self, space):
        return space.wrap(self.buffer_size)
    def set_buffer_size(self, space, w_value):
        value = space.getindex_w(w_value, space.w_TypeError)
        if value <= 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "buffer_size must be greater than zero"))
        self.flush_character_buffer(space)
        self.buffer_size = value

    def get_buffer_text(self, space):
        return space.wrap(self.buffer_w is not None)
    def set_buffer_text(self, space, w_value):
        if space.is_true(w_value):
            self.buffer_w = []
            self.buffer_used = 0
        else:
            self.flush_character_buffer(space)
            self.buffer_w = None

    def get_intern(self, space):
        if self.w_intern:
            return self.w_intern
        else:
            return space.w_None


def bool_property(name, cls, doc=None):
    def fget(space, obj):
        return space.wrap(getattr(obj, name))
    def fset(space, obj, value):
        setattr(obj, name, space.bool_w(value))
    return GetSetProperty(fget, fset, cls=cls, doc=doc)

XMLParser_methods = ['Parse', 'ParseFile', 'SetBase', 'SetParamEntityParsing',
                     'ExternalEntityParserCreate']
if XML_COMBINED_VERSION >= 19505:
    XMLParser_methods.append('UseForeignDTD')

W_XMLParserType.typedef = TypeDef(
    "pyexpat.XMLParserType",
    __doc__ = "XML parser",
    __setattr__ = interp2app(W_XMLParserType.setattr),
    returns_unicode = bool_property('returns_unicode', W_XMLParserType),
    ordered_attributes = bool_property('ordered_attributes', W_XMLParserType),
    specified_attributes = bool_property('specified_attributes', W_XMLParserType),
    intern = GetSetProperty(W_XMLParserType.get_intern, cls=W_XMLParserType),
    buffer_size = GetSetProperty(W_XMLParserType.get_buffer_size,
                                 W_XMLParserType.set_buffer_size,
                                 cls=W_XMLParserType),
    buffer_text = GetSetProperty(W_XMLParserType.get_buffer_text,
                                 W_XMLParserType.set_buffer_text, cls=W_XMLParserType),

    ErrorCode = GetSetProperty(W_XMLParserType.descr_ErrorCode, cls=W_XMLParserType),
    ErrorLineNumber = GetSetProperty(W_XMLParserType.descr_ErrorLineNumber, cls=W_XMLParserType),
    ErrorColumnNumber = GetSetProperty(W_XMLParserType.descr_ErrorColumnNumber, cls=W_XMLParserType),
    ErrorByteIndex = GetSetProperty(W_XMLParserType.descr_ErrorByteIndex, cls=W_XMLParserType),
    CurrentLineNumber = GetSetProperty(W_XMLParserType.descr_ErrorLineNumber, cls=W_XMLParserType),
    CurrentColumnNumber = GetSetProperty(W_XMLParserType.descr_ErrorColumnNumber, cls=W_XMLParserType),
    CurrentByteIndex = GetSetProperty(W_XMLParserType.descr_ErrorByteIndex, cls=W_XMLParserType),

    **dict((name, interp2app(getattr(W_XMLParserType, name)))
           for name in XMLParser_methods)
    )

def ParserCreate(space, w_encoding=None, w_namespace_separator=None,
                 w_intern=NoneNotWrapped):
    """ParserCreate([encoding[, namespace_separator]]) -> parser
Return a new XML parser object."""
    if space.is_w(w_encoding, space.w_None):
        encoding = None
    elif space.is_true(space.isinstance(w_encoding, space.w_str)):
        encoding = space.str_w(w_encoding)
    else:
        type_name = space.type(w_encoding).getname(space)
        raise OperationError(
            space.w_TypeError,
            space.wrap('ParserCreate() argument 1 must be string or None,'
                       ' not %s' % (type_name,)))

    if space.is_w(w_namespace_separator, space.w_None):
        namespace_separator = 0
    elif space.is_true(space.isinstance(w_namespace_separator, space.w_str)):
        separator = space.str_w(w_namespace_separator)
        if len(separator) == 0:
            namespace_separator = 0
        elif len(separator) == 1:
            namespace_separator = ord(separator[0])
        else:
            raise OperationError(
                space.w_ValueError,
                space.wrap('namespace_separator must be at most one character,'
                           ' omitted, or None'))
    else:
        type_name = space.type(w_namespace_separator).getname(space)
        raise OperationError(
            space.w_TypeError,
            space.wrap('ParserCreate() argument 2 must be string or None,'
                       ' not %s' % (type_name,)))

    # Explicitly passing None means no interning is desired.
    # Not passing anything means that a new dictionary is used.
    if w_intern is None:
        w_intern = space.newdict()
    elif space.is_w(w_intern, space.w_None):
        w_intern = None

    if namespace_separator:
        xmlparser = XML_ParserCreateNS(
            encoding,
            rffi.cast(rffi.CHAR, namespace_separator))
    else:
        xmlparser = XML_ParserCreate(encoding)
    # Currently this is just the size of the pointer and some estimated bytes.
    # The struct isn't actually defined in expat.h - it is in xmlparse.c
    # XXX: find a good estimate of the XML_ParserStruct
    rgc.add_memory_pressure(XML_Parser_SIZE + 300)
    if not xmlparser:
        raise OperationError(space.w_RuntimeError,
                             space.wrap('XML_ParserCreate failed'))

    parser = W_XMLParserType(space, xmlparser, w_intern)
    XML_SetUnknownEncodingHandler(
        parser.itself, UnknownEncodingHandlerData_callback,
        rffi.cast(rffi.VOIDP, parser.id))
    return space.wrap(parser)

@unwrap_spec(code=int)
def ErrorString(space, code):
    """ErrorString(errno) -> string
Returns string error for given number."""
    return space.wrap(rffi.charp2str(XML_ErrorString(code)))

