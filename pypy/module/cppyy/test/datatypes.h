const int N = 5;


//===========================================================================
struct cppyy_test_pod {
   int    m_int;
   double m_double;
};


//===========================================================================
enum fruit { kApple=78, kBanana=29, kCitrus=34 };


//===========================================================================
class four_vector {
public:
    four_vector(double x, double y, double z, double t) :
        m_x(x), m_y(y), m_z(z), m_t(t), m_cc_called(false) {}
    four_vector(const four_vector& s) :
        m_x(s.m_x), m_y(s.m_y), m_z(s.m_z), m_t(s.m_t), m_cc_called(true) {}

    double operator[](int i) {
       if (i == 0) return m_x;
       if (i == 1) return m_y;
       if (i == 2) return m_z;
       if (i == 3) return m_t;
       return -1;
    }

    bool operator==(const four_vector& o) {
       return (m_x == o.m_x && m_y == o.m_y &&
               m_z == o.m_z && m_t == o.m_t);
    }

public:
    bool m_cc_called;

private:
    double m_x, m_y, m_z, m_t;
};


//===========================================================================
class cppyy_test_data {
public:
    cppyy_test_data();
    ~cppyy_test_data();

// special cases
    enum what { kNothing=6, kSomething=111, kLots=42 };

// helper
    void destroy_arrays();

// getters
    bool                 get_bool();
    char                 get_char();
    unsigned char        get_uchar();
    short                get_short();
    unsigned short       get_ushort();
    int                  get_int();
    unsigned int         get_uint();
    long                 get_long();
    unsigned long        get_ulong();
    long long            get_llong();
    unsigned long long   get_ullong();
    float                get_float();
    double               get_double();
    what                 get_enum();
    void*                get_voidp();

    bool*           get_bool_array();
    bool*           get_bool_array2();
    short*          get_short_array();
    short*          get_short_array2();
    unsigned short* get_ushort_array();
    unsigned short* get_ushort_array2();
    int*            get_int_array();
    int*            get_int_array2();
    unsigned int*   get_uint_array();
    unsigned int*   get_uint_array2();
    long*           get_long_array();
    long*           get_long_array2();
    unsigned long*  get_ulong_array();
    unsigned long*  get_ulong_array2();

    float*  get_float_array();
    float*  get_float_array2();
    double* get_double_array();
    double* get_double_array2();

    cppyy_test_pod get_pod_val();                 // for m_pod
    cppyy_test_pod* get_pod_val_ptr();
    cppyy_test_pod& get_pod_val_ref();
    cppyy_test_pod*& get_pod_ptrref();

    cppyy_test_pod* get_pod_ptr();                // for m_ppod

// setters
    void set_bool(bool b);
    void set_char(char c);
    void set_uchar(unsigned char uc);
    void set_short(short s);
    void set_short_c(const short& s);
    void set_ushort(unsigned short us);
    void set_ushort_c(const unsigned short& us);
    void set_int(int i);
    void set_int_c(const int& i);
    void set_uint(unsigned int ui);
    void set_uint_c(const unsigned int& ui);
    void set_long(long l);
    void set_long_c(const long& l);
    void set_llong(long long ll);
    void set_llong_c(const long long& ll);
    void set_ulong(unsigned long ul);
    void set_ulong_c(const unsigned long& ul);
    void set_ullong(unsigned long long ll);
    void set_ullong_c(const unsigned long long& ll);
    void set_float(float f);
    void set_float_c(const float& f);
    void set_double(double d);
    void set_double_c(const double& d);
    void set_enum(what w);
    void set_voidp(void* p);

    void set_pod_val(cppyy_test_pod);             // for m_pod
    void set_pod_ptr_in(cppyy_test_pod*);
    void set_pod_ptr_out(cppyy_test_pod*);
    void set_pod_ref(const cppyy_test_pod&);
    void set_pod_ptrptr_in(cppyy_test_pod**);
    void set_pod_void_ptrptr_in(void**);
    void set_pod_ptrptr_out(cppyy_test_pod**);
    void set_pod_void_ptrptr_out(void**);

    void set_pod_ptr(cppyy_test_pod*);            // for m_ppod

// passers
    short*          pass_array(short*);
    unsigned short* pass_array(unsigned short*);
    int*            pass_array(int*);
    unsigned int*   pass_array(unsigned int*);
    long*           pass_array(long*);
    unsigned long*  pass_array(unsigned long*);
    float*          pass_array(float*);
    double*         pass_array(double*);

    short*          pass_void_array_h(void* a) { return pass_array((short*)a); }
    unsigned short* pass_void_array_H(void* a) { return pass_array((unsigned short*)a); }
    int*            pass_void_array_i(void* a) { return pass_array((int*)a); }
    unsigned int*   pass_void_array_I(void* a) { return pass_array((unsigned int*)a); }
    long*           pass_void_array_l(void* a) { return pass_array((long*)a); }
    unsigned long*  pass_void_array_L(void* a) { return pass_array((unsigned long*)a); }
    float*          pass_void_array_f(void* a) { return pass_array((float*)a); }
    double*         pass_void_array_d(void* a) { return pass_array((double*)a); }

// strings
    const char* get_valid_string(const char* in);
    const char* get_invalid_string();

public:
// basic types
    bool                 m_bool;
    char                 m_char;
    unsigned char        m_uchar;
    short                m_short;
    unsigned short       m_ushort;
    int                  m_int;
    unsigned int         m_uint;
    long                 m_long;
    unsigned long        m_ulong;
    long long            m_llong;
    unsigned long long   m_ullong;
    float                m_float;
    double               m_double;
    what                 m_enum;
    void*                m_voidp;

// array types
    bool            m_bool_array[N];
    bool*           m_bool_array2;
    short           m_short_array[N];
    short*          m_short_array2;
    unsigned short  m_ushort_array[N];
    unsigned short* m_ushort_array2;
    int             m_int_array[N];
    int*            m_int_array2;
    unsigned int    m_uint_array[N];
    unsigned int*   m_uint_array2;
    long            m_long_array[N];
    long*           m_long_array2;
    unsigned long   m_ulong_array[N];
    unsigned long*  m_ulong_array2;
 
    float   m_float_array[N];
    float*  m_float_array2;
    double  m_double_array[N];
    double* m_double_array2;

// object types
    cppyy_test_pod m_pod;
    cppyy_test_pod* m_ppod;

public:
    static char                    s_char;
    static unsigned char           s_uchar;
    static short                   s_short;
    static unsigned short          s_ushort;
    static int                     s_int;
    static unsigned int            s_uint;
    static long                    s_long;
    static unsigned long           s_ulong;
    static long long               s_llong;
    static unsigned long long      s_ullong;
    static float                   s_float;
    static double                  s_double;
    static what                    s_enum;
    static void*                   s_voidp;

private:
    bool m_owns_arrays;
};


//= global functions ========================================================
long get_pod_address(cppyy_test_data& c);
long get_int_address(cppyy_test_data& c);
long get_double_address(cppyy_test_data& c);


//= global variables/pointers ===============================================
extern int g_int;
void set_global_int(int i);
int get_global_int();

extern cppyy_test_pod* g_pod;
bool is_global_pod(cppyy_test_pod* t);
void set_global_pod(cppyy_test_pod* t);
cppyy_test_pod* get_global_pod();
cppyy_test_pod* get_null_pod();
