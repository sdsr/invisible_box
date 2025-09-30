#include <windows.h>
#include <d3d11.h>
#include <dxgi1_5.h>
#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")

extern "C" __declspec(dllexport)
HWND CreateProtectedWindow(HWND parent)
{
    // �ڽ� ������ ���� (W ���� API ���)
    HWND hwnd = CreateWindowExW(
        0, L"STATIC", L"ProtectedArea",
        WS_CHILD | WS_VISIBLE,
        0, 0, 640, 360,
        parent, nullptr, GetModuleHandleW(NULL), nullptr);

    // Direct3D 11 ����̽� ����
    ID3D11Device* device = nullptr;
    ID3D11DeviceContext* context = nullptr;
    D3D_FEATURE_LEVEL fl;
    D3D11CreateDevice(
        nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr,
        D3D11_CREATE_DEVICE_BGRA_SUPPORT,
        nullptr, 0, D3D11_SDK_VERSION,
        &device, &fl, &context);

    IDXGIDevice* dxgiDevice;
    device->QueryInterface(__uuidof(IDXGIDevice), (void**)&dxgiDevice);

    IDXGIAdapter* adapter;
    dxgiDevice->GetAdapter(&adapter);

    IDXGIFactory2* factory;
    adapter->GetParent(__uuidof(IDXGIFactory2), (void**)&factory);

    // Protected SwapChain ����
    DXGI_SWAP_CHAIN_DESC1 desc = {};
    desc.Width = 640;
    desc.Height = 360;
    desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    desc.SampleDesc.Count = 1;
    desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    desc.BufferCount = 2;
    desc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;
    desc.Flags = DXGI_SWAP_CHAIN_FLAG_HW_PROTECTED; // �ٽ�

    IDXGISwapChain1* swapChain;
    HRESULT hr = factory->CreateSwapChainForHwnd(
        device, hwnd, &desc, nullptr, nullptr, &swapChain);

    if (FAILED(hr)) {
        MessageBoxW(hwnd, L"Protected SwapChain ���� ����", L"Error", MB_OK);
    }

    return hwnd;
}
