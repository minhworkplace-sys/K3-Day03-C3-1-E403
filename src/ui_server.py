"""
🌐 UI SERVER - Flask Streaming Backend
Trợ Lý Tìm & Đặt Lịch Xem Nhà Trọ / Căn Hộ Cho Thuê

Chạy bằng lệnh: python src/ui_server.py
Truy cập:       http://localhost:5000
"""

import json
import os
import re
import sys
import time
import unicodedata

from flask import Flask, Response, render_template, request, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv

# ── Đảm bảo import module cùng thư mục src/ ─────────────────────────────────
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from tools import AVAILABLE_TOOLS
from prompts import REACT_SYSTEM_PROMPT, MAX_ITERATIONS
from providers import get_llm_provider

# ── Khởi tạo Flask ────────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR  = os.path.join(BASE_DIR, "templates")
app = Flask(__name__, template_folder=TEMPLATE_DIR)
CORS(app)


# ══════════════════════════════════════════════════════════════════════════════
# 🛡️  SCOPE GUARDRAIL — Chỉ xử lý chủ đề Tìm & Đặt Lịch Xem Nhà Trọ
# ══════════════════════════════════════════════════════════════════════════════

def normalize_vn(text: str) -> str:
    """Bỏ dấu tiếng Việt để so sánh không phân biệt dấu"""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower()


# Keywords với dấu (dùng cho raw text)
IN_SCOPE_KEYWORDS = [
    # Thuật ngữ thuê nhà
    "phòng", "nhà", "trọ", "căn hộ", "thuê", "cho thuê", "đặt lịch", "xem phòng",
    "giá thuê", "tiền thuê", "tiền cọc", "cọc", "hẹn xem", "lịch xem",
    "khu vực", "quận", "địa chỉ", "hợp đồng", "chủ nhà", "diện tích",
    "nội thất", "tiện ích", "phí dịch vụ", "phí quản lý",
    "tìm phòng", "tìm nhà", "tư vấn thuê", "mã phòng", "đặt hẹn",
    "chung cư", "mini", "studio", "căn hộ dịch vụ",
    # Khu vực
    "cầu giấy", "quận 1", "hà nội", "hcm", "hồ chí minh", "đà nẵng",
    # Mã phòng
    "p101", "p102", "q1-201", "q1-202", "p501",
    # Tiếng Anh
    "rental", "rent", "apartment", "booking", "deposit", "viewing", "schedule",
    # Chào hỏi
    "xin chào", "chào", "hello", "hi", "giúp tôi", "tôi muốn", "tôi cần",
]

# Keywords không dấu (dùng sau normalize)
IN_SCOPE_KEYWORDS_NORMALIZED = [
    "phong", "nha", "tro", "can ho", "thue", "cho thue", "dat lich", "xem phong",
    "gia thue", "tien thue", "tien coc", "coc", "hen xem", "lich xem",
    "khu vuc", "quan", "dia chi", "hop dong", "chu nha", "dien tich",
    "noi that", "tien ich", "phi dich vu", "phi quan ly",
    "tim phong", "tim nha", "tu van thue", "ma phong", "dat hen",
    "chung cu", "studio",
    "cau giay", "quan 1", "ha noi", "ho chi minh", "da nang",
    "p101", "p102", "p501",
    "rental", "rent", "apartment", "booking", "deposit", "viewing", "schedule",
    "xin chao", "chao", "hello", "hi", "giup toi", "toi muon", "toi can",
]

OUT_OF_SCOPE_MSG = (
    "⚠️ **Câu hỏi này nằm ngoài phạm vi hỗ trợ của tôi.**\n\n"
    "Tôi là **Trợ Lý Tìm & Đặt Lịch Xem Nhà Trọ / Căn Hộ Cho Thuê**, "
    "chuyên hỗ trợ các yêu cầu sau:\n\n"
    "🏠 **Tìm kiếm** phòng trọ / căn hộ theo khu vực & ngân sách\n"
    "📅 **Kiểm tra** khung giờ xem phòng còn trống\n"
    "✅ **Đặt lịch** hẹn xem phòng trực tiếp\n"
    "💰 **Tính toán** chi phí ban đầu (cọc + tháng đầu + phí dịch vụ)\n\n"
    "Hãy hỏi tôi về **nhà trọ hoặc căn hộ cho thuê** nhé! 🏡"
)

GREETING_KEYWORDS = ["xin chào", "chào", "hello", "hi", "hey", "giúp tôi với", "bạn là ai", "bạn có thể"]


def is_in_scope(message: str) -> bool:
    """Kiểm tra câu hỏi có trong phạm vi trợ lý không (hỗ trợ cả có dấu và không dấu)"""
    lower = message.lower()
    normalized = normalize_vn(message)
    # Cho phép câu chào hỏi ngắn
    if any(kw in lower for kw in GREETING_KEYWORDS) and len(message.split()) <= 8:
        return True
    # Kiểm tra với text gốc (có dấu)
    if any(keyword in lower for keyword in IN_SCOPE_KEYWORDS):
        return True
    # Kiểm tra với text đã bỏ dấu (hỗ trợ người dùng gõ không dấu)
    return any(keyword in normalized for keyword in IN_SCOPE_KEYWORDS_NORMALIZED)


# ══════════════════════════════════════════════════════════════════════════════
# 🔧  HELPER — Parse Action từ LLM response
# ══════════════════════════════════════════════════════════════════════════════

def parse_action(text: str):
    """Bóc tách Action: tool_name[arg1, arg2, ...] từ LLM output"""
    match = re.search(r"Action:\s*(\w+)\[(.*?)\]", text, re.DOTALL)
    if not match:
        match = re.search(r"Action:\s*(\w+)\((.*?)\)", text, re.DOTALL)
    if match:
        tool_name = match.group(1).strip()
        raw_args  = match.group(2).strip()
        args = []
        if raw_args:
            for arg in raw_args.split(","):
                args.append(arg.strip().strip('"').strip("'"))
        return tool_name, args
    return None, []


