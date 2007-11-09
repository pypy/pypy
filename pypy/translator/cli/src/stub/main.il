// This is a stub files whose only purpose is to let pypylib to be
// compiled with the right references.

// This is useful when you want to access from pypylib to some
// method/class that *you* know they will exists in the generated
// file: the problem is that the C# compiler doesn't know about those
// functions/methods, so it will refuse to compile the file. The
// solution is to add a fake reference to 'main.exe', which contains
// stubs that make the compiler happy. Once pypylib is compiled, it
// can be dinamically linked against the real 'main.exe' which
// contains the correct references.

.assembly extern mscorlib {}
.assembly main {}

.method public static void main(string[] argv) il managed
{
    .entrypoint

    ldstr "This is only a stub, it should not be executed directly"
    call void [mscorlib]System.Console::WriteLine(string)
    ret
}


.namespace pypy.runtime
{
    .class public Helpers
    {
        .method public static void raise_OSError(int32 errno_1) il managed
        {
            ldstr "This is only a stub, it should not be called"
            newobj instance void class [mscorlib]System.ApplicationException::.ctor(string)
            throw
            ret
        }

        .method public static void raise_RuntimeError() il managed
        {
            ldstr "This is only a stub, it should not be called"
            newobj instance void class [mscorlib]System.ApplicationException::.ctor(string)
            throw
            ret
        }

        .method public static void raise_OverflowError() il managed
        {
            ldstr "This is only a stub, it should not be called"
            newobj instance void class [mscorlib]System.ApplicationException::.ctor(string)
            throw
            ret
        }

        .method public static void raise_ValueError() il managed
        {
            ldstr "This is only a stub, it should not be called"
            newobj instance void class [mscorlib]System.ApplicationException::.ctor(string)
            throw
            ret
        }

        .method public static void raise_UnicodeDecodeError() il managed
        {
            ldstr "This is only a stub, it should not be called"
            newobj instance void class [mscorlib]System.ApplicationException::.ctor(string)
            throw
            ret
        }
    }
}
