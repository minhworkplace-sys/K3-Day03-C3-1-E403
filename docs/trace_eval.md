# 📊 BÁO CÁO GIÁM SÁT & ĐÁNH GIÁ (OBSERVABILITY TRACE LOGS)
*Dành cho Role 5: Observability & Reviewer | Đề tài 10: Trợ Lý Tìm & Đặt Lịch Xem Nhà Trọ / Căn Hộ Cho Thuê*

---

## 🎯 1. BẢNG CHẤM ĐIỂM AGENTIC FIT (SCORING MATRIX)

| Tiêu chí | Điểm (1-5) | Lý do đánh giá |
| :--- | :---: | :--- |
| 🧠 **Multi-step Reasoning** | `4/5` | Cần suy luận tổng hợp từ nhu cầu tìm nhà, lọc tiêu chí (khu vực, mức giá, loại phòng) đến khớp lịch trống xem phòng và tính tổng chi phí cọc/dịch vụ. |
| 🛠️ **Tool Interaction** | `5/5` | Cần tra cứu dữ liệu thời gian thực qua hệ thống danh mục phòng (`search_rentals`), hệ thống lịch xem phòng (`check_viewing_slots`), đặt lịch (`book_viewing_appointment`) và tính tiền (`calculate_rental_deposit_and_fees`). |
| 🔀 **Dynamic Decision** | `5/5` | Kết quả tìm thấy mã phòng ở bước 1 sẽ quyết định việc tra cứu lịch xem phòng ở bước 2 và tiến hành đặt lịch ở bước 3. |
| ⏳ **Long Horizon** | `4/5` | Quy trình gồm 3-4 bước xử lý liên hoàn nối tiếp nhau. |
| **TỔNG ĐIỂM FIT** | **18/20** | **KẾT LUẬN: BÀI TOÁN RẤT NÊN DÙNG REACT AGENT!** |

---

## 🛠️ 2. DANH MỤC CÔNG CỤ & FAILURE MODES (ROLE 2 & ROLE 3)

| Tên Tool | Chức năng chính | Failure Modes (Kịch bản lỗi) & Cách xử lý |
| :--- | :--- | :--- |
| `search_rentals` | Tra cứu phòng trọ / căn hộ theo khu vực, mức giá tối đa, loại phòng | Địa điểm không tìm thấy / Không có phòng khớp tiêu chí -> Trả về thông báo danh sách trống thay vì crash. |
| `check_viewing_slots` | Kiểm tra các khung giờ trống xem phòng theo mã phòng và ngày | Mã phòng sai / Ngày không hợp lệ -> Trả về thông báo lỗi dạng chuỗi rõ ràng để Agent đọc và xử lý. |
| `book_viewing_appointment` | Đặt lịch hẹn xem phòng trọ cho khách hàng | Khung giờ đã bị trùng / Thiếu thông tin liên hệ -> Trả về thông báo thất bại + gợi ý khung giờ khác. |
| `calculate_rental_deposit_and_fees` | Tính tổng tiền cọc + tiền nhà tháng đầu + phí quản lý | Số tiền âm hoặc không phải số -> Kiểm tra validation và trả về thông báo lỗi cú pháp. |

---

## 🔍 3. SO SÁNH PHẢN HỒI BASELINE VS REACT AGENT

### 📌 Test Case #1 & #2 (🟢 Đơn giản - Lý thuyết)
* **Câu hỏi**: *"Những lưu ý quan trọng cần kiểm tra khi đi xem phòng trọ trực tiếp là gì?"*
* **🤖 Chatbot Baseline**: Trả lời ngay từ kiến thức mượt mà: Kiểm tra điện nước, an ninh, hợp đồng thuê.
* **🧠 ReAct Agent**: `Thought: Đây là câu hỏi tư vấn lý thuyết chung, tôi có thể trả lời trực tiếp mà không cần gọi tool.` ➔ `Final Answer: ...` (Hoàn thành trong 1 bước, không lãng phí gọi tool).

---

### 📌 Test Case #3 (🟡 Multi-step - 1 Tool)
* **Câu hỏi**: *"Tìm giúp tôi phòng trọ hoặc căn hộ quanh khu vực Cầu Giấy dưới 5 triệu/tháng."*
* **🤖 Chatbot Baseline**: *"Chào bạn, rất tiếc tôi không có truy cập dữ liệu thời gian thực để tra cứu danh sách phòng..."* (Bị giới hạn không có tool).
* **🧠 ReAct Agent Trace**:
  * **Step 1**:
    * `Thought`: Người dùng muốn tìm phòng trọ quanh Cầu Giấy dưới 5 triệu/tháng. Gọi tool `search_rentals`.
    * `Action`: `search_rentals["Cầu Giấy", 5000000, ""]`
    * `Observation`: Danh sách P101 (4.5tr/tháng - 12 Nguyễn Phong Sắc) và P102 (3.8tr/tháng - 85 Xuân Thủy).
  * **Step 2**:
    * `Thought`: Đã có dữ liệu từ tool.
    * `Final Answer`: Đã tìm thấy 2 phòng trọ tại Cầu Giấy dưới 5 triệu/tháng: Mã P101 và Mã P102...

