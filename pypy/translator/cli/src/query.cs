using System;
using System.Reflection;
using System.Collections.Generic;

public class Query
{
    public static Dictionary<Type, bool> PendingTypes = new Dictionary<Type, bool>();

    public static int Main(string[] argv)
    { 
        if (argv.Length != 1) {
            Console.Error.WriteLine("Usage: query full-qualified-name");
            return 1;
        }
        
        string name = argv[0];
        Type t = Type.GetType(name);
        if (t == null) {
            Console.Error.WriteLine("Cannot load type {0}", name);
            return 2;
        }

        if (!t.IsPublic) {
            Console.Error.WriteLine("Cannot load a non-public type");
            return 2;
        }

        PrintType(t);
        return 0;
    }

    private static void PrintType(Type t)
    {
        Console.WriteLine("Assembly = '{0}'", t.Assembly.FullName);
        Console.WriteLine("FullName = '{0}'", t.FullName);
        Console.WriteLine("BaseType = '{0}'", GetBaseType(t));
        Console.WriteLine("OOType = '{0}'", GetOOType(t));
        Console.WriteLine("IsArray = {0}", t.IsArray);
        if (t.IsArray)
            Console.WriteLine("ElementType = '{0}'", t.GetElementType().FullName);
        PrintMethods("StaticMethods", t.GetMethods(BindingFlags.Static|BindingFlags.Public|BindingFlags.DeclaredOnly));
        PrintMethods("Methods", t.GetMethods(BindingFlags.Instance|BindingFlags.Public|BindingFlags.DeclaredOnly));
        PendingTypes.Remove(t);
        PrintDepend();
    }

    private static string GetBaseType(Type t)
    {
        if (t == typeof(object))
            return "ROOT"; // special case for System.Object to avoid circular dependencies
        else if (t.BaseType == null)
             return "System.Object"; // the only known case is the BaseType of an interface
        else
            return t.BaseType.FullName;
    }

    private static string GetOOType(Type t)
    {
        if (t == null)
            return "";
        else if (t == typeof(void))
            return "ootype.Void";
        else if (t == typeof(int))
            return "ootype.Signed";
        else if (t == typeof(uint))
            return "ootype.Unsigned";
        else if (t == typeof(long))
            return "ootype.SignedLongLong";
        else if (t == typeof(ulong))
            return "ootype.UnsignedLongLong";
        else if (t == typeof(bool))
            return "ootype.Bool";
        else if (t == typeof(double))
            return "ootype.Float";
        else if (t == typeof(char))
            return "ootype.Char"; // maybe it should be unichar?
        else if (t == typeof(string))
            return "ootype.String";
        else {
            PendingTypes[t] = true;
            string name = t.FullName.Replace(".", "_"); // TODO: ensure unicity
            if (t.IsArray)
                name = name.Replace("[]", "___array___");
            return name;
        }
    }

    private static void PrintMethods(string varname, MethodInfo[] methods)
    {
        Console.WriteLine("{0} = [", varname);
        // MethodName, [ARGS], RESULT
        foreach(MethodInfo meth in methods) {
            if (IgnoreMethod(meth))
                continue;
            Console.Write("    ('{0}', [", meth.Name);
            foreach(ParameterInfo par in meth.GetParameters()) {
                Console.Write("'{0}'", GetOOType(par.ParameterType));
                Console.Write(", ");
            }
            Console.WriteLine("], '{0}'),", GetOOType(meth.ReturnType));
        }
        Console.WriteLine("  ]");
    }

    private static bool IgnoreMethod(MethodInfo meth)
    {
        if (!meth.IsPublic)
            return true;

        // ignore all SpecialName but properties getter/setter
        if (meth.IsSpecialName && !meth.Name.StartsWith("get_") && !meth.Name.StartsWith("set_"))
            return true;

        if (IgnoreType(meth.ReturnType))
            return true;
        foreach(ParameterInfo par in meth.GetParameters())
            if (IgnoreType(par.ParameterType))
                return true;

        return false;
    }

    private static bool IgnoreType(Type t)
    {
        return !t.IsPrimitive 
            && t != typeof(void)
            &&(t == typeof(System.ValueType) ||
               t == typeof(System.Array) ||
               t.FullName.StartsWith("System.Array+InternalArray") ||
               t.IsValueType ||
               t.IsByRef ||
               t.IsPointer ||
               t.IsGenericType ||
               t.IsGenericTypeDefinition);
    }

    private static void PrintDepend()
    {
        Console.Write("Depend = [");
        foreach(Type t in PendingTypes.Keys)
            Console.Write("'{0}', ", t.FullName);
        Console.WriteLine("]");
    }
}
