import cherrypy
from rpython2javascript.pypy.translator.js.main import rpython2javascript

class TemplatePlugin:

    def __init__(self, extra_vars_func=None, options=None):
        """The standard constructor takes an 'extra_vars_func',
        which is a callable that is called for additional
        variables with each rendering. Options is a dictionary
        that provides options specific to template engines
        (encoding, for example). The options should be
        prefixed with the engine's scheme name to allow the
        same dictionary to be passed in to multiple engines
        without ill effects."""
        pass
    
    # the template name will be in python "dot" notation
    # eg "package1.package2.templatename". It will *not*
    # have the extension on it. You may want to cache the
    # template. This method is only called directly if a
    # template is specified in turbogears.view.baseTemplates.
    # You might call this yourself from render.
    # This doesn't *have* to return anything, but
    # existing implementations return a template class.
    # (this does not necessarily make sense for all template
    # engines, though, which is why no return value is
    # required.)
    def load_template(self, templatename):
        "Find a template specified in python 'dot' notation."
        pass
    
    # info is the dictionary returned by the user's controller.
    # format may only make sense for template engines that can
    # produce different styles of output based on the same
    # template.
    # fragment is used if there are special rules about rendering
    # a part of a page (don't include headers and declarations).
    # template is the name of the template to render.
    # You should incorporate extra_vars_func() output
    # into the namespace in your template if at all possible.
    def render(self, info, format="html", fragment=False, template=None):
        "Renders the template to a string using the provided info."
        cherrypy.response.headers["Content-Type"] = "text/javascript"
        return 'alert("JavascriptCodeGoesHere")'

    # This method is not required for most uses of templates.
    # It is specifically used for efficiently inserting widget
    # output into Kid pages. It does the same thing render does,
    # except the output is a generator of ElementTree Elements 
    # rather than a string.
    def transform(self, info, template):
        "Render the output to Elements"
        pass
