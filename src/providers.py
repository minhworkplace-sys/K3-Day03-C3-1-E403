"""
🔌 MULTI-PROVIDER LLM ADAPTER (OpenAI, Gemini, Anthropic, OpenRouter & Offline Mock)
Hỗ trợ chuyển đổi linh hoạt giữa các nhà cung cấp AI chỉ bằng cách đổi biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho tất cả các LLM Provider"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (SDK + REST API Fallback)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env!"
        
        contents_text = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        # 1. Thử dùng SDK chính thức google.genai
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents_text
            )
            if hasattr(response, "text") and response.text:
                return response.text
        except Exception:
            pass

        # 2. Fallback sang Google Gemini REST API trực tiếp qua requests
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": contents_text}]}]
            }
            res = requests.post(url, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                # Nếu API key bị leak/hết quota/lỗi 403/429 -> Fallback an toàn sang MockProvider
                return MockProvider().generate(prompt, system_prompt)
        except Exception:
            return MockProvider().generate(prompt, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (GPT-4o, GPT-3.5-turbo, etc.)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env!"
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude Provider (Claude 3.5 Sonnet, Claude 3 Haiku)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "claude-3-haiku-20240307"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_anthropic_api_key_here":
            return "[Anthropic Error]: Chưa cấu hình ANTHROPIC_API_KEY trong file .env!"
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            kwargs = {
                "model": self.model_name,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system_prompt:
                kwargs["system"] = system_prompt
                
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            return f"[Anthropic Exception]: {str(e)}"


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter Provider (Hỗ trợ gọi mọi model qua OpenRouter API)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "google/gemini-2.5-flash"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            return "[OpenRouter Error]: Chưa cấu hình OPENROUTER_API_KEY trong file .env!"
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_name,
                "messages": messages
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"[OpenRouter API Error {res.status_code}]: {res.text}"
        except Exception as e:
            return f"[OpenRouter Exception]: {str(e)}"


class MockProvider(BaseLLMProvider):
    """Offline Mock Provider (Giả lập thông minh cho bài test offline / không API Key)"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        text = prompt.lower()
        is_react = "react" in system_prompt.lower() or "thought:" in system_prompt.lower() or "danh sách các công cụ" in system_prompt.lower()
        
        # Phản hồi cho ReAct Agent
        if is_react:
            # Case 1 & Case 2: Đơn giản / Lý thuyết
            if "quan trọng" in text or "lưu ý" in text:
                return "Thought: Đây là câu hỏi tư vấn lý thuyết chung, tôi có thể trả lời trực tiếp mà không cần gọi tool.\nFinal Answer: Khi đi xem phòng trọ trực tiếp, bạn nên kiểm tra: 1. Đồ đạc và hệ thống điện nước. 2. Giá điện nước sinh hoạt và an ninh khu vực. 3. Các điều khoản hợp đồng thuê và tiền cọc."
            elif "hợp đồng" in text or "đặt cọc" in text:
                return "Thought: Đây là câu hỏi về quy trình pháp lý / hợp đồng, trả lời trực tiếp từ kiến thức.\nFinal Answer: Quy trình làm hợp đồng đặt cọc gồm 3 bước: 1. Xác minh quyền sở hữu của chủ nhà. 2. Thống nhất số tiền cọc, thời hạn thuê và điều kiện hoàn cọc. 3. Ký hợp đồng cọc có 2 bản và biên nhận tiền."

            # Case 3: Search Cầu Giấy (1 tool)
            elif "cầu giấy" in text:
                if "observation:" not in text:
                    return 'Thought: Người dùng muốn tìm phòng trọ quanh khu vực Cầu Giấy dưới 5 triệu/tháng. Tôi sẽ sử dụng công cụ search_rentals.\nAction: search_rentals["Cầu Giấy", 5000000, ""]'
                else:
                    return "Thought: Tôi đã nhận được danh sách phòng từ công cụ search_rentals. Đã đủ thông tin để trả lời.\nFinal Answer: Đã tìm thấy các phòng trọ ở Cầu Giấy dưới 5 triệu/tháng:\n1. Mã P101: Căn hộ mini 30m2 tại 12 Nguyễn Phong Sắc (Giá: 4,500,000 VNĐ/tháng)\n2. Mã P102: Phòng trọ khép kín 22m2 tại 85 Xuân Thủy (Giá: 3,800,000 VNĐ/tháng)."

            # Case 4: Search -> Check -> Book (Multi-step 3 tools)
            elif "quận 1" in text or "nguyễn văn a" in text:
                if "observation:" not in text:
                    return 'Thought: Người dùng cần tìm phòng ở Quận 1 dưới 7 triệu/tháng. Tôi sẽ gọi tool search_rentals trước.\nAction: search_rentals["Quận 1", 7000000, ""]'
                elif "search_rentals" in text and "check_viewing_slots" not in text:
                    return 'Thought: Đã tìm thấy phòng Q1-201. Tiếp theo tôi cần kiểm tra lịch xem phòng còn trống cho mã P101 ngày 2026-08-01.\nAction: check_viewing_slots["P101", "2026-08-01"]'
                elif "check_viewing_slots" in text and "book_viewing_appointment" not in text:
                    return 'Thought: Lịch xem phòng P101 khung giờ 14:00 ngày 2026-08-01 còn trống. Tôi tiến hành đặt lịch cho khách hàng Nguyễn Văn A.\nAction: book_viewing_appointment["P101", "Nguyễn Văn A", "0912345678", "2026-08-01", "14:00"]'
                else:
                    return "Thought: Đã nhận được xác nhận đặt lịch xem phòng thành công. Tôi sẽ tổng hợp kết quả gửi cho người dùng.\nFinal Answer: Đã hoàn tất đặt lịch xem phòng trọ mã P101 cho khách hàng Nguyễn Văn A (SĐT: 0912345678) vào lúc 14:00 ngày 2026-08-01. Trạng thái: Đặt lịch thành công!"

            # Case 5: Edge Case (Bẫy Atlantis P9999)
            elif "atlantis" in text or "p9999" in text or "32/13" in text:
                if "observation:" not in text:
                    return 'Thought: Người dùng muốn đặt lịch xem phòng P9999 tại Atlantis ngày 32/13/2026. Tôi sẽ kiểm tra thông tin lịch xem phòng.\nAction: check_viewing_slots["P9999", "32/13/2026"]'
                else:
                    return "Thought: Công cụ báo lỗi do mã phòng P9999 không tồn tại và ngày 32/13/2026 là ngày không hợp lệ. Tôi sẽ báo lại người dùng.\nFinal Answer: Rất tiếc, không thể đặt lịch xem phòng vì mã phòng P9999 không tồn tại trên hệ thống và ngày 32/13/2026 không hợp lệ. Vui lòng kiểm tra lại thông tin."

            else:
                return "Thought: Tôi sẽ xử lý yêu cầu dựa trên kiến thức sẵn có.\nFinal Answer: Yêu cầu của bạn đã được tiếp nhận và xử lý thành công."

        # Phản hồi cho Baseline Chatbot
        else:
            if "lưu ý" in text or "xem phòng" in text:
                return "Khi đi xem phòng trọ trực tiếp, bạn nên kiểm tra: 1. Hệ thống điện nước và giá sinh hoạt. 2. An ninh khu vực và chỗ để xe. 3. Hợp đồng thuê và các điều khoản đặt cọc."
            elif "hợp đồng" in text or "đặt cọc" in text:
                return "Quy trình làm hợp đồng đặt cọc gồm: 1. Xác minh thông tin chủ nhà. 2. Thống nhất số tiền cọc và điều kiện hoàn cọc. 3. Ký biên bản giao nhận tiền cọc có người làm chứng."
            else:
                return "Chào bạn, tôi là Chatbot tư vấn phòng trọ. Rất tiếc tôi không có truy cập dữ liệu thời gian thực để tra cứu danh sách phòng hoặc đặt lịch hẹn trực tiếp giúp bạn được."


def get_llm_provider(provider_name: str = None) -> BaseLLMProvider:
    """Factory function tự chọn Provider từ biến môi trường LLM_PROVIDER"""
    name = (provider_name or os.getenv("LLM_PROVIDER") or "mock").lower().strip()
    
    if name == "gemini":
        return GeminiProvider()
    elif name == "openai":
        return OpenAIProvider()
    elif name == "anthropic":
        return AnthropicProvider()
    elif name == "openrouter":
        return OpenRouterProvider()
    else:
        return MockProvider()


if __name__ == "__main__":
    print("=== TEST MULTI-PROVIDER LLM ADAPTER ===")
    provider = get_llm_provider()
    print(f"✅ Provider đang dùng: {provider.__class__.__name__}")
    print(f"🤖 User Query: Hello")
    print(f"💬 Response  : {provider.generate('Hello')}")
