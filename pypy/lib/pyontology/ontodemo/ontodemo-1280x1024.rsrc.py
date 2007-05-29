{'application':{'type':'Application',
          'name':'Minimal',
    'backgrounds': [
    {'type':'Background',
          'name':'bgMin',
          'title':u'Query Answering in LT World',
          'size':(1280, 1024),

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
    'position':(675, 245), 
    'size':(115, 38), 
    'font':{'family': 'sansSerif', 'size': 18}, 
    'label':'Answer:', 
    },

{'type':'TextArea', 
    'name':'AnswerTextArea', 
    'position':(675, 310), 
    'size':(580, 630), 
    'font':{'family': 'sansSerif', 'size': 18}, 
    },

{'type':'TextArea', 
    'name':'SparqlTextArea', 
    'position':(50, 310), 
    'size':(580, 630), 
    'font':{'family': 'sansSerif', 'size': 18}, 
    },

{'type':'StaticText', 
    'name':'SparqlStaticText', 
    'position':(55, 250), 
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
    'position':(155, 180), 
    'size':(1086, 36), 
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
