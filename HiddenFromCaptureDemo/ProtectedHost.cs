using System;
using System.Runtime.InteropServices;
using System.Windows.Interop;

namespace HiddenFromCaptureDemo
{
    public class ProtectedHost : HwndHost
    {
        [DllImport("ProtectedSwapChain.dll", CallingConvention = CallingConvention.Cdecl)]
        public static extern IntPtr CreateProtectedWindow(IntPtr parent);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool DestroyWindow(IntPtr hWnd);

        private IntPtr hwndChild;

        protected override HandleRef BuildWindowCore(HandleRef hwndParent)
        {
            hwndChild = CreateProtectedWindow(hwndParent.Handle);
            if (hwndChild == IntPtr.Zero)
                throw new InvalidOperationException("보호 스왑체인 호스트 윈도우 생성 실패");
            return new HandleRef(this, hwndChild);
        }

        protected override void DestroyWindowCore(HandleRef hwnd)
        {
            if (hwnd.Handle != IntPtr.Zero)
                DestroyWindow(hwnd.Handle);
        }
    }
}
