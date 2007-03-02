from pypy.translator.gensupp import NameManager
#from pypy.translator.js.optimize import is_optimized_function

class JavascriptNameManager(NameManager):
    def __init__(self, db):
        NameManager.__init__(self)
        self.db = db
        self.reserved = {}

        #http://javascript.about.com/library/blreserved.htm
        reserved_words = '''
            abstract as boolean break byte case catch
            char class continue const debugger default delete
            do double else enum export extends false
            final finally float for function goto if implements
            import in instanceof int interface is long
            namespace native new null package private protected
            public return short static super switch synchronized
            this throw throws transient true try typeof
            use var void volatile while with alert
            '''
        for name in reserved_words.split():
            self.reserved[name] = True

        #http://javascript.about.com/library/blclassobj.htm
        # XXX WAAAHHH!!! IE alert :( there are a lot of objects here that are
        # _not_ in standard JS, see
        # http://devedge-temp.mozilla.org/library/manuals/2000/javascript/1.5/reference/
        predefined_classes_and_objects = '''
            Anchor anchors Applet applets Area Array Body
            Button Checkbox Date document Error EvalError FileUpload
            Form forms frame frames Function Hidden History
            history Image images Link links location Math
            MimeType mimetypes navigator Number Object Option options
            Password Plugin plugins Radio RangeError ReferenceError RegExp
            Reset screen Script Select String Style StyleSheet
            Submit SyntaxError Text Textarea TypeError URIError window
            '''
        for name in predefined_classes_and_objects.split():
            self.reserved[name] = True

        #http://javascript.about.com/library/blglobal.htm
        global_properties_and_methods = '''
            _content closed Components controllers crypto defaultstatus directories
            document frames history innerHeight innerWidth length location
            locationbar menubar name navigator opener outerHeight outerWidth
            pageXOffset pageYOffset parent personalbar pkcs11 prompter screen
            screenX screenY scrollbars scrollX scrollY self statusbar
            toolbar top window
            '''
        for name in global_properties_and_methods.split():
            self.reserved[name] = True

        self.make_reserved_names(' '.join(self.reserved))
        
        self.predefined = set(predefined_classes_and_objects)

    #def uniquename(self, name, lenmax=0):
    #    return NameManager.uniquename(self, , lenmax)

    def ensure_non_reserved(self, name):
        while name in self.reserved:
            name += '_'
        return name
