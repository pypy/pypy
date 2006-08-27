from turbogears.widgets.base import JSSource, CoreWD, RenderOnlyWD

class RPyJSSource(JSSource):
    def __init__(self, src, location=None):
        #print 'RPyJSSource: python:', src
        mod = 'RPyJSSourceTmp.py'
        f = open(mod, 'w')
        f.write(src)
        f.close()
        function_names = []
        from rpython2javascript.pypy.translator.js.main import rpython2javascript_main
        jssrc = rpython2javascript_main([mod] + function_names)
        #print 'RPyJSSource: javascript:', jssrc
        super(RPyJSSource, self).__init__(jssrc)
        
class RPyJSSourceDesc(CoreWD, RenderOnlyWD):
    name = "RPyJSSource"
    for_widget = RPyJSSource("def main(): return 42")
