using System;
using System.Runtime.InteropServices;
using System.Windows.Interop;

namespace HiddenFromCaptureDemo
{
    public class ProtectedHost : HwndHost
    {
        [DllImport("ProtectedSwapChain.dll", CharSet = CharSet.Unicode)]
        public static extern IntPtr CreateProtectedWindow(IntPtr parent);

        protected override HandleRef BuildWindowCore(HandleRef hwndParent)
        {
            IntPtr hwnd = CreateProtectedWindow(hwndParent.Handle);
            return new HandleRef(this, hwnd);
        }

        protected override void DestroyWindowCore(HandleRef hwnd) {}
    }
}
