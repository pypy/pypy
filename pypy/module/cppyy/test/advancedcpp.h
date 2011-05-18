#include <vector>


//===========================================================================
class base_class {                 // for simple inheritance testing
public:
   base_class() { m_a = 1; m_da = 1.1; }
   virtual ~base_class() {}
   virtual int get_value() = 0;

public:
   int m_a;
   double m_da;
};

class derived_class : public base_class {
public:
   derived_class() { m_b = 2; m_db = 2.2;}
   virtual int get_value() { return m_b; }

public:
   int m_b;
   double m_db;
};


//===========================================================================
class a_class {                    // for esoteric inheritance testing
public:
   a_class() { m_a = 1; m_da = 1.1; }
   virtual ~a_class() {}
   virtual int get_value() = 0;

public:
   int m_a;
   double m_da;
};

class b_class : public virtual a_class {
public:
   b_class() { m_b = 2; m_db = 2.2;}
   virtual int get_value() { return m_b; }

public:
   int m_b;
   double m_db;
};

class c_class_1 : public virtual a_class, public virtual b_class {
public:
   c_class_1() { m_c = 3; }
   virtual int get_value() { return m_c; }

public:
   int m_c;
};

class c_class_2 : public virtual b_class, public virtual a_class {
public:
   c_class_2() { m_c = 3; }
   virtual int get_value() { return m_c; }

public:
   int m_c;
};

typedef c_class_2 c_class;

class d_class : public virtual c_class, public virtual a_class {
public:
   d_class() { m_d = 4; }
   virtual int get_value() { return m_d; }

public:
   int m_d;
};

int get_a( a_class& a );
int get_b( b_class& b );
int get_c( c_class& c );
int get_d( d_class& d );


//===========================================================================
template< typename T >             // for template testing
class T1 {
public:
   T1( T t = T(0) ) : m_t1( t ) {}
   T value() { return m_t1; }

public:
   T m_t1;
};

template< typename T >
class T2 {
public:
   T m_t2;
};

namespace {
   T1< int > tt1;
   T2< T1< int > > tt2;
}

// helpers for checking pass-by-ref
void set_int_through_ref(int& i, int val);
int pass_int_through_const_ref(const int& i);
void set_long_through_ref(long& l, long val);
long pass_long_through_const_ref(const long& l);
void set_double_through_ref(double& d, double val);
double pass_double_through_const_ref(const double& d);


//===========================================================================
class some_abstract_class {        // to test abstract class handling
public:
   virtual void a_virtual_method() = 0;
};

class some_concrete_class : public some_abstract_class {
public:
   virtual void a_virtual_method() {}
};


//===========================================================================
/*
TODO: methptrgetter support for std::vector<>
class ref_tester {                 // for assignment by-ref testing
public:
   ref_tester() : m_i(-99) {}
   ref_tester(int i) : m_i(i) {}
   ref_tester(const ref_tester& s) : m_i(s.m_i) {}
   ref_tester& operator=(const ref_tester& s) {
      if (&s != this) m_i = s.m_i;
      return *this;
   }
   ~ref_tester() {}

public:
   int m_i;
};

template class std::vector< ref_tester >;
*/


//===========================================================================
class some_convertible {           // for math conversions testing
public:
   some_convertible() : m_i(-99), m_d(-99.) {}

   operator int()    { return m_i; }
   operator long()   { return m_i; }
   operator double() { return m_d; }

public:
   int m_i;
   double m_d;
};


class some_comparable {
};

bool operator==(const some_comparable& c1, const some_comparable& c2 );
bool operator!=( const some_comparable& c1, const some_comparable& c2 );


//===========================================================================
extern double my_global_double;    // a couple of globals for access testing
extern double my_global_array[500];


//===========================================================================
class some_class_with_data {       // for life-line testing
public:
   class some_data {
   public:
      some_data()                 { ++s_num_data; }
      some_data(const some_data&) { ++s_num_data; }
      ~some_data()                { --s_num_data; }

      static int s_num_data;
   };

   some_class_with_data gime_copy() {
      return *this;
   }

   const some_data& gime_data() { /* TODO: methptrgetter const support */
      return m_data;
   }

   some_data m_data;
};