# ══════════════════════════════════════════════════════════════════════════════
# 🔄  REACT AGENT STREAMING GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

def sse(event_type: str, **kwargs) -> str:
    """Tạo 1 SSE data line"""
    payload = {"type": event_type, **kwargs}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def react_agent_stream(user_query: str, provider):
    """Generator: yield từng SSE event trong vòng lặp ReAct"""

    # ── 1. Scope guardrail ────────────────────────────────────────────────────
    if not is_in_scope(user_query):
        yield sse("out_of_scope", content=OUT_OF_SCOPE_MSG)
        yield sse("done")
        return

    # ── 2. Greeting shortcut ──────────────────────────────────────────────────
    lower = user_query.lower()
    if any(kw in lower for kw in GREETING_KEYWORDS) and len(user_query.split()) <= 8:
        greeting_reply = (
            "👋 **Xin chào! Tôi là Trợ Lý Tìm & Đặt Lịch Xem Nhà Trọ.**\n\n"
            "Tôi có thể giúp bạn:\n"
            "🏠 Tìm phòng trọ / căn hộ cho thuê theo khu vực và ngân sách\n"
            "📅 Kiểm tra lịch xem phòng còn trống\n"
            "✅ Đặt lịch hẹn xem phòng trực tiếp\n"
            "💰 Tính toán chi phí ban đầu khi thuê\n\n"
            "Hãy cho tôi biết bạn muốn tìm phòng ở **khu vực nào** và **ngân sách** của bạn là bao nhiêu? 😊"
        )
        yield sse("final_answer", content=greeting_reply)
        yield sse("done")
        return

    # ── 3. ReAct loop ─────────────────────────────────────────────────────────
    current_prompt = f"User Query: {user_query}\n"
    step = 0

    while step < MAX_ITERATIONS:
        step += 1
        yield sse("step_start", step=step, max=MAX_ITERATIONS)
        time.sleep(0.05)

        # Gọi LLM Provider
        response = provider.generate(current_prompt, system_prompt=REACT_SYSTEM_PROMPT)

        # Bóc tách Thought
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|Final Answer:|$)", response, re.DOTALL)
        if thought_match:
            thought_text = thought_match.group(1).strip()
            if thought_text:
                yield sse("thought", content=thought_text, step=step)
                time.sleep(0.08)

        # Kiểm tra Final Answer
        if "Final Answer:" in response:
            final_ans = response.split("Final Answer:")[-1].strip()
            yield sse("final_answer", content=final_ans)
            yield sse("done")
            return

        # Bóc tách và thực thi Action
        tool_name, args = parse_action(response)

        if tool_name:
            yield sse("action", tool=tool_name, args=args, step=step)
            time.sleep(0.1)

            if tool_name in AVAILABLE_TOOLS:
                tool_func = AVAILABLE_TOOLS[tool_name]
                try:
                    observation = tool_func(*args)
                except Exception as e:
                    observation = f"LỖI THỰC THI TOOL '{tool_name}': {str(e)}"
            else:
                observation = (
                    f"LỖI: Tool '{tool_name}' không tồn tại. "
                    f"Các tool hợp lệ: {list(AVAILABLE_TOOLS.keys())}"
                )

            yield sse("observation", content=observation, step=step)
            time.sleep(0.05)
            current_prompt += f"\n{response}\nObservation: {observation}\n"

        else:
            # LLM không sinh Action hợp lệ — nhắc lại định dạng
            current_prompt += (
                f"\n{response}\n"
                "Observation: LỖI CÚ PHÁP. Bạn phải sinh "
                "'Action: tên_công_cụ[tham_số]' hoặc 'Final Answer: ...'\n"
            )

    # ── 4. Guardrail vượt MAX_ITERATIONS ─────────────────────────────────────
    fallback = (
        f"🛡️ **Hệ thống đã đạt giới hạn tối đa {MAX_ITERATIONS} bước xử lý.**\n\n"
        "Không thể hoàn tất giao dịch tự động. Vui lòng liên hệ:\n"
        "📞 **Hotline hỗ trợ: 1900-1234** (Miễn phí, 8:00 – 22:00)"
    )
    yield sse("guardrail", content=fallback)
    yield sse("done")


# ══════════════════════════════════════════════════════════════════════════════
# 🌐  FLASK ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat/stream", methods=["POST"])
def chat_stream():
    """SSE endpoint — nhận message và stream lại từng bước ReAct"""
    data         = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        def empty_gen():
            yield sse("error", content="Tin nhắn không được để trống.")
            yield sse("done")
        return Response(stream_with_context(empty_gen()),
                        mimetype="text/event-stream")

    provider = get_llm_provider()

    return Response(
        stream_with_context(react_agent_stream(user_message, provider)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


@app.route("/health")
def health():
    provider = get_llm_provider()
    return {
        "status":   "ok",
        "provider": provider.__class__.__name__,
        "model":    getattr(provider, "model_name", "mock"),
    }


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("🏠  TRỢ LÝ TÌM & ĐẶT LỊCH XEM NHÀ TRỌ / CĂN HỘ")
    print("=" * 55)
    provider = get_llm_provider()
    print(f"🔌  Provider : {provider.__class__.__name__}")
    print(f"🤖  Model    : {getattr(provider, 'model_name', 'mock')}")
    print(f"🌐  URL      : http://localhost:5000")
    print("=" * 55 + "\n")
    app.run(debug=True, threaded=True, port=5000)
