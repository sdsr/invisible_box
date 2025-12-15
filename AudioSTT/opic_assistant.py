"""
OPIC 자동 답변 시스템
STT로 질문 인식 → Gemini로 답변 생성 → 출력
"""
import numpy as np
import time
from audio_capture_loopback import LoopbackAudioCapture
from stt_engine import WhisperSTT
from gemini_answer import GeminiAnswerGenerator
import argparse
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="OPIC 자동 답변 시스템")
    parser.add_argument("--stt-model", default="base",
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Whisper STT 모델 크기")
    parser.add_argument("--language", default="en",
                       help="답변 언어 (en, ko)")
    parser.add_argument("--energy-threshold", type=float, default=0.01,
                       help="음성 감지 에너지 임계값")
    parser.add_argument("--silence-duration", type=float, default=2.0,
                       help="침묵으로 간주할 시간 (초)")
    parser.add_argument("--min-speech-duration", type=float, default=1.0,
                       help="최소 음성 길이 (초)")
    parser.add_argument("--gemini-api-key", default=None,
                       help="Gemini API 키 (미지정 시 환경변수 GEMINI_API_KEY 사용)")
    parser.add_argument("--save-log", default=None,
                       help="Q&A 로그를 파일로 저장 (선택)")
    
    args = parser.parse_args()
    
    # API 키 확인
    api_key = args.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n오류: Gemini API 키가 필요합니다.")
        print("\n설정 방법:")
        print("1. 환경변수: set GEMINI_API_KEY=your_api_key")
        print("2. 인자: --gemini-api-key your_api_key")
        print("\nAPI 키 발급: https://makersuite.google.com/app/apikey")
        return
    
    # STT 엔진 초기화
    print(f"\n[1/3] Whisper STT 엔진 초기화 (모델: {args.stt_model})")
    # STT는 자동 언어 감지 (한/영 혼용 대응)
    stt = WhisperSTT(model_size=args.stt_model, language=None)
    
    # Gemini 답변 생성기 초기화
    print(f"[2/3] Gemini 답변 생성기 초기화 (답변 언어: {args.language})")
    llm = GeminiAnswerGenerator(api_key=api_key)
    
    # 오디오 캡처 시작
    print(f"[3/3] WASAPI 루프백 캡처 시작")
    sample_rate = 16000
    capture = LoopbackAudioCapture(sample_rate=sample_rate)
    
    try:
        capture.start()
    except Exception as e:
        print(f"\n오류: {e}")
        return
    
    print("\n" + "=" * 60)
    print("OPIC 자동 답변 시스템 시작")
    print("=" * 60)
    print(f"VAD 설정: 에너지={args.energy_threshold}, 침묵={args.silence_duration}초")
    print("PC에서 OPIC 문제를 재생하세요")
    print("질문이 끝나면 자동으로 답변을 생성합니다")
    print("Ctrl+C로 종료\n")
    print("=" * 60)
    
    # VAD 상태 관리
    is_speaking = False
    speech_buffer = []
    silence_samples_threshold = int(args.silence_duration * sample_rate)
    silent_block_count = 0
    
    # Q&A 히스토리
    qa_history = []
    question_count = 0
    
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
                    is_speaking = True
                    speech_buffer = []
                    silent_block_count = 0
                    print(f"\n[{time.strftime('%H:%M:%S')}] 질문 음성 감지...", flush=True)
                
                speech_buffer.append(block)
                silent_block_count = 0
                
            else:
                # 조용함
                if is_speaking:
                    speech_buffer.append(block)
                    silent_block_count += 1
                    
                    # 침묵이 충분히 길면 발화 종료
                    if silent_block_count * len(block) >= silence_samples_threshold:
                        is_speaking = False
                        
                        # 전체 음성 데이터
                        full_audio = np.concatenate(speech_buffer)
                        duration = len(full_audio) / sample_rate
                        
                        # 최소 길이 체크
                        if duration >= args.min_speech_duration:
                            # STT 변환
                            print(f"[{time.strftime('%H:%M:%S')}] STT 변환 중... ", end="", flush=True)
                            start_time = time.time()
                            
                            result = stt.transcribe(full_audio, verbose=False)
                            stt_time = time.time() - start_time
                            
                            question = result.get("text", "").strip()
                            detected_lang = result.get("language", "?")
                            
                            if question and len(question) > 10:
                                print(f"({stt_time:.2f}초)")
                                question_count += 1
                                print(f"\n【질문 {question_count}】 (언어: {detected_lang.upper()})")
                                print(f"{question}")
                                print()
                                
                                # Gemini로 답변 생성
                                print("답변 생성 중... ", end="", flush=True)
                                gen_start = time.time()
                                
                                answer = llm.generate_answer_with_context(
                                    question, 
                                    previous_qa=qa_history,
                                    language=args.language
                                )
                                
                                gen_time = time.time() - gen_start
                                print(f"({gen_time:.2f}초)")
                                
                                if answer:
                                    print(f"\n【답변 {question_count}】")
                                    print(answer)
                                    print("\n" + "=" * 60)
                                    
                                    # 히스토리 저장
                                    qa_history.append((question, answer))
                                    
                                    # 로그 저장
                                    if args.save_log:
                                        with open(args.save_log, 'a', encoding='utf-8') as f:
                                            f.write(f"\n{'='*60}\n")
                                            f.write(f"질문 {question_count} [{time.strftime('%H:%M:%S')}]\n")
                                            f.write(f"{'='*60}\n")
                                            f.write(f"{question}\n\n")
                                            f.write(f"답변:\n{answer}\n")
                                else:
                                    print("답변 생성 실패")
                            else:
                                print(f"({stt_time:.2f}초) [텍스트 너무 짧음]")
                        
                        # 버퍼 초기화
                        speech_buffer = []
                        silent_block_count = 0
    
    except KeyboardInterrupt:
        print("\n\n종료 중...")
    
    finally:
        capture.stop()
        
        # 최종 통계
        print("\n" + "=" * 60)
        print(f"총 처리한 질문: {question_count}개")
        if args.save_log:
            print(f"로그 저장됨: {args.save_log}")
        print("=" * 60)


if __name__ == "__main__":
    main()

