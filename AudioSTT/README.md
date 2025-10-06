# 실시간 오디오 STT (Speech-to-Text)

PC에서 나오는 소리를 실시간으로 캡처하여 OpenAI Whisper 모델로 텍스트로 변환하는 Python 프로젝트입니다.

## 주요 기능

- PC 스피커 출력(루프백) 또는 마이크 입력 실시간 캡처
- OpenAI Whisper 기반 고품질 음성 인식
- 다국어 지원 (한국어, 영어 등)
- 슬라이딩 윈도우 방식 실시간 처리
- GPU 가속 지원 (CUDA)

## 설치 방법

### 1. Python 환경 준비
Python 3.8 이상 권장

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

**주의:** Windows에서 `sounddevice`는 PortAudio가 필요합니다. 일반적으로 자동 설치되지만, 문제 발생 시 수동 설치:
```bash
pip install sounddevice --force-reinstall
```

### 3. PyTorch 설치 (GPU 사용 시)

CUDA 지원 버전:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

CPU만 사용:
```bash
pip install torch torchvision torchaudio
```

## 사용 방법

### 오디오 디바이스 확인

```bash
python main.py --list-devices
```

출력 예시:
```
=== 사용 가능한 오디오 디바이스 ===
0: Microsoft Sound Mapper - Input
   입력 채널: 2, 출력 채널: 0, 샘플레이트: 44100.0Hz
1: 마이크 (Realtek High Definition Audio)
   입력 채널: 2, 출력 채널: 0, 샘플레이트: 44100.0Hz
2: 스테레오 믹스 (Realtek High Definition Audio)
   입력 채널: 2, 출력 채널: 0, 샘플레이트: 44100.0Hz
...
```

**PC 소리 캡처:** "스테레오 믹스" 디바이스를 찾아 인덱스 확인

### 기본 실행 (기본 디바이스, 한국어)

```bash
python main.py
```

### 고급 옵션

```bash
# 특정 오디오 디바이스 사용 (예: 인덱스 2번)
python main.py --device 2

# 더 정확한 모델 사용 (느림)
python main.py --model small

# 영어 인식
python main.py --language en

# 청크/스트라이드 조정 (실시간성 vs 정확도 트레이드오프)
python main.py --chunk-duration 3.0 --stride 1.5
```

### 모든 옵션

```
--model {tiny,base,small,medium,large}
    Whisper 모델 크기 (기본: base)
    - tiny: 가장 빠름, 정확도 낮음
    - base: 균형잡힌 선택 (권장)
    - small/medium: 더 정확, 느림
    - large: 최고 정확도, 매우 느림

--language LANG
    인식 언어 코드 (기본: ko)
    - ko: 한국어
    - en: 영어
    - ja: 일본어 등

--device INDEX
    오디오 디바이스 인덱스 (미지정 시 기본값)

--chunk-duration SECONDS
    변환할 오디오 청크 길이 (기본: 5.0초)

--stride SECONDS
    청크 간 이동 간격 (기본: 2.0초)
```

## Windows 스테레오 믹스 활성화

PC 스피커 출력을 캡처하려면 "스테레오 믹스" 또는 "루프백" 디바이스가 필요합니다.

1. 시작 → 설정 → 시스템 → 소리
2. "소리 제어판" 클릭
3. "녹음" 탭
4. 빈 공간 우클릭 → "사용 안 함인 장치 표시"
5. "스테레오 믹스" 우클릭 → "사용"
6. 기본값으로 설정 (선택)

## 프로젝트 구조

```
AudioSTT/
├── main.py              # 메인 실행 스크립트
├── audio_capture.py     # 오디오 캡처 모듈
├── stt_engine.py        # Whisper STT 엔진
├── requirements.txt     # 의존성 목록
└── README.md           # 이 문서
```

## 파일 기반 테스트 (권장)

오디오/비디오 파일로 먼저 테스트해 보세요!

### 1. 테스트용 라이브러리 설치
```bash
# 가장 간단 (오디오 전용)
pip install librosa

# 또는 비디오 지원 (ffmpeg 필요)
pip install pydub moviepy
```

### 2. 파일 테스트 실행
```bash
# 기본 실행
python test_file.py your_audio.mp3

# 다양한 옵션
python test_file.py video.mp4 --model small --language ko --verbose

# 결과를 파일로 저장
python test_file.py audio.wav --output result.txt
```

### 지원 포맷
- 오디오: mp3, wav, flac, ogg, m4a 등
- 비디오: mp4, avi, mov, mkv 등 (자동으로 오디오 추출)

### 사용 예시
```bash
# YouTube 다운로드 파일 테스트
python test_file.py "downloaded_video.mp4" --model base --language ko

# 영어 팟캐스트
python test_file.py podcast.mp3 --model small --language en

# 고품질 변환
python test_file.py interview.wav --model medium --output transcript.txt
```

## 모듈 개별 테스트

### 오디오 캡처 테스트
```bash
python audio_capture.py
```

### STT 엔진 테스트
```bash
python stt_engine.py
```

## 성능 팁

- GPU 사용: CUDA 설치 시 자동으로 GPU 가속 활성화 (10배 이상 빠름)
- 모델 선택: 실시간 처리는 `tiny` 또는 `base` 권장
- 청크/스트라이드 조정:
  - 청크가 길수록 정확도 상승, 지연 증가
  - 스트라이드가 짧을수록 업데이트 빠름, CPU 부하 증가

## 문제 해결

### "No module named 'sounddevice'"
```bash
pip install sounddevice
```

### "CUDA out of memory"
- 더 작은 모델 사용 (`--model tiny`)
- CPU 모드 강제 (stt_engine.py 수정)

### 오디오 디바이스 없음/에러
- 드라이버 업데이트
- 관리자 권한으로 실행
- 스테레오 믹스 활성화 확인

### 한국어 인식 정확도 낮음
- 더 큰 모델 사용 (`--model small` 이상)
- 청크 길이 늘리기 (`--chunk-duration 10.0`)
- 마이크/스피커 음량 적절히 조정

## 라이선스

MIT License

## 참고

- [OpenAI Whisper](https://github.com/openai/whisper)
- [sounddevice](https://python-sounddevice.readthedocs.io/)

