
""" Communication proxy rendering
"""


from pypy.objspace.flow.model import Variable, Constant

METHOD_BODY = """
%(class)s.prototype.%(method)s = function ( %(args)s ) {
    var data,str;
    x = new XMLHttpRequest();
    data = %(data)s;
    str = "?"
    for(i in data) {
        if (data[i]) {
            str += i + "=" + data[i].toString() + ";";
        }
    }
    logDebug('%(call)s'+str);
    x.open("GET", '%(call)s' + str, true);
    //x.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    x.onreadystatechange = function () { %(real_callback)s(callback) };
    //x.setRequestHeader("Connection", "close");
    //x.send(data);
    x.send(null);
}
"""

CALLBACK_BODY = """
function %(real_callback)s (cb) {
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

MOCHIKIT_BODY = """
%(class)s.prototype.%(method)s = function ( %(args)s ) {
    var data,str;
    data = %(data)s;
    str = "?"
    for(i in data) {
        //if (data[i]) {
            str += i + "=" + data[i].toString() + ";";
        //}
    }
    //logDebug('%(call)s'+str);
    loadJSONDoc('%(call)s' + str).addCallback(callback);
}
"""

class XmlHttp(object):
    """ Class for rendering xmlhttp request communication
    over normal js code
    """
    def __init__(self, ext_obj, name):
        self.ext_obj = ext_obj
        self.name = name
    
    def render(self, ilasm):
        self.render_body(ilasm)
        for method_name, method in self.ext_obj._TYPE._class_._methods.iteritems():
            self.render_method(method_name, method, ilasm)
    
    def render_body(self, ilasm):
        ilasm.begin_function(self.name, [])
        ilasm.end_function()
    
    def render_method(self, method_name, method, ilasm):
        USE_MOCHIKIT = True # FIXME: some option?
        
        args, retval = method.args, method.retval.name
        real_args = list(arg.name for arg in args)
        # FIXME: dirty JS here
        data = "{%s}" % ",".join(["'%s':%s" % (i,i) for i in real_args if i != 'callback'])
        real_callback = Variable("callback").name
        if USE_MOCHIKIT:
            ilasm.codegenerator.write(MOCHIKIT_BODY % {'class':self.name, 'method':method_name,\
                'args':','.join(real_args), 'data':data, 'call':method_name})
        else:
            ilasm.codegenerator.write(CALLBACK_BODY % {'real_callback':real_callback})
            ilasm.codegenerator.write(METHOD_BODY % {'class':self.name, 'method':method_name,\
                'args':",".join(real_args), 'data':data, 'call':'http://localhost:8080/'+method_name,\
                'real_callback':real_callback})
