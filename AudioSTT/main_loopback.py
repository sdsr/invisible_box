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
    parser.add_argument("--language", default=None, 
                       help="인식 언어 코드 (ko, en 등). None이면 자동 감지")
    parser.add_argument("--chunk-duration", type=float, default=5.0,
                       help="변환할 오디오 청크 길이 (초)")
    parser.add_argument("--stride", type=float, default=None,
                       help="청크 간 이동 간격 (초, 기본값은 chunk-duration과 동일)")
    
    args = parser.parse_args()
    
    # stride 기본값 설정 (chunk와 동일하게)
    if args.stride is None:
        args.stride = args.chunk_duration
    
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
        last_text = ""  # 중복 텍스트 필터링용
        
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
                    # stride == chunk인 경우 중복 없이 모두 출력
                    # stride < chunk인 경우에만 중복 제거 로직 적용
                    if args.stride >= args.chunk_duration:
                        # 겹침 없음 - 모두 출력
                        print(f"({elapsed:.2f}초)")
                        print(f"  >> {text}")
                        print("-" * 60)
                    else:
                        # 겹침 있음 - 유사도 기반 중복 제거
                        if last_text:
                            # 간단한 유사도 체크: 공통 단어 비율
                            last_words = set(last_text.lower().split())
                            current_words = set(text.lower().split())
                            
                            if len(current_words) > 0:
                                common = last_words & current_words
                                similarity = len(common) / len(current_words)
                                
                                # 70% 이상 겹치면 중복으로 간주 (건너뜀)
                                if similarity > 0.7:
                                    # 중복이므로 출력 안 함
                                    pass
                                else:
                                    # 새로운 내용
                                    print(f"({elapsed:.2f}초)")
                                    print(f"  >> {text}")
                                    print("-" * 60)
                            else:
                                print(f"({elapsed:.2f}초)")
                                print(f"  >> {text}")
                                print("-" * 60)
                        else:
                            # 첫 번째 출력
                            print(f"({elapsed:.2f}초)")
                            print(f"  >> {text}")
                            print("-" * 60)
                    
                    last_text = text
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

