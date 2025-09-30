using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Input;

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

        // WinEvent 훅으로 새 창에도 WDA 적용
        private delegate void WinEventDelegate(IntPtr hWinEventHook, uint eventType, IntPtr hwnd, int idObject, int idChild, uint dwEventThread, uint dwmsEventTime);
        [DllImport("user32.dll")]
        private static extern IntPtr SetWinEventHook(uint eventMin, uint eventMax, IntPtr hmodWinEventProc, WinEventDelegate lpfnWinEventProc, uint idProcess, uint idThread, uint dwFlags);
        [DllImport("user32.dll")]
        private static extern bool UnhookWinEvent(IntPtr hWinEventHook);
        private const uint EVENT_OBJECT_SHOW = 0x8002;
        private const uint WINEVENT_OUTOFCONTEXT = 0;
        private IntPtr _hook;
        private WinEventDelegate _hookDelegate;

        // 프라이버시 모드 토글(Ctrl+Alt+P)
        private const int HOTKEY_PRIVACY = 9001;
        private const uint VK_P = 0x50;
        private bool _privacyMode = false;

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
                // 팝업/Owned HWND에도 자동 적용
                _hookDelegate = OnWinEvent;
                _hook = SetWinEventHook(EVENT_OBJECT_SHOW, EVENT_OBJECT_SHOW, IntPtr.Zero, _hookDelegate, 0, 0, WINEVENT_OUTOFCONTEXT);
                RegisterGlobalHotkey();   // Ctrl+Alt+Q 종료
                RegisterPrivacyHotkey();  // Ctrl+Alt+P 프라이버시 모드
            };
            this.Closed += (_, __) => UnregisterGlobalHotkey();
            this.Closed += (_, __) => { if (_hook != IntPtr.Zero) UnhookWinEvent(_hook); };
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

        private void RegisterPrivacyHotkey()
        {
            var helper = new WindowInteropHelper(this);
            HwndSource source = HwndSource.FromHwnd(helper.Handle);
            RegisterHotKey(helper.Handle, HOTKEY_PRIVACY, MOD_CONTROL | MOD_ALT, VK_P);
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
            else if (msg == WM_HOTKEY && wParam.ToInt32() == HOTKEY_PRIVACY)
            {
                _privacyMode = !_privacyMode;
                // 프라이버시 모드: 창 숨김/표시 토글 (간단 구현)
                if (_privacyMode) this.Hide(); else this.Show();
                handled = true;
            }
            return IntPtr.Zero;
        }

        // 드래그로 이동 지원(무테 창)
        private void RootGrid_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (e.ButtonState == MouseButtonState.Pressed)
                this.DragMove();
        }

        // WinEvent 콜백: 새로 나타난 창에 WDA 적용
        private void OnWinEvent(IntPtr hWinEventHook, uint eventType, IntPtr hwnd, int idObject, int idChild, uint dwEventThread, uint dwmsEventTime)
        {
            if (eventType != EVENT_OBJECT_SHOW) return;
            if (hwnd == IntPtr.Zero) return;
            SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE);
        }

        private void BtnClose_Click(object sender, RoutedEventArgs e) => Close();
    }
}
