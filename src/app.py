"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer / Integrator)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
Đã tối ưu hóa cho Mốc 1 (Environment & Safeguards) và Mốc 2 (Baseline vs ReAct Evaluation).
"""

import json
import os
import re
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console / Terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
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
    """Đọc bộ test cases từ config/test_cases.json của Role 1 với cơ chế fallback an toàn"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ CẢNH BÁO: Không thể nạp file test_cases.json ({str(e)}). Sử dụng bộ test case mặc định.")
        return [
            {
                "id": 1,
                "category": "🟢 Đơn giản (Chỉ cần LLM)",
                "question": "Những lưu ý quan trọng cần kiểm tra khi đi xem phòng trọ trực tiếp là gì?",
                "expected_behavior": "Chatbot hoặc Agent trả lời trực tiếp từ kiến thức có sẵn."
            },
            {
                "id": 3,
                "category": "🟡 Multi-step (Cần Tool)",
                "question": "Tìm giúp tôi phòng trọ hoặc căn hộ quanh khu vực Cầu Giấy dưới 5 triệu/tháng.",
                "expected_behavior": "Agent suy luận và gọi tool search_rentals['Cầu Giấy', 5000000]."
            }
        ]


def parse_action(text: str):
    """
    Bóc tách Action từ phản hồi của LLM một cách linh hoạt.
    Ví dụ: 
      - 'Action: search_rentals["Cầu Giấy", 5000000]' -> ('search_rentals', ['Cầu Giấy', 5000000])
      - 'Action: check_viewing_slots("P101", "2026-08-01")' -> ('check_viewing_slots', ['P101', '2026-08-01'])
    """
    match = re.search(r"Action:\s*(\w+)\[(.*?)\]", text, re.DOTALL)
    if not match:
        match = re.search(r"Action:\s*(\w+)\((.*?)\)", text, re.DOTALL)
    
    if match:
        tool_name = match.group(1).strip()
        raw_args = match.group(2).strip()
        
        args = []
        if raw_args:
            for arg in raw_args.split(","):
                clean_arg = arg.strip().strip('"').strip("'")
                # Tự động ép kiểu số nguyên / số thực nếu hợp lệ
                if clean_arg.isdigit():
                    clean_arg = int(clean_arg)
                else:
                    try:
                        clean_arg = float(clean_arg)
                    except ValueError:
                        pass
                args.append(clean_arg)
        return tool_name, args
    return None, []


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    try:
        response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
        print(f"🤖 Chatbot trả lời:\n{response}")
        return response
    except Exception as e:
        err_msg = f"❌ Lỗi khi gọi Baseline Chatbot: {str(e)}"
        print(err_msg)
        return err_msg


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
        try:
            response = provider.generate(current_prompt, system_prompt=REACT_SYSTEM_PROMPT)
        except Exception as e:
            print(f"❌ Lỗi Provider ở Step {step}: {str(e)}")
            return f"LỖI PROVIDER: {str(e)}"

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


def print_comparison_summary(test_case, baseline_res, agent_res):
    """In ra bảng đối chứng so sánh hiệu quả giữa Baseline Chatbot và ReAct Agent (Phục vụ Role 5)"""
    print("\n" + "="*60)
    print(f"📊 BẢNG ĐỐI CHỨNG EVALUATION [TEST CASE #{test_case['id']}]")
    print("="*60)
    print(f"❓ Câu hỏi: {test_case['question']}")
    print(f"🎯 Kỳ vọng: {test_case['expected_behavior']}")
    print("-" * 60)
    
    # Kiểm tra xem baseline có bị từ chối/ảo giác không
    is_baseline_limited = "không có truy cập" in str(baseline_res).lower() or "rất tiếc" in str(baseline_res).lower()
    baseline_status = "⚠️ HẠN CHẾ (Từ chối tra cứu thực tế)" if is_baseline_limited else "✅ Hoàn thành (Lý thuyết)"
    
    print(f"💬 [CHATBOT BASELINE]: {baseline_status}")
    
    # Kiểm tra ReAct Agent
    is_agent_success = "Final Answer:" in str(agent_res) or "✅" in str(agent_res)
    agent_status = "✅ THÀNH CÔNG (Tự suy luận & Gọi công cụ)" if is_agent_success else "🛡️ Guardrail Ngắt An Toàn"
    print(f"🤖 [REACT AGENT]     : {agent_status}")
    print("="*60 + "\n")


def run_batch_eval(provider):
    """Chạy toàn bộ bộ Test Cases phục vụ nghiệm thu Mốc 1 & Mốc 2"""
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")
    
    print("==================================================")
    print("🚀 BẮT ĐẦU CHẠY THỬ NGHỆM CÁC TEST CASES (MỐC 1 & 2)")
    print("==================================================")
    
    for test in tests:
        print(f"\n==================================================")
        print(f"📌 TEST CASE #{test['id']} [{test['category']}]")
        print(f"❓ Câu hỏi: {test['question']}")
        print(f"🎯 Kỳ vọng: {test['expected_behavior']}")
        print("==================================================")
        
        print("\n--- 1. CHẠY CHATBOT BASELINE ---")
        b_res = run_baseline_chatbot(test["question"], provider)
        
        print("\n--- 2. CHẠY REACT AGENT ---")
        a_res = run_react_agent(test["question"], provider)
        
        print_comparison_summary(test, b_res, a_res)


def run_interactive_mode(provider):
    """Chế độ hỏi đáp trực tiếp linh hoạt từ bàn phím (Demo Mốc 4 & Test đòn bẫy)"""
    print("\n==================================================")
    print("💬 CHẾ ĐỘ DEMO TƯƠNG TÁC TRỰC TIẾP (INTERACTIVE DEMO)")
    print("Gõ 'exit' hoặc 'quit' để thoát chế độ demo.")
    print("==================================================")
    
    while True:
        try:
            user_input = input("\n👤 Bạn hỏi: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "thoát"]:
                print("👋 Đã thoát chế độ demo tương tác.")
                break
            
            print("\n🤖 [AGENT DANG XỬ LÝ...]")
            run_react_agent(user_input, provider)
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Đã thoát.")
            break


if __name__ == "__main__":
    print("==================================================")
    print("🏫 TRỢ LÝ TÌM & ĐẶT LỊCH XEM NHÀ TRỌ / CĂN HỘ CHO THUÊ")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter với kiểm tra an toàn
    try:
        provider = get_llm_provider()
        model_name = getattr(provider, "model_name", "Offline Mock Mode")
        print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo Provider: {str(e)}")
        sys.exit(1)
        
    # Kiểm tra tham số dòng lệnh hoặc mặc định chạy batch eval
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        run_interactive_mode(provider)
    else:
        run_batch_eval(provider)
