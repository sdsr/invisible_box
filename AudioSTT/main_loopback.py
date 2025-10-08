"""
실시간 PC 오디오 STT (WASAPI 루프백)
스테레오 믹스 활성화 없이 PC 스피커 출력을 자동 캡처합니다.
"""
import numpy as np
import time
from audio_capture_loopback import LoopbackAudioCapture
from stt_engine import WhisperSTT
from collections import deque
import argparse


def main():
    parser = argparse.ArgumentParser(description="실시간 PC 오디오 STT (WASAPI 루프백)")
    parser.add_argument("--model", default="base", 
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Whisper 모델 크기")
    parser.add_argument("--language", default="ko", 
                       help="인식 언어 코드 (ko, en 등)")
    parser.add_argument("--chunk-duration", type=float, default=5.0,
                       help="변환할 오디오 청크 길이 (초)")
    parser.add_argument("--stride", type=float, default=2.0,
                       help="청크 간 이동 간격 (초)")
    
    args = parser.parse_args()
    
    # STT 엔진 초기화
    print(f"\nWhisper STT 엔진 초기화 (모델: {args.model}, 언어: {args.language})")
    stt = WhisperSTT(model_size=args.model, language=args.language)
    
    # WASAPI 루프백 캡처 시작
    sample_rate = 16000
    capture = LoopbackAudioCapture(sample_rate=sample_rate)
    
    print("\n" + "=" * 60)
    print("PC 오디오 자동 캡처 (WASAPI 루프백)")
    print("스테레오 믹스 활성화 불필요!")
    print("=" * 60)
    
    try:
        capture.start()
    except Exception as e:
        print(f"\n오류: {e}")
        print("\n해결 방법:")
        print("1. Windows 오디오 드라이버가 최신인지 확인")
        print("2. pip install pyaudiowpatch 재설치")
        print("3. 관리자 권한으로 실행")
        return
    
    # 오디오 버퍼 (deque로 슬라이딩 윈도우 구현)
    chunk_samples = int(args.chunk_duration * sample_rate)
    stride_samples = int(args.stride * sample_rate)
    audio_buffer = deque(maxlen=chunk_samples)
    
    print(f"\n실시간 STT 시작 (청크: {args.chunk_duration}초, 스트라이드: {args.stride}초)")
    print("PC에서 소리를 재생하세요 (YouTube, 음악, 게임 등)")
    print("Ctrl+C로 종료\n")
    print("=" * 60)
    
    try:
        sample_count = 0
        last_process_count = 0
        
        while True:
            # 오디오 블록 읽기
            block = capture.read(timeout=0.5)
            if block is None:
                continue
            
            # 버퍼에 추가
            audio_buffer.extend(block)
            sample_count += len(block)
            
            # 충분한 샘플이 모이고 stride 간격이 지났으면 처리
            if (len(audio_buffer) >= chunk_samples and 
                sample_count - last_process_count >= stride_samples):
                
                # 버퍼에서 오디오 추출
                audio_chunk = np.array(audio_buffer, dtype=np.float32)
                
                # 에너지 체크 (너무 조용하면 건너뜀)
                energy = np.abs(audio_chunk).mean()
                if energy < 0.001:
                    print(f"[{time.strftime('%H:%M:%S')}] [조용함/침묵]")
                    last_process_count = sample_count
                    continue
                
                # STT 변환
                print(f"[{time.strftime('%H:%M:%S')}] 변환 중... ", end="", flush=True)
                start_time = time.time()
                
                text = stt.transcribe_realtime(audio_chunk, min_speech_duration=0.5)
                
                elapsed = time.time() - start_time
                
                if text:
                    print(f"({elapsed:.2f}초)")
                    print(f"  >> {text}")
                    print("-" * 60)
                else:
                    print(f"({elapsed:.2f}초) [음성 감지 안됨]")
                
                last_process_count = sample_count
    
    except KeyboardInterrupt:
        print("\n\n종료 중...")
    
    finally:
        capture.stop()
        print("STT 종료")


if __name__ == "__main__":
    main()

