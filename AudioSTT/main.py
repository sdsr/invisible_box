"""
실시간 오디오 STT 메인 스크립트
PC 오디오를 캡처하여 Whisper로 실시간 텍스트 변환합니다.
"""
import numpy as np
import time
from audio_capture import AudioCapture
from stt_engine import WhisperSTT
from collections import deque
import argparse


def main():
    parser = argparse.ArgumentParser(description="실시간 오디오 STT")
    parser.add_argument("--model", default="base", 
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Whisper 모델 크기")
    parser.add_argument("--language", default="ko", 
                       help="인식 언어 코드 (ko, en 등)")
    parser.add_argument("--device", type=int, default=None,
                       help="오디오 디바이스 인덱스 (미지정 시 기본값)")
    parser.add_argument("--list-devices", action="store_true",
                       help="오디오 디바이스 목록 출력 후 종료")
    parser.add_argument("--chunk-duration", type=float, default=5.0,
                       help="변환할 오디오 청크 길이 (초)")
    parser.add_argument("--stride", type=float, default=2.0,
                       help="청크 간 이동 간격 (초)")
    
    args = parser.parse_args()
    
    # 디바이스 목록 출력
    if args.list_devices:
        AudioCapture.list_devices()
        return
    
    # STT 엔진 초기화
    print(f"\nWhisper STT 엔진 초기화 (모델: {args.model}, 언어: {args.language})")
    stt = WhisperSTT(model_size=args.model, language=args.language)
    
    # 오디오 캡처 시작
    sample_rate = 16000
    capture = AudioCapture(sample_rate=sample_rate, device=args.device)
    
    print("\n오디오 캡처 디바이스:")
    AudioCapture.list_devices()
    
    capture.start()
    
    # 오디오 버퍼 (deque로 슬라이딩 윈도우 구현)
    chunk_samples = int(args.chunk_duration * sample_rate)
    stride_samples = int(args.stride * sample_rate)
    audio_buffer = deque(maxlen=chunk_samples)
    
    print(f"\n실시간 STT 시작 (청크: {args.chunk_duration}초, 스트라이드: {args.stride}초)")
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

