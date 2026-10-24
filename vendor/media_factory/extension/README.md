# Cofi Flow Job Controller

Mở `chrome://extensions`, bật **Developer mode**, chọn **Load unpacked** và trỏ tới thư mục này.

Extension dùng API local `http://127.0.0.1:8894`, hiển thị bảng điều phối trong popup và một nút `COFI Jobs` ngay trên `flow.google.com`. Mỗi account vẫn dùng Chrome profile riêng do CofiDocumentary quản lý; nút **Mở nền** khôi phục worker headless, còn **Xác minh** chỉ mở cửa sổ khi Google yêu cầu đăng nhập lại.
