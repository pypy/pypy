using System;
using System.Runtime.InteropServices;
using pypy.runtime;

namespace pypy.builtin
{
    public class ll_math
    {

        public static double ll_math_floor(double x)
        {
            return Math.Floor(x);
        }

        public static double ll_math_fmod(double x, double y)
        {
            return x % y;
        }

        public static Record_Float_Float ll_math_modf(double x)
        {
            Record_Float_Float result = new Record_Float_Float();
            result.item1 = (long)x; // truncate
            result.item0 = x - result.item1;
            return result;
        }

        // the following code is borrowed from 
        // http://web.telia.com/~u31115556/under_construction/Functions.Cephes.CFunctions.cs
        const double MAXNUM = double.MaxValue; // 1.79769313486232e308
        const int MEXP = 0x7ff;

        [StructLayout(LayoutKind.Explicit)] //, CLSCompliantAttribute(false)]
        struct DoubleUshorts 
        {
            [FieldOffset(0)] public double d;
            [FieldOffset(0)] public ushort u0;
            [FieldOffset(2)] public ushort u1;
            [FieldOffset(4)] public ushort u2;
            [FieldOffset(6)] public ushort u3;
        }

        public static unsafe Record_Float_Signed ll_math_frexp(double x)
        {
            Record_Float_Signed result = new Record_Float_Signed();
            if (x == 0.0) // Laj: Else pw2 = -1022
            {
                result.item0 = 0.0;
                result.item1 = 0;
                return result;
            }

            DoubleUshorts u;
            u.d = x;

            short *q = (short *)&u.u3;

            int i = (*q >> 4) & 0x7ff;

            i -= 0x3fe;
            result.item1 = i;
            unchecked
            {
                // Constant value '32783' cannot be converted to a 'short'
                *q &= (short)0x800f;
            }
            // Warning: Bitwise-or operator used on a sign-extended operand;
            // consider casting to a smaller unsigned type first
            *q |= 0x3fe0;
            result.item0 = u.d;
            return result;
        }

        static public unsafe double ll_math_ldexp(double x, int pw2)
        {
            DoubleUshorts u;
            u.d = x;

            short *q = (short *)&u.u3;
            double ud;
            int e;
            while ((e = (*q & 0x7ff0) >> 4) == 0)
            {
                if (u.d == 0.0)
                {
                    return 0.0;
                }
                // Input is denormal.
                if (pw2 > 0)
                {
                    u.d *= 2.0;
                    pw2 -= 1;
                }
                if (pw2 < 0)
                {
                    if (pw2 < -53)
                        return 0.0;
                    u.d /= 2.0;
                    pw2 += 1;
                }
                if (pw2 == 0)
                {
                    return u.d;
                }
            }

            e += pw2;

            // Handle overflow
            if (e >= MEXP)
                Helpers.raise_OverflowError();

            if (e < 1)
            {
                return 0.0;
            }
            else
            {
                unchecked
                {
                    // Constant value '32783' cannot be converted to a 'short'
                    *q &= (short)0x800f;
                }
                // Cannot implicitly convert type 'int' to 'short'
                // Warning: Bitwise-or operator used on a sign-extended operand;
                // consider casting to a smaller unsigned type first
                *q |= (short)((e & 0x7ff) << 4);
                return u.d;
            }
        }

        static public double ll_math_atan2(double y, double x)
        {
            return Math.Atan2(y, x);
        }

        static public double ll_math_acos(double x)
        {
            return Math.Acos(x);
        }

        static public double ll_math_asin(double x)
        {
            return Math.Asin(x);
        }

        static public double ll_math_atan(double x)
        {
            return Math.Atan(x);
        }

        static public double ll_math_ceil(double x)
        {
            return Math.Ceiling(x);
        }

        static public double ll_math_cos(double x)
        {
            return Math.Cos(x);
        }

        static public double ll_math_cosh(double x)
        {
            return Math.Cosh(x);
        }

        static public double ll_math_exp(double x)
        {
            double res = Math.Exp(x);
            if (double.IsPositiveInfinity(res))
                Helpers.raise_OverflowError();
            return res;
        }

        static public double ll_math_fabs(double x)
        {
            return Math.Abs(x);
        }

        static public double ll_math_hypot(double x, double y)
        {
            return Math.Sqrt(x*x+y*y); // XXX: is it numerically correct?
        }

        static public double ll_math_log(double x)
        {
            return Math.Log(x);
        }

        static public double ll_math_log10(double x)
        {
            return Math.Log10(x);
        }

        static public double ll_math_pow(double x, double y)
        {
            return Math.Pow(x, y);
        }

        static public double ll_math_sin(double x)
        {
            return Math.Sin(x);
        }

        static public double ll_math_sinh(double x)
        {
            return Math.Sinh(x);
        }

        static public double ll_math_sqrt(double x)
        {
            double res = Math.Sqrt(x);
            if (double.IsNaN(res))
                Helpers.raise_ValueError();
            return res;
        }

        static public double ll_math_tan(double x)
        {
            return Math.Tan(x);
        }

        static public double ll_math_tanh(double x)
        {
            return Math.Tanh(x);
        }

        static public bool ll_math_isnan(double x)
        {
            return double.IsNaN(x);
        }

        static public bool ll_math_isinf(double x)
        {
            return double.IsInfinity(x);
        }

        static public double ll_math_copysign(double x, double y)
        {
            if (x < 0.0)
                x = -x;
            if (y > 0.0 || (y == 0.0 && Math.Atan2(y, -1.0) > 0.0))
                return x;
            else
                return -x;
        }
    }
}
