"""
🚀 CẤP ĐỘ 4: AUTONOMOUS AGENT (Agent tự chủ với Planning & Memory - BONUS)
Tự chia nhỏ mục tiêu phức tạp thành nhiều bước, duy trì bộ nhớ (Memory) và tự đánh giá tiến độ.
"""

class AutonomousGoalAgent:
    def __init__(self, goal: str, max_steps: int = 4):
        self.goal = goal
        self.max_steps = max_steps
        self.memory = []  # Bộ nhớ lưu vết các bước đã thực hiện
        
    def execute(self):
        print(f"🚀 === Bắt đầu Autonomous Goal: {self.goal} ===")
        
        for step in range(1, self.max_steps + 1):
            print(f"\n--- Vòng lặp tự chủ Planning & Action (Step {step}/{self.max_steps}) ---")
            
            if step == 1:
                plan = "Bước 1: Tìm danh sách căn hộ cho thuê quanh khu vực mong muốn"
                action = "Call Tool: search_rentals('Cầu Giấy', 5000000)"
                result = "Đã tìm thấy phòng P101 (4.5tr/tháng) và P102 (3.8tr/tháng)."
            elif step == 2:
                plan = "Bước 2: Kiểm tra lịch xem phòng trống cho phòng P101"
                action = "Call Tool: check_viewing_slots('P101', '2026-08-01')"
                result = "Khung giờ 14:00 ngày 2026-08-01 còn trống."
            elif step == 3:
                plan = "Bước 3: Tiến hành đặt lịch hẹn xem phòng cho khách hàng"
                action = "Call Tool: book_viewing_appointment('P101', 'Nguyễn Văn A', '0912345678', '2026-08-01', '14:00')"
                result = "Đặt lịch thành công, Mã hẹn: APP-103004."
            else:
                print("🎯 [Goal Evaluation]: Mục tiêu tìm nhà & đặt lịch xem phòng đã hoàn thành 100%!")
                break
                
            self.memory.append({"step": step, "plan": plan, "result": result})
            print(f"📋 [Planning]: {plan}")
            print(f"🛠️ [Execution]: {action} ➔ {result}")
            print(f"💾 [Memory Saved]: Logged step {step} to memory.")

if __name__ == "__main__":
    agent = AutonomousGoalAgent("Tìm phòng trọ Cầu Giấy dưới 5tr và đặt lịch xem phòng P101 ngày 2026-08-01")
    agent.execute()

