# Thư mục Mock

Thư mục này chứa các file mock (giả lập) cho các thành phần chính của hệ thống blockchain. Các file mock được sử dụng để:

- Kiểm thử (testing) các module khác mà không cần phụ thuộc vào các thành phần thực tế.
- Phát triển và debug mà không cần khởi tạo toàn bộ hệ thống.
- Giả lập hành vi của các thành phần để kiểm tra logic.

## Các file trong thư mục:

- `mock_block.py`: Mock cho lớp block layer, cung cấp các phương thức giả lập để xây dựng và xác thực block.
- `mock_core.py`: Mock cho core components.
- `mock_network.py`: Mock cho network components.

## Thay thế các file thực tế:

Các file mock này được thiết kế để thay thế các implementation thực tế trong các thư mục sau:

- `mock_block.py` thay thế cho các file trong `src/blocklayer/`
- `mock_core.py` thay thế cho các file trong `src/core/`
- `mock_network.py` thay thế cho các file trong `src/network/`

Các mock này trả về dữ liệu giả lập để hỗ trợ quá trình phát triển.