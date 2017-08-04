#include <list>
#include <map>
#include <string>
#include <utility>
#include <vector>

//- basic example class
class just_a_class {
public:
    int m_i;
};

//- class with lots of std::string handling
class stringy_class {
public:
   stringy_class(const char* s);

   std::string get_string1();
   void get_string2(std::string& s);

   void set_string1(const std::string& s);
   void set_string2(std::string s);

   std::string m_string;
};

//- class that has an STL-like interface
class no_dict_available;
    
template<class T>
class stl_like_class {
public: 
   no_dict_available* begin() { return 0; }
   no_dict_available* end() { return 0; }
   int size() { return 4; }
   int operator[](int i) { return i; }
   std::string operator[](double) { return "double"; }
   std::string operator[](const std::string&) { return "string"; }
};      
