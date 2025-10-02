"""
Whisper STT 엔진 모듈
OpenAI Whisper 모델을 사용하여 오디오를 텍스트로 변환합니다.
"""
import whisper
import numpy as np
from typing import Optional, Dict
import torch


class WhisperSTT:
    """Whisper 기반 음성-텍스트 변환 엔진"""
    
    def __init__(self, model_size: str = "base", device: Optional[str] = None,
                 language: str = "ko"):
        """
        Args:
            model_size: 모델 크기 (tiny, base, small, medium, large)
            device: 실행 디바이스 (None이면 자동 선택, 'cpu' 또는 'cuda')
            language: 인식 언어 코드 (ko=한국어, en=영어 등)
        """
        self.model_size = model_size
        self.language = language
        
        # 디바이스 자동 선택
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        print(f"Whisper 모델 로딩 중: {model_size} on {self.device}...")
        self.model = whisper.load_model(model_size, device=self.device)
        print("모델 로딩 완료")
    
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000,
                   verbose: bool = False) -> Dict:
        """
        오디오를 텍스트로 변환
        
        Args:
            audio: 오디오 배열 (float32, [-1, 1] 범위)
            sample_rate: 샘플레이트 (Whisper는 16kHz 권장)
            verbose: 진행 상황 출력 여부
            
        Returns:
            변환 결과 딕셔너리 (text, segments, language 등)
        """
        # 오디오 정규화 및 리샘플링
        if sample_rate != 16000:
            # Whisper는 16kHz를 기대하므로 리샘플링 필요
            from scipy import signal
            num_samples = int(len(audio) * 16000 / sample_rate)
            audio = signal.resample(audio, num_samples)
        
        # 정규화: [-1, 1] 범위로
        audio = audio.astype(np.float32)
        if np.abs(audio).max() > 1.0:
            audio = audio / np.abs(audio).max()
        
        # Whisper 변환
        result = self.model.transcribe(
            audio,
            language=self.language,
            verbose=verbose,
            fp16=(self.device == "cuda")  # GPU에서는 FP16 사용
        )
        
        return result
    
    def transcribe_realtime(self, audio: np.ndarray, 
                           min_speech_duration: float = 1.0) -> Optional[str]:
        """
        실시간용 간단한 변환 (짧은 구간)
        
        Args:
            audio: 오디오 배열
            min_speech_duration: 최소 음성 길이 (초)
            
        Returns:
            변환된 텍스트 또는 None
        """
        # 최소 길이 체크
        duration = len(audio) / 16000
        if duration < min_speech_duration:
            return None
        
        # 에너지 기반 음성 감지 (간단한 VAD)
        energy = np.abs(audio).mean()
        if energy < 0.01:  # 임계값 (조정 필요)
            return None
        
        # 변환
        result = self.transcribe(audio, verbose=False)
        text = result.get("text", "").strip()
        
        return text if text else None


if __name__ == "__main__":
    # 간단한 테스트
    print("Whisper STT 엔진 테스트")
    
    # 더미 오디오 생성 (1초, 16kHz)
    duration = 1.0
    sample_rate = 16000
    t = np.linspace(0, duration, int(sample_rate * duration))
    # 440Hz 사인파 (A4 음)
    audio = 0.3 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    
    # STT 엔진 초기화
    stt = WhisperSTT(model_size="tiny", language="ko")
    
    # 변환 (더미 오디오라 의미있는 결과는 안 나옴)
    result = stt.transcribe(audio)
    print(f"변환 결과: {result['text']}")
    print(f"언어: {result['language']}")

