"""
PC 오디오 캡처 모듈
Windows 루프백(스피커 출력) 또는 마이크 입력을 실시간 캡처합니다.
"""
import sounddevice as sd
import numpy as np
from queue import Queue
from typing import Optional
import threading


class AudioCapture:
    """실시간 오디오 캡처"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, 
                 blocksize: int = 8000, device: Optional[int] = None):
        """
        Args:
            sample_rate: 샘플링 레이트 (Whisper는 16kHz 권장)
            channels: 채널 수 (1=모노, 2=스테레오)
            blocksize: 블록 크기 (샘플 수)
            device: 오디오 디바이스 인덱스 (None이면 기본값)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.blocksize = blocksize
        self.device = device
        self.audio_queue = Queue()
        self.stream = None
        self.running = False
        
    def _audio_callback(self, indata, frames, time, status):
        """오디오 스트림 콜백"""
        if status:
            print(f"오디오 상태: {status}")
        # 모노로 변환하고 큐에 추가
        audio = indata.copy()
        if audio.shape[1] > 1:
            audio = np.mean(audio, axis=1, keepdims=True)
        self.audio_queue.put(audio.flatten())
    
    def start(self):
        """캡처 시작"""
        if self.running:
            return
        
        self.running = True
        self.stream = sd.InputStream(
            device=self.device,
            channels=self.channels,
            samplerate=self.sample_rate,
            blocksize=self.blocksize,
            callback=self._audio_callback
        )
        self.stream.start()
        print(f"오디오 캡처 시작: {self.sample_rate}Hz, {self.channels}ch, 디바이스={self.device}")
    
    def stop(self):
        """캡처 종료"""
        if not self.running:
            return
        
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
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
            return self.audio_queue.get(timeout=timeout)
        except:
            return None
    
    @staticmethod
    def list_devices():
        """사용 가능한 오디오 디바이스 목록 출력"""
        print("\n=== 사용 가능한 오디오 디바이스 ===")
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            print(f"{idx}: {device['name']}")
            print(f"   입력 채널: {device['max_input_channels']}, "
                  f"출력 채널: {device['max_output_channels']}, "
                  f"샘플레이트: {device['default_samplerate']}Hz")
        print()


if __name__ == "__main__":
    # 디바이스 목록 출력
    AudioCapture.list_devices()
    
    # 간단한 테스트
    print("5초간 오디오 캡처 테스트...")
    capture = AudioCapture()
    capture.start()
    
    import time
    time.sleep(5)
    
    # 큐에서 데이터 읽기
    blocks = []
    while not capture.audio_queue.empty():
        block = capture.read()
        if block is not None:
            blocks.append(block)
    
    capture.stop()
    
    if blocks:
        total = np.concatenate(blocks)
        print(f"캡처된 오디오: {len(total)} 샘플, {len(total)/16000:.2f}초")
    else:
        print("캡처된 오디오 없음")

