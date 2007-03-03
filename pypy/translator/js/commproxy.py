
""" Communication proxy rendering
"""


from pypy.objspace.flow.model import Variable, Constant
from pypy.rpython.ootypesystem.bltregistry import ArgDesc

GET_METHOD_BODY = """
%(class)s.prototype.%(method)s = function ( %(args)s ) {
    var data,str;
    var x = new XMLHttpRequest();
    data = %(data)s;
    str = ""
    for(i in data) {
        if (data[i]) {
            if (str.length == 0) {
                str += "?";
            } else {
                str += "&";
            }
            str += escape(i) + "=" + escape(data[i].toString());
        }
    }
    //logDebug('%(call)s'+str);
    x.open("GET", '%(call)s' + str, true);
    x.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    x.onreadystatechange = function () { %(real_callback)s(x, callback) };
    //x.setRequestHeader("Connection", "close");
    //x.send(data);
    x.send(null);
}
"""

POST_METHOD_BODY = """
%(class)s.prototype.%(method)s = function ( %(args)s ) {
    var data,str;
    var x = new XMLHttpRequest();
    data = %(data)s;
    str = ""
    for(i in data) {
        if (data[i]) {
            if (str.length != 0) {
                str += "&";
            }
            str += escape(i) + "=" + escape(data[i].toString());
        }
    }
    //logDebug('%(call)s'+str);
    x.open("POST", '%(call)s', true);
    //x.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    x.onreadystatechange = function () { %(real_callback)s(x, callback) };
    //x.setRequestHeader("Connection", "close");
    //logDebug(str);
    x.send(str);
    //x.send(null);
}
"""

CALLBACK_BODY = """
function %(real_callback)s (x, cb) {
   var d;
   if (x.readyState == 4) {
      if (x.responseText) {
         eval ( "d = " + x.responseText );
         cb(d);
      } else {
         cb({});
      }
   }
}
"""

CALLBACK_XML_BODY = """
function %(real_callback)s (x, cb) {
   if (x.readyState == 4) {
     if (x.responseXML) {
       cb(x.responseXML.documentElement);
     } else {
       cb(null);
     }
   }
}
"""

MOCHIKIT_BODY = """
%(class)s.prototype.%(method)s = function ( %(args)s ) {
    var data,str;
    data = %(data)s;
    loadJSONDoc('%(call)s', data).addCallback(callback);
}
"""

USE_MOCHIKIT = True # FIXME: some option?

class XmlHttp(object):
    """ Class for rendering xmlhttp request communication
    over normal js code
    """
    def __init__(self, ext_obj, name, use_xml=False, base_url="", method="GET"):
        self.ext_obj = ext_obj
        self.name = name
        self.use_xml = use_xml
        self.base_url = base_url
        obj = self.ext_obj._TYPE._class_
        if not base_url and hasattr(obj, '_render_base_path'):
            self.base_url = obj._render_base_path
        self.method = method
    
    def render(self, ilasm):
        self.render_body(ilasm)
        for method_name, method in self.ext_obj._TYPE._class_._methods.iteritems():
            self.render_method(method_name, method, ilasm)
    
    def render_body(self, ilasm):
        ilasm.begin_function(self.name, [])
        ilasm.end_function()
    
    def render_method(self, method_name, method, ilasm):
        args, retval = method.args, method.retval.name
        if len(args) == 0 or args[-1].name != 'callback':
            args.append(ArgDesc('callback', lambda : None))
        real_args = list(arg.name for arg in args)
        # FIXME: dirty JS here
        data = "{%s}" % ",".join(["'%s':%s" % (i,i) for i in real_args if i != 'callback'])
        real_callback = Variable("callback").name
        if len(self.base_url) > 0 and not self.base_url.endswith("/"):
            url = self.base_url + "/" +method_name
        else:
            url = self.base_url + method_name
        
        METHOD_BODY = globals()[self.method + "_METHOD_BODY"]
        if USE_MOCHIKIT and self.use_xml:
            assert 0, "Cannot use mochikit and xml requests at the same time"
        if USE_MOCHIKIT and self.method == "POST":
            assert 0, "Cannot use mochikit with POST method"
        if USE_MOCHIKIT:
            ilasm.codegenerator.write(MOCHIKIT_BODY % {'class':self.name, 'method':method_name,\
                'args':','.join(real_args), 'data':data, 'call':url})
        else:
            if not self.use_xml:
                callback_body = CALLBACK_BODY
            else:
                callback_body = CALLBACK_XML_BODY
            ilasm.codegenerator.write(callback_body % {'real_callback':real_callback})
            ilasm.codegenerator.write(METHOD_BODY % {'class':self.name, 'method':method_name,\
                'args':",".join(real_args), 'data':data, 'call':url,\
                'real_callback':real_callback})
