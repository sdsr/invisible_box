#include "ProtectedSwapChain.h"
#include <d3d11.h>
#include <dxgi1_5.h>
#include <atomic>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")

// 간단한 렌더 스레드를 돌리며 보호 스왑체인을 지속 Present 합니다.
// OBS/디스플레이 캡처에서 보호 표면은 블랙/비표시로 처리됩니다.

struct Renderer {
    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* ctx = nullptr;
    IDXGISwapChain1* swap = nullptr;
    ID3D11RenderTargetView* rtv = nullptr;
    HANDLE thread = nullptr;
    std::atomic<bool> running{ false };
};

static LRESULT CALLBACK HostWndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    if (msg == WM_NCDESTROY) {
        Renderer* r = reinterpret_cast<Renderer*>(GetWindowLongPtrW(hWnd, GWLP_USERDATA));
        if (r) {
            r->running = false;
            if (r->thread) {
                WaitForSingleObject(r->thread, 2000);
                CloseHandle(r->thread);
            }
            if (r->rtv) r->rtv->Release();
            if (r->swap) r->swap->Release();
            if (r->ctx)  r->ctx->Release();
            if (r->device) r->device->Release();
            delete r;
            SetWindowLongPtrW(hWnd, GWLP_USERDATA, 0);
        }
    }
    return DefWindowProcW(hWnd, msg, wParam, lParam);
}

static DWORD WINAPI RenderThread(LPVOID param)
{
    Renderer* r = reinterpret_cast<Renderer*>(param);
    r->running = true;

    while (r->running) {
        FLOAT clear[4] = { 0.f, 0.f, 0.f, 0.f }; // 완전 투명/검정
        r->ctx->OMSetRenderTargets(1, &r->rtv, nullptr);
        r->ctx->ClearRenderTargetView(r->rtv, clear);
        r->swap->Present(1, 0);
        Sleep(16); // ~60 FPS
    }
    return 0;
}

extern "C" __declspec(dllexport)
HWND CreateProtectedWindow(HWND parent)
{
    // 1) 자식 윈도우 클래스 등록
    static bool s_registered = false;
    if (!s_registered) {
        WNDCLASSW wc = {};
        wc.style = CS_HREDRAW | CS_VREDRAW;
        wc.lpfnWndProc = HostWndProc;
        wc.hInstance = GetModuleHandleW(nullptr);
        wc.lpszClassName = L"ProtectedHostWnd";
        RegisterClassW(&wc);
        s_registered = true;
    }

    // 2) 자식 윈도우 생성
    HWND hwnd = CreateWindowExW(
        0, L"ProtectedHostWnd", L"",
        WS_CHILD | WS_VISIBLE,
        0, 0, 640, 360,
        parent, nullptr, GetModuleHandleW(nullptr), nullptr);

    if (!hwnd) return nullptr;

    // 자식 창을 화면 캡처에서 제외 (Windows 10 2004+)
    {
        // user32 선언은 포함되어 있으므로 직접 선언 없이 호출
        const UINT WDA_EXCLUDEFROMCAPTURE = 0x00000011;
        SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE);
    }

    // 3) D3D11 디바이스/컨텍스트 생성
    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* ctx = nullptr;
    D3D_FEATURE_LEVEL fl;
    HRESULT hr = D3D11CreateDevice(
        nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr,
        D3D11_CREATE_DEVICE_BGRA_SUPPORT,
        nullptr, 0, D3D11_SDK_VERSION,
        &device, &fl, &ctx);
    if (FAILED(hr)) {
        MessageBoxW(hwnd, L"D3D11CreateDevice 실패", L"Error", MB_OK);
        DestroyWindow(hwnd);
        return nullptr;
    }

    // 4) DXGI 팩토리
    IDXGIDevice* dxgiDevice = nullptr;
    device->QueryInterface(__uuidof(IDXGIDevice), (void**)&dxgiDevice);
    IDXGIAdapter* adapter = nullptr;
    dxgiDevice->GetAdapter(&adapter);
    IDXGIFactory2* factory = nullptr;
    adapter->GetParent(__uuidof(IDXGIFactory2), (void**)&factory);

    // 5) 보호 스왑체인 생성
    RECT rc; GetClientRect(hwnd, &rc);
    UINT w = rc.right - rc.left, h = rc.bottom - rc.top;

    DXGI_SWAP_CHAIN_DESC1 desc = {};
    desc.Width = w;
    desc.Height = h;
    desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    desc.SampleDesc.Count = 1;
    desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    desc.BufferCount = 2;
    desc.Scaling = DXGI_SCALING_STRETCH;
    desc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;
    desc.Flags = DXGI_SWAP_CHAIN_FLAG_HW_PROTECTED; // ★ 핵심

    IDXGISwapChain1* swap = nullptr;
    hr = factory->CreateSwapChainForHwnd(device, hwnd, &desc, nullptr, nullptr, &swap);
    if (FAILED(hr)) {
        MessageBoxW(hwnd, L"Protected SwapChain 생성 실패", L"Error", MB_OK);
        if (factory) factory->Release();
        if (adapter) adapter->Release();
        if (dxgiDevice) dxgiDevice->Release();
        device->Release(); ctx->Release();
        DestroyWindow(hwnd);
        return nullptr;
    }

    // 6) RTV 생성
    ID3D11Texture2D* backbuf = nullptr;
    swap->GetBuffer(0, __uuidof(ID3D11Texture2D), (void**)&backbuf);
    ID3D11RenderTargetView* rtv = nullptr;
    device->CreateRenderTargetView(backbuf, nullptr, &rtv);
    backbuf->Release();

    // 7) 렌더러 상태 저장 & 렌더 스레드 시작
    Renderer* r = new Renderer();
    r->device = device; r->ctx = ctx; r->swap = swap; r->rtv = rtv;
    SetWindowLongPtrW(hwnd, GWLP_USERDATA, (LONG_PTR)r);
    r->thread = CreateThread(nullptr, 0, RenderThread, r, 0, nullptr);

    // 8) 해제
    if (factory) factory->Release();
    if (adapter) adapter->Release();
    if (dxgiDevice) dxgiDevice->Release();

    return hwnd;
}
