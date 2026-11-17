# Lab 4 — Phân tích kết quả

| Kịch bản | Users | Spawn rate | Duration | p95 (ms) | Failure rate | RPS |
|---|---:|---:|---:|---:|---:|---:|
| A | 10 | 2 | 30s | 140 | 0 | 4.84 |
| B | 50 | 5 | 60s | 310 | 2 | 22.29 |
| C | 200 | 50 | 30s | 5200 | 11 | 42.46 |

1. Kịch bản có p95 cao nhất là gì? Dùng số liệu quan sát để giải thích.
 Kịch bản có p95 cao nhất là kịch bản C. P95 ở kịch bản C là 5200(ms) cao hơn hẳn so với kịch bản A và B.

2. Endpoint nào tăng failure rate? Phân biệt lỗi HTTP thực và lỗi đánh dấu trong Locust.
| Endpoint | A — lỗi/request (%) | B — lỗi/request (%) | C — lỗi/request (%) |
|---|---:|---:|---:|
| GET /books | 0 | 0 | 0 |
| GET /books/{id} | 0 | 0 | 0 |
| POST /books | 0 | 0 | 10 |
| GET /books?year=[year] | 0 | 2 | 1 |

Endpoint POST /books tăng failure rate (lỗi thực)
Endpoint GET /books?year=[year] (lỗi đánh dấu trong locust)
Dựa vào code trong endpoint POST /books, khi create_book có gọi db.session.commit(), SQLite chỉ cho phép một
lượt ghi tại một thời điểm, do đó khi có nhiều user gửi POST đồng thời thì có thể phải chờ dẫn đến 1 số request 
thất bại. 

3. Với SLO giả định p95 < 300 ms, kịch bản nào đạt? Nêu giới hạn của phép đo.
Dựa theo kết quả báo cáo, kịch bản đạt p95 < 300ms là kịch bản A.
Giới hạn của phép đo: mỗi kịch bản chỉ chạy trong 30-60s và có tốc độ tải khác nhau. Locust và Flask chạy trên 
cùng 1 máy local. Kết quả chỉ phản ánh môi trường local tại thời điểm thử nghiệm. Ngoài ra p95 gộp chung tất cả 
endpoint, nên cần xem xét riêng endpoint POST /books để đánh giá lại.

4. Nếu connection pool bị giới hạn ở 5, bạn sẽ kiểm chứng ảnh hưởng như thế nào?
Chạy cùng 1 kịch bản C, với 2 connection pool, 1 cái giới hạn ở 5, 1 cái giới hạn ở 20. Sau đó so sánh p95, RPS,
failure rate,..

> Không điền số liệu giả định vào bảng. Không khẳng định hiệu năng production
> từ SQLite + Flask development server trên máy cá nhân.
