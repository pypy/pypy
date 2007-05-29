{'application':{'type':'Application',
          'name':'Minimal',
    'backgrounds': [
    {'type':'Background',
          'name':'bgMin',
          'title':u'Query Answering in LT World',
          'size':(1024, 768),

        'menubar': {'type':'MenuBar',
         'menus': [
             {'type':'Menu',
             'name':'menuFile',
             'label':'File',
             'items': [
                  {'type':'MenuItem',
                   'name':'menuFileExit',
                   'label':'E&xit\tAlt+X',
                   'command':'exit',
                  },
              ]
             },
         ]
     },
         'components': [

{'type':'Button', 
    'name':'AnswerButton', 
    'position':(540, 240), 
    'size':(115, 38), 
    'font':{'family': 'sansSerif', 'size': 18}, 
    'label':'Answer:', 
    },

{'type':'TextArea', 
    'name':'AnswerTextArea', 
    'position':(540, 305), 
    'size':(442, 412), 
    'font':{'family': 'sansSerif', 'size': 12}, 
    },

{'type':'TextArea', 
    'name':'SparqlTextArea', 
    'position':(55, 305), 
    'size':(430, 408), 
    'font':{'family': 'sansSerif', 'size': 12}, 
    },

{'type':'StaticText', 
    'name':'SparqlStaticText', 
    'position':(55, 240), 
    'size':(243, 53), 
    'font':{'family': 'sansSerif', 'size': 18}, 
    'text':'SPARQL translation:', 
    },

{'type':'StaticText', 
    'name':'QueryStaticText', 
    'position':(50, 185), 
    'size':(164, -1), 
    'font':{'family': 'sansSerif', 'size': 18}, 
    'text':'Query:', 
    },

{'type':'Choice', 
    'name':'Queries', 
    'position':(150, 185), 
    'size':(851, 36), 
    'font':{'family': 'sansSerif', 'size': 18}, 
    'items':[u'Query one', u'Query two', u'Query three'], 
    },

{'type':'ImageButton', 
    'name':'PyPy', 
    'position':(50, 25), 
    'size':(166, 128), 
    'border':'none', 
    'file':'pypy.gif', 
    },

{'type':'ImageButton', 
    'name':'DFKI', 
    'position':(755, 45), 
    'size':(188, 84), 
    'border':'none', 
    'file':'dfki-logo.jpg', 
    },

{'type':'ImageButton', 
    'name':'LTWorld', 
    'position':(335, 59), 
    'size':(311, 59), 
    'border':'none', 
    'file':'lt-world.jpg', 
    },

] # end components
} # end background
] # end backgrounds
} }
