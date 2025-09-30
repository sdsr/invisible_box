#pragma once
#include <windows.h>

#ifdef PROTECTEDSWAPCHAIN_EXPORTS
#define PROTECTED_API __declspec(dllexport)
#else
#define PROTECTED_API __declspec(dllimport)
#endif

extern "C" PROTECTED_API HWND CreateProtectedWindow(HWND parent);
