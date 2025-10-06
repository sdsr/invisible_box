"""
오디오/비디오 파일 STT 테스트 스크립트
mp3, mp4, avi, wav 등 다양한 포맷 지원
"""
import argparse
import numpy as np
from stt_engine import WhisperSTT
import time
import os


def load_audio_file(file_path: str, target_sr: int = 16000) -> np.ndarray:
    """
    오디오/비디오 파일에서 오디오 추출
    
    Args:
        file_path: 파일 경로
        target_sr: 타겟 샘플레이트
        
    Returns:
        오디오 배열 (float32, mono)
    """
    try:
        # librosa 사용 (오디오 전용)
        import librosa
        audio, sr = librosa.load(file_path, sr=target_sr, mono=True)
        return audio.astype(np.float32)
    except ImportError:
        pass
    
    try:
        # pydub 사용 (오디오/비디오 모두 가능, ffmpeg 필요)
        from pydub import AudioSegment
        
        # 파일 로드
        if file_path.endswith('.mp3'):
            audio_seg = AudioSegment.from_mp3(file_path)
        elif file_path.endswith('.mp4') or file_path.endswith('.avi'):
            audio_seg = AudioSegment.from_file(file_path)
        elif file_path.endswith('.wav'):
            audio_seg = AudioSegment.from_wav(file_path)
        else:
            audio_seg = AudioSegment.from_file(file_path)
        
        # 모노, 타겟 샘플레이트로 변환
        audio_seg = audio_seg.set_channels(1).set_frame_rate(target_sr)
        
        # numpy 배열로 변환
        samples = np.array(audio_seg.get_array_of_samples(), dtype=np.float32)
        
        # 정규화 [-1, 1]
        max_val = float(2 ** (audio_seg.sample_width * 8 - 1))
        samples = samples / max_val
        
        return samples
    except ImportError:
        pass
    
    try:
        # moviepy 사용 (비디오 파일 지원)
        from moviepy.editor import VideoFileClip, AudioFileClip
        
        if file_path.endswith(('.mp4', '.avi', '.mov', '.mkv')):
            clip = VideoFileClip(file_path)
            audio_clip = clip.audio
        else:
            audio_clip = AudioFileClip(file_path)
        
        # 오디오 추출
        audio_array = audio_clip.to_soundarray(fps=target_sr)
        
        # 모노로 변환
        if len(audio_array.shape) > 1:
            audio_array = np.mean(audio_array, axis=1)
        
        # 정규화
        audio_array = audio_array.astype(np.float32)
        if np.abs(audio_array).max() > 1.0:
            audio_array = audio_array / np.abs(audio_array).max()
        
        clip.close()
        return audio_array
    except ImportError:
        pass
    
    raise ImportError(
        "오디오 로딩 라이브러리가 설치되지 않았습니다.\n"
        "다음 중 하나를 설치하세요:\n"
        "  pip install librosa\n"
        "  pip install pydub (+ ffmpeg 시스템 설치 필요)\n"
        "  pip install moviepy"
    )


def format_timestamp(seconds: float) -> str:
    """초를 HH:MM:SS.mmm 형식으로 변환"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def main():
    parser = argparse.ArgumentParser(description="파일 기반 STT 테스트")
    parser.add_argument("file", help="오디오/비디오 파일 경로 (mp3, mp4, avi, wav 등)")
    parser.add_argument("--model", default="base",
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Whisper 모델 크기")
    parser.add_argument("--language", default="ko",
                       help="인식 언어 코드 (ko, en 등)")
    parser.add_argument("--verbose", action="store_true",
                       help="상세 출력 (세그먼트별 타임스탬프)")
    parser.add_argument("--output", help="결과를 텍스트 파일로 저장 (선택)")
    
    args = parser.parse_args()
    
    # 파일 존재 확인
    if not os.path.exists(args.file):
        print(f"오류: 파일을 찾을 수 없습니다: {args.file}")
        return
    
    print(f"\n=== 파일 STT 테스트 ===")
    print(f"파일: {args.file}")
    print(f"모델: {args.model}")
    print(f"언어: {args.language}")
    print()
    
    # 오디오 로딩
    print("오디오 로딩 중...")
    try:
        audio = load_audio_file(args.file, target_sr=16000)
        duration = len(audio) / 16000
        print(f"로딩 완료: {duration:.2f}초")
    except Exception as e:
        print(f"오류: {e}")
        return
    
    # STT 엔진 초기화
    print(f"\nWhisper 모델 로딩 중 ({args.model})...")
    stt = WhisperSTT(model_size=args.model, language=args.language)
    
    # 변환 시작
    print("\nSTT 변환 중...")
    start_time = time.time()
    
    result = stt.transcribe(audio, verbose=args.verbose)
    
    elapsed = time.time() - start_time
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("=== 변환 결과 ===")
    print("=" * 60)
    print()
    
    # 전체 텍스트
    full_text = result.get("text", "").strip()
    print("【전체 텍스트】")
    print(full_text)
    print()
    
    # 세그먼트별 출력 (타임스탬프 포함)
    if "segments" in result and len(result["segments"]) > 0:
        print("【타임스탬프별 세그먼트】")
        print("-" * 60)
        for seg in result["segments"]:
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            text = seg["text"].strip()
            print(f"[{start} --> {end}]")
            print(f"  {text}")
            print()
    
    # 통계
    print("=" * 60)
    print("【변환 통계】")
    print(f"오디오 길이: {duration:.2f}초")
    print(f"변환 소요 시간: {elapsed:.2f}초")
    print(f"처리 속도: {duration/elapsed:.2f}x 실시간")
    print(f"인식 언어: {result.get('language', 'N/A')}")
    
    word_count = len(full_text.split())
    print(f"단어 수: {word_count}")
    if duration > 0:
        print(f"분당 단어 수: {word_count / (duration / 60):.1f}")
    print("=" * 60)
    
    # 파일로 저장
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(f"파일: {args.file}\n")
            f.write(f"모델: {args.model}\n")
            f.write(f"언어: {result.get('language', 'N/A')}\n")
            f.write(f"길이: {duration:.2f}초\n")
            f.write(f"변환 시간: {elapsed:.2f}초\n")
            f.write("\n" + "=" * 60 + "\n")
            f.write("전체 텍스트:\n")
            f.write(full_text + "\n")
            f.write("\n" + "=" * 60 + "\n")
            f.write("타임스탬프별 세그먼트:\n\n")
            
            if "segments" in result:
                for seg in result["segments"]:
                    start = format_timestamp(seg["start"])
                    end = format_timestamp(seg["end"])
                    text = seg["text"].strip()
                    f.write(f"[{start} --> {end}]\n")
                    f.write(f"{text}\n\n")
        
        print(f"\n결과가 저장되었습니다: {args.output}")


if __name__ == "__main__":
    main()


