*Building wrapper libs*
The backend currently requires LLVM 12. If you need to build this version from source, don't worry about installing it system wide. Just add `llvm-project/build/bin/llvm-config` to your path and the rest will get sorted out for you.

The backend needs a couple of wrapper libraries to work, located in llvm\_wrapper/.
Because I don't understand makefiles very well, the C++ wrapper has to be compiled by hand first with the following command:

	g++ wrapper_cpp.cpp $(llvm-config --cxxflags --ldflags --libs all) -I. -fPIC -shared -o libcppwrapper.so

Once `libcppwrapper.so` exists you can just run `make` to create `libwrapper.so`. 


