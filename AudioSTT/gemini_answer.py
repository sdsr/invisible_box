"""
Gemini API를 사용한 OPIC 답변 생성 모듈
"""
import google.generativeai as genai
import os
from typing import Optional
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class GeminiAnswerGenerator:
    """Gemini 기반 OPIC 답변 생성기"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-pro"):
        """
        Args:
            api_key: Gemini API 키 (None이면 환경변수 GEMINI_API_KEY 사용)
            model_name: 사용할 모델 (gemini-pro, gemini-pro-vision 등)
        """
        # API 키 설정
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError(
                    "Gemini API 키가 필요합니다.\n"
                    "다음 중 하나를 선택하세요:\n"
                    "1. 환경변수 설정: set GEMINI_API_KEY=your_api_key\n"
                    "2. 인자로 전달: GeminiAnswerGenerator(api_key='your_key')"
                )
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        print(f"Gemini 모델 초기화 완료: {model_name}")
        
        # OPIC 답변 시스템 프롬프트
        self.system_prompt = """You are an OPIC (Oral Proficiency Interview by Computer) test assistant.
Your role is to generate natural, conversational answers to OPIC questions.

Guidelines:
- Answer in a natural, conversational style as if speaking
- Use appropriate level of English (intermediate to advanced)
- Include specific details and examples
- Keep answers between 30-60 seconds when spoken
- Use transitions and connectors naturally
- Show personality while staying appropriate
- Answer completely but don't over-elaborate

Remember: This is a speaking test, so the answer should sound natural when read aloud."""
    
    def generate_answer(self, question: str, language: str = "en") -> str:
        """
        OPIC 질문에 대한 답변 생성
        
        Args:
            question: OPIC 질문 텍스트
            language: 답변 언어 (en=영어, ko=한국어)
            
        Returns:
            생성된 답변 텍스트
        """
        # 언어별 프롬프트 조정
        if language.lower() == "ko":
            instruction = f"""다음은 OPIC 시험 질문입니다. 자연스럽고 구체적인 한국어 답변을 생성하세요.
질문을 반복하지 말고 바로 답변만 작성하세요.

질문: {question}

답변:"""
        else:
            instruction = f"""This is an OPIC test question. Generate a natural, conversational answer in English.
Don't repeat the question, just provide the answer directly.

Question: {question}

Answer:"""
        
        try:
            # Gemini API 호출
            response = self.model.generate_content(
                f"{self.system_prompt}\n\n{instruction}",
                generation_config={
                    "temperature": 0.7,  # 자연스러운 변화
                    "top_p": 0.9,
                    "top_k": 40,
                    "max_output_tokens": 300,  # 30~60초 분량
                }
            )
            
            answer = response.text.strip()
            return answer
            
        except Exception as e:
            print(f"Gemini API 오류: {e}")
            return ""
    
    def generate_answer_with_context(self, question: str, 
                                     previous_qa: list = None,
                                     language: str = "en") -> str:
        """
        이전 Q&A 문맥을 포함한 답변 생성
        
        Args:
            question: 현재 질문
            previous_qa: 이전 질문-답변 리스트 [(q1, a1), (q2, a2), ...]
            language: 답변 언어
            
        Returns:
            생성된 답변
        """
        # 문맥 구성
        context = ""
        if previous_qa:
            context = "Previous questions and answers in this test:\n"
            for i, (q, a) in enumerate(previous_qa[-3:], 1):  # 최근 3개만
                context += f"\nQ{i}: {q}\nA{i}: {a}\n"
            context += "\n---\n\n"
        
        if language.lower() == "ko":
            instruction = f"""{context}다음 질문에 이전 답변과 일관성 있게 답하세요.
질문을 반복하지 말고 바로 답변만 작성하세요.

질문: {question}

답변:"""
        else:
            instruction = f"""{context}Answer the following question consistently with your previous answers.
Don't repeat the question, just provide the answer directly.

Question: {question}

Answer:"""
        
        try:
            response = self.model.generate_content(
                f"{self.system_prompt}\n\n{instruction}",
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "max_output_tokens": 300,
                }
            )
            
            return response.text.strip()
            
        except Exception as e:
            print(f"Gemini API 오류: {e}")
            return ""


if __name__ == "__main__":
    # 간단한 테스트
    print("Gemini 답변 생성 테스트\n")
    
    # API 키 확인
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("환경변수 GEMINI_API_KEY를 설정하세요.")
        print("예: set GEMINI_API_KEY=your_api_key_here")
        exit(1)
    
    # 생성기 초기화
    generator = GeminiAnswerGenerator()
    
    # 테스트 질문
    test_question = "Can you tell me about yourself?"
    
    print(f"질문: {test_question}\n")
    print("답변 생성 중...\n")
    
    answer = generator.generate_answer(test_question, language="en")
    
    print("=" * 60)
    print(answer)
    print("=" * 60)