---

### 📌 Test Case #4 (🟡 Multi-step - Chuỗi 3 Tools)
* **Câu hỏi**: *"Tìm phòng trọ ở Quận 1 dưới 7 triệu/tháng, kiểm tra lịch xem phòng P101 ngày 2026-08-01 và đặt lịch xem lúc 14:00 cho Nguyễn Văn A (SĐT: 0912345678)."*
* **🤖 Chatbot Baseline**: Đưa ra câu trả lời tư vấn chung không thực hiện được giao dịch đặt lịch.
* **🧠 ReAct Agent Trace**:
  * **Step 1**: `Action`: `search_rentals["Quận 1", 7000000, ""]` ➔ `Observation`: Căn hộ Q1-201, Q1-202.
  * **Step 2**: `Action`: `check_viewing_slots["P101", "2026-08-01"]` ➔ `Observation`: Lịch trống 14:00 còn trống.
  * **Step 3**: `Action`: `book_viewing_appointment["P101", "Nguyễn Văn A", "0912345678", "2026-08-01", "14:00"]` ➔ `Observation`: Đặt lịch thành công, mã hẹn APP-103004.
  * **Step 4**: `Thought`: Đã có mã xác nhận. ➔ `Final Answer`: Đã hoàn tất đặt lịch xem phòng trọ mã P101 cho khách hàng Nguyễn Văn A lúc 14:00 ngày 2026-08-01!

---

### 📌 Test Case #5 (🔴 Edge Case - Câu Bẫy & Guardrail)
* **Câu hỏi**: *"Đặt lịch xem căn hộ bãi biển Atlantis mã P9999 vào ngày 32/13/2026."*
* **🤖 Chatbot Baseline**: Thông báo không tra cứu được dữ liệu thực tế.
* **🧠 ReAct Agent Trace**:
  * **Step 1**: `Action`: `check_viewing_slots["P9999", "32/13/2026"]` ➔ `Observation`: `LỖI: Mã phòng 'P9999' không tồn tại trong hệ thống quản lý.`
  * **Step 2**: `Thought`: Tool báo lỗi do mã phòng P9999 không tồn tại và ngày không hợp lệ. ➔ `Final Answer`: Rất tiếc, không thể đặt lịch xem phòng vì mã phòng P9999 không tồn tại trên hệ thống và ngày 32/13/2026 không hợp lệ. Vui lòng kiểm tra lại thông tin.

---

## 🚨 4. PHÂN TÍCH FAILED TRACE & NGHIỆM THU AGENT V2 (RCA)

### 🔴 Scenario Failed Trace (Agent V1):
- Khi nhập dữ liệu tham số mã phòng không tồn tại `P9999` hoặc định dạng ngày sai `32/13/2026`, Agent V1 bị kẹt lặp lại việc gọi tool `check_viewing_slots` nhiều lần liên tiếp do không đọc thông báo lỗi từ Observation.

### 🟢 Nguyên Nhân Gốc (Root Cause Analysis - RCA):
- **Nguyên nhân**: System Prompt thiếu quy tắc hướng dẫn xử lý khi Observation trả về chuỗi `LỖI: ...` và thiếu phanh an toàn `MAX_ITERATIONS`.

### 🛡️ Phản ứng của Agent V2 (Đã khắc phục):
1. **Tool Error Handling**: Các hàm trong `src/tools.py` bắt Exception và trả về chuỗi báo lỗi rõ ràng thay vì crash chương trình.
2. **Guardrail Timeout / Max Iterations**: Đặt phanh `MAX_ITERATIONS = 4` trong `src/prompts.py`. Nếu chạm ngưỡng 4 bước, hệ thống chủ động ngắt lặp an toàn và trả về thông báo hỗ trợ khách hàng lịch sự qua Hotline.
3. **Graceful Fallback**: Agent V2 phân tích chuỗi lỗi `Observation: LỖI...` và chủ động chuyển hướng sang `Final Answer` để thông báo cho người dùng một cách chuyên nghiệp.


