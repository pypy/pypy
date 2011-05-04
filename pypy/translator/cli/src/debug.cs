using System;
using System.IO;
using System.Collections.Generic;
using System.Diagnostics;

// this code is modeled after translator/c/src/debug.h
namespace pypy.runtime
{

    public class Debug
    {
        public static void DEBUG_FATALERROR(string msg)
        {
            throw new Exception("debug_fatalerror: " + msg);
        }
    }

    public class DebugPrint
    {
        static Stopwatch watch = null;
        static TextWriter debug_file = null;
        static int have_debug_prints = -1;
        static bool debug_ready = false;
        static bool debug_profile = false;
        static string[] active_categories = null;

        public static void close_file()
        {
            if (debug_file != null)
                debug_file.Close();
        }

        public static bool startswithoneof(string category, string[] active_categories)
        {
            foreach(string cat in active_categories)
                if (category.StartsWith(cat))
                    return true;
            return false;
        }

        public static bool HAVE_DEBUG_PRINTS()
        {
            if ((have_debug_prints & 1) != 0) {
                debug_ensure_opened();
                return true;
            }
            return false;
        }

        public static void DEBUG_START(string category)
        {
            debug_ensure_opened();
            /* Enter a nesting level.  Nested debug_prints are disabled by
               default because the following left shift introduces a 0 in the
               last bit.  Note that this logic assumes that we are never going
               to nest debug_starts more than 31 levels (63 on 64-bits). */
            have_debug_prints <<= 1;
            if (!debug_profile) {
                /* non-profiling version */
                if (active_categories == null || 
                    !startswithoneof(category, active_categories)) {
                    /* wrong section name, or no PYPYLOG at all, skip it */
                    return;
                }
                /* else make this subsection active */
                have_debug_prints |= 1;
            }
            display_startstop("{", "", category);
        }

        public static void DEBUG_STOP(string category)
        {
            if (debug_profile || (have_debug_prints & 1) != 0)
                display_startstop("", "}", category);
            have_debug_prints >>= 1;
        }


        static void setup_profiling()
        {
            watch = new Stopwatch();
            watch.Start();
        }

        static void debug_open()
        {
            string filename = Environment.GetEnvironmentVariable("PYPYLOG");
            if (filename != null && filename.Length > 0){
                int colon = filename.IndexOf(':');
                if (colon == -1) {
                    /* PYPYLOG=filename --- profiling version */
                    debug_profile = true;
                }
                else {
                    /* PYPYLOG=prefix:filename --- conditional logging */
                    string debug_prefix = filename.Substring(0, colon);
                    active_categories = debug_prefix.Split(',');
                    filename = filename.Substring(colon+1);
                }
                if (filename != "-")
                    debug_file = File.CreateText(filename);
            }
            if (debug_file == null)
                debug_file = System.Console.Error;
            debug_ready = true;
            setup_profiling();
        }
        
        static void debug_ensure_opened() {
            if (!debug_ready)
                debug_open();
        }

        static long read_timestamp() {
            return watch.ElapsedMilliseconds;
        }

        static void display_startstop(string prefix,
                                      string postfix,
                                      string category)
        {
            long timestamp = read_timestamp();
            debug_file.WriteLine("[{0:X}] {1}{2}{3}", 
                                 timestamp,
                                 prefix,
                                 category,
                                 postfix);
        }

        // **************************************************
        // debug_print family
        // **************************************************
        public static void DEBUG_PRINT(object a0)
        {
            if (HAVE_DEBUG_PRINTS())
                debug_file.WriteLine("{0}", a0);
        }

        public static void DEBUG_PRINT(object a0, object a1)
        {
            if (HAVE_DEBUG_PRINTS())
                debug_file.WriteLine("{0} {1}", a0, a1);
        }

        public static void DEBUG_PRINT(object a0, object a1, object a2)
        {
            if (HAVE_DEBUG_PRINTS())
                debug_file.WriteLine("{0} {1} {2}", a0, a1, a2);
        }

        public static void DEBUG_PRINT(object a0, object a1, object a2, object a3)
        {
            if (HAVE_DEBUG_PRINTS())
                debug_file.WriteLine("{0} {1} {2} {3}",
                                        a0, a1, a2, a3);
        }

        public static void DEBUG_PRINT(object a0, object a1, object a2, object a3,
                                       object a4)
        {
            if (HAVE_DEBUG_PRINTS())
                debug_file.WriteLine("{0} {1} {2} {3} {4}", 
                                        a0, a1, a2, a3, a4);
        }

        public static void DEBUG_PRINT(object a0, object a1, object a2, object a3,
                                       object a4, object a5)
        {
            if (HAVE_DEBUG_PRINTS())
                debug_file.WriteLine("{0} {1} {2} {3} {4} {5}", 
                                        a0, a1, a2, a3, a4, a5);
        }

        public static void DEBUG_PRINT(object a0, object a1, object a2, object a3,
                                       object a4, object a5, object a6)
        {
            if (HAVE_DEBUG_PRINTS())
                debug_file.WriteLine("{0} {1} {2} {3} {4} {5} {6}", 
                                        a0, a1, a2, a3, a4, a5, a6);
        }

        public static void DEBUG_PRINT(object a0, object a1, object a2, object a3,
                                       object a4, object a5, object a6, object a7)
        {
            if (HAVE_DEBUG_PRINTS())
                debug_file.WriteLine("{0} {1} {2} {3} {4} {5} {6} {7}", 
                                        a0, a1, a2, a3, a4, a5, a6, a7);
        }
    }
}
