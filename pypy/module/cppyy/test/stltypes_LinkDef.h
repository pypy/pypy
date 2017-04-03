#ifdef __CINT__

#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;

#pragma link C++ class std::vector<just_a_class>;
#pragma link C++ class std::vector<just_a_class>::iterator;
#pragma link C++ class std::vector<just_a_class>::const_iterator;

#pragma link C++ class map<std::string, unsigned int>;
#pragma link C++ class map<std::string, unsigned int>::iterator;
#pragma link C++ class map<std::string, unsigned int>::const_iterator;
#pragma link C++ class pair<std::string, unsigned int>;

#pragma link C++ class map<std::string, unsigned long>;
#pragma link C++ class map<std::string, unsigned long>::iterator;
#pragma link C++ class map<std::string, unsigned long>::const_iterator;
#pragma link C++ class pair<std::string, unsigned long>;

#pragma link C++ class just_a_class;
#pragma link C++ class stringy_class;
#pragma link C++ class stl_like_class<int>;

#endif
