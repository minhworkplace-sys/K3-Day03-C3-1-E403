"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer / Integrator)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import os
import re
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import (
    AVAILABLE_TOOLS,
    search_rentals,
    check_viewing_slots,
    book_viewing_appointment,
    calculate_rental_deposit_and_fees
)
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS
from providers import get_llm_provider

load_dotenv()


def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_action(text: str):
    """
    Bóc tách Action từ phản hồi của LLM.
    Ví dụ: 'Action: search_rentals["Cầu Giấy", 5000000]' -> ('search_rentals', ['Cầu Giấy', '5000000'])
    """
    match = re.search(r"Action:\s*(\w+)\[(.*?)\]", text, re.DOTALL)
    if not match:
        match = re.search(r"Action:\s*(\w+)\((.*?)\)", text, re.DOTALL)
    
    if match:
        tool_name = match.group(1).strip()
        raw_args = match.group(2).strip()
        
        # Bóc tách tham số phân cách bằng dấu phẩy
        args = []
        if raw_args:
            # Parse các tham số được bọc trong dấu ngoặc kép hoặc không
            for arg in raw_args.split(","):
                clean_arg = arg.strip().strip('"').strip("'")
                args.append(clean_arg)
        return tool_name, args
    return None, []


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")
    return response


def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) có Guardrails và tự xử lý lỗi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    current_prompt = f"User Query: {user_query}\n"
    step = 0
    full_trace = []

    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")
        
        # 1. Gọi LLM Provider để sinh Thought và Action
        response = provider.generate(current_prompt, system_prompt=REACT_SYSTEM_PROMPT)
        print(f"🧠 LLM Output:\n{response}")
        full_trace.append(response)

        # 2. Kiểm tra nếu Agent đã đưa ra Final Answer
        if "Final Answer:" in response:
            final_ans = response.split("Final Answer:")[-1].strip()
            print(f"\n🏁 FINAL ANSWER RECOVERY:\n{final_ans}")
            return response

        # 3. Bóc tách Action và tham số
        tool_name, args = parse_action(response)
        
        if tool_name:
            print(f"🛠️ Detected Action: {tool_name} với tham số {args}")
            
            # Executing tool trong registry
            if tool_name in AVAILABLE_TOOLS:
                tool_func = AVAILABLE_TOOLS[tool_name]
                try:
                    observation = tool_func(*args)
                except Exception as e:
                    observation = f"LỖI THỰC THI TOOL '{tool_name}': {str(e)}"
            else:
                observation = f"LỖI: Tool '{tool_name}' không tồn tại trong danh mục công cụ sẵn có: {list(AVAILABLE_TOOLS.keys())}"
            
            print(f"👁️ Observation:\n{observation}")
            
            # Cập nhật prompt nối tiếp Observation cho vòng lặp kế tiếp
            current_prompt += f"\n{response}\nObservation: {observation}\n"
        else:
            print("⚠️ Không bóc tách được Action hợp lệ. Gửi lại yêu cầu tuân thủ định dạng...")
            current_prompt += f"\n{response}\nObservation: LỖI CÚ PHÁP. Bạn phải sinh 'Action: tên_công_cụ[tham_số]' hoặc 'Final Answer: ...'\n"

    # Khi vượt quá giới hạn MAX_ITERATIONS (Guardrail Triggered)
    if step >= MAX_ITERATIONS:
        fallback_msg = (
            f"🛡️ [GUARDRAIL TRIGGERED]: Hệ thống đã đạt giới hạn tối đa {MAX_ITERATIONS} bước xử lý. "
            f"Do không thể hoàn tất giao dịch tự động, xin vui lòng liên hệ trực tiếp Bộ phận Hỗ trợ Khách hàng qua Hotline: 1900-1234."
        )
        print(f"\n{fallback_msg}")
        return fallback_msg


if __name__ == "__main__":
    print("==================================================")
    print("🏫 TRỢ LÝ TÌM & ĐẶT LỊCH XEM NHÀ TRỌ / CĂN HỘ CHO THUÊ")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")
    
    print("==================================================")
    print("🚀 BẮT ĐẦU CHẠY THỬ NGHỆM CÁC TEST CASES")
    print("==================================================")
    
    for test in tests:
        print(f"\n==================================================")
        print(f"📌 TEST CASE #{test['id']} [{test['category']}]")
        print(f"❓ Câu hỏi: {test['question']}")
        print(f"🎯 Kỳ vọng: {test['expected_behavior']}")
        print("==================================================")
        
        print("\n--- 1. CHÁY CHATBOT BASELINE ---")
        run_baseline_chatbot(test["question"], provider)
        
        print("\n--- 2. CHẠY REACT AGENT ---")
        run_react_agent(test["question"], provider)

