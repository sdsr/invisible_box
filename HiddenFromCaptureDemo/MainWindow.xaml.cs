using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace HiddenFromCaptureDemo
{
    public partial class MainWindow : Window
    {
        // Alt+Tab 숨김용 확장 스타일
        const int GWL_EXSTYLE = -20;
        const long WS_EX_TOOLWINDOW = 0x00000080;  // Alt+Tab 숨김
        const long WS_EX_APPWINDOW = 0x00040000;   // Alt+Tab 표시

        [DllImport("user32.dll")]
        static extern IntPtr GetWindowLongPtr(IntPtr hWnd, int nIndex);

        [DllImport("user32.dll")]
        static extern IntPtr SetWindowLongPtr(IntPtr hWnd, int nIndex, IntPtr dwNewLong);

        // 전역 종료 핫키
        [DllImport("user32.dll")]
        private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

        [DllImport("user32.dll")]
        private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

        private const int HOTKEY_ID = 9000;
        private const uint MOD_CONTROL = 0x0002;
        private const uint MOD_ALT = 0x0001;
        private const uint VK_Q = 0x51; // 'Q'

        // 화면 캡처 제외 설정 API
        [DllImport("user32.dll")]
        private static extern bool SetWindowDisplayAffinity(IntPtr hWnd, uint dwAffinity);
        private const uint WDA_NONE = 0x00000000;
        private const uint WDA_MONITOR = 0x00000001;
        private const uint WDA_EXCLUDEFROMCAPTURE = 0x00000011; // Win10 2004+

        public MainWindow()
        {
            InitializeComponent();
            // 창 초기화 후 스타일/핫키 적용
            this.SourceInitialized += (_, __) =>
            {
                ApplyToolWindowStyle();   // 작업표시줄/Alt+Tab 숨김
                // 최상위 창을 화면 캡처에서 제외
                var hwnd = new WindowInteropHelper(this).Handle;
                if (hwnd != IntPtr.Zero)
                    SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE);
                RegisterGlobalHotkey();   // Ctrl+Alt+Q 종료
            };
            this.Closed += (_, __) => UnregisterGlobalHotkey();
        }

        private void ApplyToolWindowStyle()
        {
            var hwnd = new WindowInteropHelper(this).Handle;
            if (hwnd == IntPtr.Zero) return;

            long ex = GetWindowLongPtr(hwnd, GWL_EXSTYLE).ToInt64();
            ex |= WS_EX_TOOLWINDOW;      // Alt+Tab에서 숨김
            ex &= ~WS_EX_APPWINDOW;      // Alt+Tab 강제 표시 제거
            SetWindowLongPtr(hwnd, GWL_EXSTYLE, new IntPtr(ex));
        }

        private void RegisterGlobalHotkey()
        {
            var helper = new WindowInteropHelper(this);
            HwndSource source = HwndSource.FromHwnd(helper.Handle);
            source.AddHook(HwndHook);
            RegisterHotKey(helper.Handle, HOTKEY_ID, MOD_CONTROL | MOD_ALT, VK_Q);
        }

        private void UnregisterGlobalHotkey()
        {
            var helper = new WindowInteropHelper(this);
            UnregisterHotKey(helper.Handle, HOTKEY_ID);
        }

        private IntPtr HwndHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
        {
            const int WM_HOTKEY = 0x0312;
            if (msg == WM_HOTKEY && wParam.ToInt32() == HOTKEY_ID)
            {
                Application.Current.Shutdown();
                handled = true;
            }
            return IntPtr.Zero;
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
