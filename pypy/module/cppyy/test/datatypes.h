const int N = 5;


//===========================================================================
struct cppyy_test_pod {
   int    m_int;
   double m_double;
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
    bool           get_bool();
    char           get_char();
    unsigned char  get_uchar();
    short          get_short();
    unsigned short get_ushort();
    int            get_int();
    unsigned int   get_uint();
    long           get_long();
    unsigned long  get_ulong();
    float          get_float();
    double         get_double();
    what           get_enum();

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

    cppyy_test_pod get_pod_val();
    cppyy_test_pod* get_pod_ptr();
    cppyy_test_pod& get_pod_ref();
    cppyy_test_pod*& get_pod_ptrref();

// setters
    void set_bool(bool b);
    void set_char(char c);
    void set_uchar(unsigned char uc);
    void set_short(short s);
    void set_ushort(unsigned short us);
    void set_int(int i);
    void set_uint(unsigned int ui);
    void set_long(long l);
    void set_ulong(unsigned long ul);
    void set_float(float f);
    void set_double(double d);
    void set_enum(what w);

public:
// basic types
    bool           m_bool;
    char           m_char;
    unsigned char  m_uchar;
    short          m_short;
    unsigned short m_ushort;
    int            m_int;
    unsigned int   m_uint;
    long           m_long;
    unsigned long  m_ulong;
    float          m_float;
    double         m_double;
    what           m_enum;

// array types
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
    static char           s_char;
    static unsigned char  s_uchar;
    static short          s_short;
    static unsigned short s_ushort;
    static int            s_int;
    static unsigned int   s_uint;
    static long           s_long;
    static unsigned long  s_ulong;
    static float          s_float;
    static double         s_double;
    static what           s_enum;

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
