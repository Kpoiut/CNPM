# Hướng dẫn thu thập 3-5% dữ liệu

## Tổng quan

Hệ thống yêu cầu tối thiểu 3-5% dữ liệu tự thu thập (self-collected data) để đảm bảo tính unique và đa dạng của dataset. Dữ liệu này phải là dữ liệu thật, không phải dữ liệu giả.

## Các phương thức thu thập hợp lệ

### 1. Khảo sát thực địa (Field Survey)
- Điều tra trực tiếp tại các khu vực
- Ghi nhận thông tin bất động sản qua quan sát
- Thu thập thông tin từ chủ sở hữu hoặc môi giới

### 2. Phiếu khảo sát (Survey Form)
- Thiết kế form khảo sát online/offline
- Thu thập phản hồi từ người dùng thử nghiệm
- Thu thập từ các nguồn xác minh được

### 3. Nhập liệu từ nguồn đáng tin cậy
- Từ các sàn bất động sản uy tín (có xác minh)
- Từ các báo cáo định giá chuyên nghiệp
- Từ cơ quan quản lý đất đai

### 4. Người dùng thử nghiệm (User Testing)
- Thu thập từ beta testers
- Thu thập feedback từ người dùng thực

## Các trường dữ liệu tự thu thập

Hệ thống theo dõi các trường sau cho dữ liệu tự thu thập:

| Trường | Mô tả |
|---------|-------|
| is_self_collected | Đánh dấu là dữ liệu tự thu thập |
| collection_method | Phương thức thu thập (survey_form, field_visit, user_input) |
| collected_by | Người thu thập |
| collected_at | Thời điểm thu thập |
| verification_note | Ghi chú xác minh |
| source_name | Tên nguồn |
| source_url | URL nguồn (nếu có) |
| noise_level | Mức tiếng ồn (dB) - từ smartphone |
| capture_time | Thời điểm chụp/ghi |
| phone_device | Thiết bị sử dụng |

## Cách thêm dữ liệu tự thu thập

### Qua API:
```bash
curl -X POST http://localhost:8000/api/properties \
  -H "Content-Type: application/json" \
  -d '{
    "property_type": "house",
    "province_city": "Hà Nội",
    "district": "Quận Cầu Giấy",
    "area_m2": 100,
    "price": 5000000000,
    "is_self_collected": true,
    "collection_method": "field_visit",
    "collected_by": "Nguyễn Văn A",
    "noise_level": 45.5,
    "phone_device": "iPhone 14"
  }'
```

### Qua Frontend:
Sử dụng trang "Dữ liệu tự thu thập" để thêm mới.

### Qua CSV:
```bash
python scripts/import_csv.py data.csv --self-collected --source "Survey 2024"
```

## Cảnh báo hệ thống

Hệ thống tự động kiểm tra tỷ lệ dữ liệu tự thu thập:

- **< 3%**: Cảnh báo đỏ - Cần thu thêm dữ liệu
- **3-5%**: Đạt yêu cầu - OK
- **> 5%**: Thông tin - Có thể thu thập thêm nếu muốn

## Lưu ý quan trọng

1. **Không được dùng dữ liệu giả** - Dữ liệu tự thu thập phải là thật
2. **Phải có xác minh** - Ghi rõ nguồn và phương thức thu thập
3. **IoT features** - Sử dụng smartphone để thu thập noise_level, capture_time
4. **Tách biệt** - Dữ liệu tự thu thập phải được đánh dấu rõ ràng
