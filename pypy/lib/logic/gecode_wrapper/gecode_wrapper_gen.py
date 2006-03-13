# wrapper code generator for gecode library


GECODE_WRAP_HH = file("gecode_wrap_tmpl.hh").read()
GECODE_WRAP_CC = file("gecode_wrap_tmpl.cc").read()

VAR_CLASS_DEF = """
class Py%(var_type)s : public PyVar {
public:
    /* constructor */
    Py%(var_type)s( PySpace* space, %(var_factory_args)s );
    virtual void update( PySpace* space, bool share, Py%(var_type)s& _var );

    virtual %(value_type)s val() { return var.val(); }

    %(var_type)s  var;
};
"""

VAR_CLASS_BODY = """
Py%(var_type)s::Py%(var_type)s( PySpace* space, %(var_factory_args)s ):var(space, %(var_args)s )
{
}

void
Py%(var_type)s::update( PySpace* space, bool share, Py%(var_type)s& _var )
{
    var.update( space, share, _var );
}

"""

VARACCESS = """
   %(var_type)s* get%(var_type)s( int i ) { return &(dynamic_cast<Py%(var_type)s*>(&vars[i])->var); }
"""

VARTYPES = [ { 'var_type'    : 'IntVar',
               'value_type'  : 'int',
               'args'        : [ ('int', 'min'), ('int', 'max') ],
               'propagators' : [],
               },
               { 'var_type'    : 'BoolVar',
                 'value_type' : 'int',
                 'args' : [('int', 'min'), ('int', 'max') ],
                 'propagators' : [],
                 },
##              { 'var_type' : 'SetVar',
##              },
             ]

for vardef in VARTYPES:
    vardef['var_factory_args'] = ", ".join( [ "%s _%s" % (typ,nam) for typ, nam in vardef['args'] ] )
    vardef['var_args'] = ", ".join( [ "_%s" % nam for typ, nam in vardef['args'] ] )
    vardef['var_storage'] = '_'+vardef['var_type'] + "_vect"
    vardef['var_storage_temp'] = '_'+vardef['var_type'] + "_tmp_vect"


VAR_FACTORY_DEF = """
    int %(var_type)s( %(var_factory_args)s );
    int %(var_type)s_temp( %(var_factory_args)s );
"""

VAR_FACTORY_BODY = """
int PySpace::%(var_type)s( %(var_factory_args)s ) {
        %(var_storage)s.push_back( %(var_type)s( %(var_args)s ) );
        return %(var_storage)s.size();
    }

int PySpace::%(var_type)s_temp( %(var_factory_args)s ) {
        %(var_storage_temp)s.push_back( %(var_type)s( %(var_args)s ) );
        return %(var_storage)s.size();
    }
"""

VAR_ACCESSOR = """
    void get%(var_type)sValues( int idx, int n, int* vars, %(var_type)s* values ) {
        for(int i=0;i<n;++i) {
            %(var_type)s* v = get%(var_type)s( vars[i] );
            if (v) {
                values[i] = v->val();
            }
        }
    }
"""

PROPCOND = []




def create_var_subclasses( d ):
    out_hh = []
    out_cc = []
    for vardef in VARTYPES:
        out_hh.append( VAR_CLASS_DEF % vardef )
        out_cc.append( VAR_CLASS_BODY % vardef )
    d['var_subclasses_decl'] = "\n".join( out_hh )
    d['var_subclasses_body'] = "\n".join( out_cc )

def create_var_factories( d ):
    out_hh = []
    out_cc = []
    for vardef in VARTYPES:
        out_hh.append( VAR_FACTORY_DEF % vardef )
        out_cc.append( VAR_FACTORY_BODY % vardef )

    d['var_factories_decl'] = "\n".join( out_hh )
    d['var_factories_body'] = "\n".join( out_cc )

def create_var_propagators( d ):
    out_hh = []
    out_cc = []

    d['var_propagators_decl'] = "\n".join( out_hh )
    d['var_propagators_body'] = "\n".join( out_cc )


if __name__ == "__main__":
    wrapper_hh = file("_gecode_wrap.hh", "w")
    wrapper_cc = file("_gecode_wrap.cc", "w")
    d = {}

    create_var_subclasses( d )
    create_var_factories( d )
    create_var_propagators( d )

    wrapper_hh.write( GECODE_WRAP_HH % d )
    wrapper_cc.write( GECODE_WRAP_CC % d )
