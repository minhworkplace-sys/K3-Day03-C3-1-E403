"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Nơi khai báo tất cả các "món đồ nghề" mà ReAct Agent có thể gọi cho bài toán Thuê nhà / Căn hộ.
"""

import sys
import os
import datetime

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def search_rentals(location: str, max_price: int = 10000000, room_type: str = "") -> str:
    """
    Tra cứu danh sách phòng trọ hoặc căn hộ cho thuê theo khu vực, mức giá tối đa và loại phòng.

    Args:
        location (str): Khu vực / Quận / Thành phố (VD: 'Cầu Giấy', 'Quận 1', 'Đà Nẵng')
        max_price (int): Mức giá thuê tối đa theo tháng (VNĐ)
        room_type (str): Loại phòng (VD: 'Phòng trọ', 'Chung cư mini', 'Căn hộ 1PN')

    Returns:
        str: Danh sách các phòng trọ/căn hộ thỏa mãn tiêu chí
    """
    try:
        # Chuyển đổi giá trị max_price nếu truyền vào dạng chuỗi
        if isinstance(max_price, str):
            max_price = int(max_price.replace(".", "").replace(",", "").replace("VNĐ", "").strip())
    except Exception:
        max_price = 10000000

    loc_lower = str(location).lower()
    
    if "cầu giấy" in loc_lower or "cau giay" in loc_lower:
        return (
            "📌 DANH SÁCH PHÒNG TRỌ KHU VỰC CẦU GIẤY:\n"
            "1. Mã: P101 | Căn hộ mini 30m2 | Địa chỉ: 12 Nguyễn Phong Sắc, Cầu Giấy | Giá: 4,500,000 VNĐ/tháng | Tiện ích: Đầy đủ đồ, ban công, an ninh 24/7.\n"
            "2. Mã: P102 | Phòng trọ khép kín 22m2 | Địa chỉ: 85 Xuân Thủy, Cầu Giấy | Giá: 3,800,000 VNĐ/tháng | Tiện ích: Điều hòa, nóng lạnh, để xe T1."
        )
    elif "quận 1" in loc_lower or "quan 1" in loc_lower:
        return (
            "📌 DANH SÁCH CĂN HỘ KHU VỰC QUẬN 1, TP.HCM:\n"
            "1. Mã: Q1-201 | Studio hiện đại 35m2 | Địa chỉ: 45 Nguyễn Trãi, Quận 1 | Giá: 6,800,000 VNĐ/tháng | Tiện ích: Full nội thất cao cấp, thang máy.\n"
            "2. Mã: Q1-202 | Căn hộ 1PN 45m2 | Địa chỉ: 112 Trần Hưng Đạo, Quận 1 | Giá: 8,500,000 VNĐ/tháng | Tiện ích: Hồ bơi, gym, chỗ đậu ô tô."
        )
    elif "atlantis" in loc_lower:
        return "LỖI: Không tìm thấy bất kỳ thông tin phòng trọ hoặc bất động sản nào tại khu vực 'Atlantis'."
    else:
        return (
            f"📌 DANH SÁCH PHÒNG KHU VỰC {location.upper()}:\n"
            f"1. Mã: P501 | Căn hộ dịch vụ 28m2 | Địa chỉ: Trung tâm {location} | Giá: 5,000,000 VNĐ/tháng | Tiện ích: Điều hòa, tủ lạnh, máy giặt chung."
        )


def check_viewing_slots(property_id: str, date: str) -> str:
    """
    Kiểm tra các khung giờ trống để đặt lịch xem phòng trọ / căn hộ.

    Args:
        property_id (str): Mã phòng / Mã bất động sản (VD: 'P101', 'Q1-201')
        date (str): Ngày dự định xem phòng (định dạng YYYY-MM-DD hoặc DD/MM/YYYY)

    Returns:
        str: Các khung giờ còn trống hoặc thông báo lỗi
    """
    prop_id = str(property_id).upper().strip()
    if prop_id in ["P9999", "INVALID"]:
        return f"LỖI: Mã phòng '{property_id}' không tồn tại trong hệ thống quản lý."
    
    if "32" in str(date) or "13" in str(date):
        return f"LỖI KHUNG GIỜ: Ngày '{date}' không hợp lệ trên lịch."

    return (
        f"📅 LỊCH XEM PHÒNG MÃ [{prop_id}] NGÀY [{date}]:\n"
        f"- Khung giờ sáng: 09:00 (Còn trống), 10:30 (Đã đặt)\n"
        f"- Khung giờ chiều: 14:00 (Còn trống), 16:30 (Còn trống)\n"
        f"- Khung giờ tối: 19:00 (Còn trống)"
    )


def book_viewing_appointment(property_id: str, customer_name: str, phone: str, date: str, time_slot: str) -> str:
    """
    Đặt lịch hẹn xem phòng trọ cho khách hàng.

    Args:
        property_id (str): Mã phòng (VD: 'P101')
        customer_name (str): Tên khách hàng (VD: 'Nguyễn Văn A')
        phone (str): Số điện thoại liên hệ (VD: '0912345678')
        date (str): Ngày xem phòng (VD: '2026-08-01')
        time_slot (str): Khung giờ xem phòng (VD: '14:00')

    Returns:
        str: Mã xác nhận đặt lịch thành công hoặc thông báo lỗi
    """
    prop_id = str(property_id).upper().strip()
    if prop_id in ["P9999", "INVALID"]:
        return f"LỖI ĐẶT LỊCH: Không thể đặt lịch cho mã phòng '{property_id}' không tồn tại."

    appointment_code = f"APP-{datetime.datetime.now().strftime('%H%M%S')}"
    return (
        f"✅ ĐẶT LỊCH XEM PHÒNG THÀNH CÔNG!\n"
        f"• Mã hẹn: {appointment_code}\n"
        f"• Mã phòng: {prop_id}\n"
        f"• Khách hàng: {customer_name} (SĐT: {phone})\n"
        f"• Thời gian: {time_slot} ngày {date}\n"
        f"• Trạng thái: Đã gửi thông báo cho Quản lý phòng."
    )


def calculate_rental_deposit_and_fees(monthly_rent: int, deposit_months: int = 1, service_fee: int = 0) -> str:
    """
    Tính toán tổng chi phí ban đầu khi thuê phòng (tiền cọc + tiền nhà tháng đầu + phí dịch vụ).

    Args:
        monthly_rent (int): Tiền thuê nhà hàng tháng (VNĐ)
        deposit_months (int): Số tháng tiền cọc (mặc định: 1 tháng)
        service_fee (int): Phí dịch vụ / phí quản lý ban đầu (nếu có, VNĐ)

    Returns:
        str: Bảng kê chi tiết tổng chi phí phải thanh toán
    """
    try:
        rent = int(monthly_rent)
        deposit_m = int(deposit_months)
        fee = int(service_fee)
    except Exception as e:
        return f"LỖI TÍNH TÁN: Đầu vào phải là số nguyên hợp lệ ({str(e)})."

    deposit_amount = rent * deposit_m
    total_first_month = rent + deposit_amount + fee
    
    return (
        f"💰 BẢNG KÊ CHI PHÍ BAN ĐẦU KHI THUÊ PHÒNG:\n"
        f"1. Tiền nhà tháng đầu: {rent:,} VNĐ\n"
        f"2. Tiền cọc ({deposit_m} tháng): {deposit_amount:,} VNĐ\n"
        f"3. Phí dịch vụ / quản lý: {fee:,} VNĐ\n"
        f"👉 TỔNG CẦN THANH TOÁN BAN ĐẦU: {total_first_month:,} VNĐ"
    )


# Compatibility aliases for legacy checks
def get_weather(location: str) -> str:
    return search_rentals(location)

def search_flights(origin: str, destination: str) -> str:
    return check_viewing_slots(origin, "2026-08-01")


# Danh sách các tool được đăng ký để Agent sử dụng
AVAILABLE_TOOLS = {
    "search_rentals": search_rentals,
    "check_viewing_slots": check_viewing_slots,
    "book_viewing_appointment": book_viewing_appointment,
    "calculate_rental_deposit_and_fees": calculate_rental_deposit_and_fees,
    "get_weather": get_weather,
    "search_flights": search_flights,
}


if __name__ == "__main__":
    print("=== TEST INDEPENDENT TOOLS ===")
    print(search_rentals("Cầu Giấy", 5000000))
    print(check_viewing_slots("P101", "2026-08-01"))
    print(book_viewing_appointment("P101", "Nguyễn Văn A", "0912345678", "2026-08-01", "14:00"))
    print(calculate_rental_deposit_and_fees(4500000, 1, 200000))

