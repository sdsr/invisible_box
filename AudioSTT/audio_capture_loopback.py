"""
WASAPI 루프백 오디오 캡처 모듈 (Windows 전용)
스테레오 믹스 활성화 없이 PC 스피커 출력을 자동으로 캡처합니다.
"""
import numpy as np
from queue import Queue
from typing import Optional
import sys


class LoopbackAudioCapture:
    """WASAPI 루프백 기반 실시간 오디오 캡처 (PC 스피커 출력)"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, 
                 chunk_size: int = 8000):
        """
        Args:
            sample_rate: 샘플링 레이트 (Whisper는 16kHz 권장)
            channels: 채널 수 (1=모노, 2=스테레오)
            chunk_size: 청크 크기 (샘플 수)
        """
        if sys.platform != 'win32':
            raise RuntimeError("WASAPI 루프백은 Windows 전용입니다.")
        
        try:
            import pyaudiowpatch as pyaudio
            self.pyaudio = pyaudio
        except ImportError:
            raise ImportError(
                "pyaudiowpatch가 설치되지 않았습니다.\n"
                "설치: pip install pyaudiowpatch"
            )
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_queue = Queue()
        self.stream = None
        self.running = False
        self.pa = None
        self.wasapi_info = None
        
    def _find_loopback_device(self):
        """WASAPI 루프백 디바이스 찾기"""
        self.pa = self.pyaudio.PyAudio()
        
        # 기본 스피커의 WASAPI 루프백 찾기
        try:
            # Get default WASAPI info
            wasapi_info = self.pa.get_default_wasapi_loopback()
            if wasapi_info:
                print(f"WASAPI 루프백 디바이스 발견: {wasapi_info['name']}")
                return wasapi_info
        except Exception as e:
            print(f"기본 WASAPI 루프백 찾기 실패: {e}")
        
        # 수동으로 루프백 디바이스 검색
        print("수동으로 루프백 디바이스 검색 중...")
        for i in range(self.pa.get_device_count()):
            dev = self.pa.get_device_info_by_index(i)
            if dev.get('isLoopbackDevice', False):
                print(f"루프백 디바이스 발견: {dev['name']}")
                return dev
        
        raise RuntimeError(
            "WASAPI 루프백 디바이스를 찾을 수 없습니다.\n"
            "Windows 오디오 드라이버를 확인하세요."
        )
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """오디오 스트림 콜백"""
        # bytes를 numpy 배열로 변환
        audio = np.frombuffer(in_data, dtype=np.int16).astype(np.float32)
        
        # 정규화 [-1, 1]
        audio = audio / 32768.0
        
        # 스테레오 → 모노 변환
        if self.wasapi_info['maxInputChannels'] >= 2 and self.channels == 1:
            audio = audio.reshape(-1, 2)
            audio = np.mean(audio, axis=1)
        
        self.audio_queue.put(audio)
        return (None, self.pyaudio.paContinue)
    
    def start(self):
        """캡처 시작"""
        if self.running:
            return
        
        print("WASAPI 루프백 초기화 중...")
        self.wasapi_info = self._find_loopback_device()
        
        # 실제 디바이스 샘플레이트 확인
        device_rate = int(self.wasapi_info['defaultSampleRate'])
        print(f"디바이스 샘플레이트: {device_rate}Hz")
        
        # 스트림 열기
        self.stream = self.pa.open(
            format=self.pyaudio.paInt16,
            channels=self.wasapi_info['maxInputChannels'],
            rate=device_rate,
            input=True,
            input_device_index=self.wasapi_info['index'],
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback
        )
        
        self.running = True
        self.stream.start_stream()
        print(f"PC 오디오 캡처 시작 (스테레오 믹스 불필요)")
        print(f"  - 디바이스: {self.wasapi_info['name']}")
        print(f"  - 샘플레이트: {device_rate}Hz → {self.sample_rate}Hz 변환")
        print(f"  - 채널: {self.wasapi_info['maxInputChannels']}ch → {self.channels}ch")
    
    def stop(self):
        """캡처 종료"""
        if not self.running:
            return
        
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.pa:
            self.pa.terminate()
            self.pa = None
        print("오디오 캡처 종료")
    
    def read(self, timeout: Optional[float] = None) -> Optional[np.ndarray]:
        """
        큐에서 오디오 블록 읽기
        
        Args:
            timeout: 대기 시간 (초)
            
        Returns:
            오디오 데이터 배열 또는 None
        """
        try:
            audio = self.audio_queue.get(timeout=timeout)
            
            # 리샘플링 (디바이스 레이트 → 16kHz)
            if self.wasapi_info:
                device_rate = int(self.wasapi_info['defaultSampleRate'])
                if device_rate != self.sample_rate:
                    from scipy import signal
                    num_samples = int(len(audio) * self.sample_rate / device_rate)
                    audio = signal.resample(audio, num_samples)
            
            return audio.astype(np.float32)
        except:
            return None


if __name__ == "__main__":
    # 간단한 테스트
    print("WASAPI 루프백 테스트 (5초간 PC 오디오 캡처)")
    print("PC에서 음악이나 비디오를 재생하세요...")
    
    capture = LoopbackAudioCapture()
    
    try:
        capture.start()
        
        import time
        time.sleep(5)
        
        # 큐에서 데이터 읽기
        blocks = []
        while not capture.audio_queue.empty():
            block = capture.read()
            if block is not None:
                blocks.append(block)
        
        if blocks:
            total = np.concatenate(blocks)
            print(f"\n캡처 성공: {len(total)} 샘플, {len(total)/16000:.2f}초")
            print(f"최대 진폭: {np.abs(total).max():.4f}")
        else:
            print("\n캡처된 오디오 없음 (PC에서 소리가 나고 있나요?)")
    
    except Exception as e:
        print(f"\n오류: {e}")
    
    finally:
        capture.stop()

