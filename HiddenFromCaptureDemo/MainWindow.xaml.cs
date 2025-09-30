using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;

namespace HiddenFromCaptureDemo
{
    public partial class MainWindow : Window
    {
        private const uint WDA_NONE = 0;
        private const uint WDA_MONITOR = 1;                 // 폴백(검은칸 가능)
        private const uint WDA_EXCLUDEFROMCAPTURE = 0x00000011; // Win10 2004+

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool SetWindowDisplayAffinity(IntPtr hWnd, uint dwAffinity);

        [DllImport("user32.dll")]
        private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

        [DllImport("user32.dll")]
        private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

        private bool _isExcluded;
        private const int HOTKEY_ID = 9000;
        private const uint MOD_CONTROL = 0x0002;
        private const uint MOD_ALT = 0x0001;
        private const uint VK_Q = 0x51; // Q 키

        public MainWindow()
        {
            InitializeComponent();
            // 화면 캡처 제외 적용
            this.SourceInitialized += (_, __) =>
            {
                TrySetExcludeFromCapture(true);
                RegisterGlobalHotkey(); // 전역 종료 핫키 등록
            };
            this.Closed += (_, __) => UnregisterGlobalHotkey();
        }

        private void BtnToggle_Click(object sender, RoutedEventArgs e)
            => TrySetExcludeFromCapture(!_isExcluded);

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();

        private void TrySetExcludeFromCapture(bool enable)
        {
            var hwnd = new WindowInteropHelper(this).Handle;
            if (hwnd == IntPtr.Zero) { MessageBox.Show("HWND 없음"); return; }

            if (!SetWindowDisplayAffinity(hwnd, enable ? WDA_EXCLUDEFROMCAPTURE : WDA_NONE))
            {
                int err = Marshal.GetLastWin32Error();
                if (enable)
                {
                    MessageBox.Show($"WDA_EXCLUDEFROMCAPTURE 실패(GetLastError={err})");
                    _isExcluded = false;
                    if (btnToggle != null) btnToggle.Content = "숨김 적용 (Enable)";
                    return;
                }
            }

            _isExcluded = enable;
            if (btnToggle != null)
                btnToggle.Content = enable ? "숨김 해제 (Disable)" : "숨김 적용 (Enable)";
        }

        private void RegisterGlobalHotkey()
        {
            var helper = new WindowInteropHelper(this);
            HwndSource source = HwndSource.FromHwnd(helper.Handle);
            source.AddHook(HwndHook);

            // Ctrl+Alt+Q 로 종료
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
                Application.Current.Shutdown(); // 앱 종료
                handled = true;
            }
            return IntPtr.Zero;
        }
    }
}
