"""
실시간 PC 오디오 STT (VAD 기반 자동 버퍼링)
음성 구간을 자동 감지하여 발화가 끝나면 전체를 한 번에 변환합니다.
"""
import numpy as np
import time
from audio_capture_loopback import LoopbackAudioCapture
from stt_engine import WhisperSTT
import argparse


def main():
    parser = argparse.ArgumentParser(description="실시간 PC 오디오 STT (VAD 자동 감지)")
    parser.add_argument("--model", default="base", 
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Whisper 모델 크기")
    parser.add_argument("--language", default=None, 
                       help="인식 언어 코드 (ko, en 등). None이면 자동 감지")
    parser.add_argument("--energy-threshold", type=float, default=0.01,
                       help="음성 감지 에너지 임계값 (기본: 0.01)")
    parser.add_argument("--silence-duration", type=float, default=2.0,
                       help="침묵으로 간주할 시간 (초, 기본: 2.0)")
    parser.add_argument("--min-speech-duration", type=float, default=1.0,
                       help="최소 음성 길이 (초, 기본: 1.0)")
    
    args = parser.parse_args()
    
    # STT 엔진 초기화
    print(f"\nWhisper STT 엔진 초기화 (모델: {args.model}, 언어: {args.language or '자동'})")
    stt = WhisperSTT(model_size=args.model, language=args.language)
    
    # WASAPI 루프백 캡처 시작
    sample_rate = 16000
    capture = LoopbackAudioCapture(sample_rate=sample_rate)
    
    print("\n" + "=" * 60)
    print("PC 오디오 자동 캡처 (VAD 기반)")
    print("음성 시작 감지 → 침묵 감지 → 전체 변환")
    print("=" * 60)
    
    try:
        capture.start()
    except Exception as e:
        print(f"\n오류: {e}")
        return
    
    print(f"\nVAD 설정:")
    print(f"  - 에너지 임계값: {args.energy_threshold}")
    print(f"  - 침묵 판단 시간: {args.silence_duration}초")
    print(f"  - 최소 음성 길이: {args.min_speech_duration}초")
    print(f"\nPC에서 소리를 재생하세요")
    print("Ctrl+C로 종료\n")
    print("=" * 60)
    
    # VAD 상태 관리
    is_speaking = False
    speech_buffer = []
    silence_start = None
    silence_samples_threshold = int(args.silence_duration * sample_rate)
    silent_block_count = 0
    
    try:
        while True:
            # 오디오 블록 읽기
            block = capture.read(timeout=0.5)
            if block is None:
                continue
            
            # 에너지 계산
            energy = np.abs(block).mean()
            
            if energy > args.energy_threshold:
                # 음성 감지
                if not is_speaking:
                    # 음성 시작
                    is_speaking = True
                    speech_buffer = []
                    silence_start = None
                    silent_block_count = 0
                    print(f"[{time.strftime('%H:%M:%S')}] 음성 감지 시작...", flush=True)
                
                # 버퍼에 추가
                speech_buffer.append(block)
                silent_block_count = 0
                
            else:
                # 조용함
                if is_speaking:
                    # 말하는 중인데 조용해짐 → 침묵 카운트
                    speech_buffer.append(block)  # 일단 버퍼에 추가 (끝 부분 놓치지 않게)
                    silent_block_count += 1
                    
                    # 침묵이 충분히 길면 발화 종료로 판단
                    if silent_block_count * len(block) >= silence_samples_threshold:
                        # 발화 종료
                        is_speaking = False
                        
                        # 전체 음성 데이터
                        full_audio = np.concatenate(speech_buffer)
                        duration = len(full_audio) / sample_rate
                        
                        # 최소 길이 체크
                        if duration >= args.min_speech_duration:
                            print(f"[{time.strftime('%H:%M:%S')}] 침묵 감지, 변환 중 ({duration:.1f}초)... ", end="", flush=True)
                            
                            start_time = time.time()
                            result = stt.transcribe(full_audio, verbose=False)
                            elapsed = time.time() - start_time
                            
                            text = result.get("text", "").strip()
                            lang = result.get("language", "?")
                            
                            if text:
                                print(f"({elapsed:.2f}초)")
                                print(f"[{lang.upper()}] {text}")
                                print("-" * 60)
                            else:
                                print(f"({elapsed:.2f}초) [텍스트 없음]")
                        else:
                            print(f"[{time.strftime('%H:%M:%S')}] 너무 짧음 ({duration:.1f}초), 무시")
                        
                        # 버퍼 초기화
                        speech_buffer = []
                        silent_block_count = 0
    
    except KeyboardInterrupt:
        print("\n\n종료 중...")
    
    finally:
        capture.stop()
        print("STT 종료")


if __name__ == "__main__":
    main()

