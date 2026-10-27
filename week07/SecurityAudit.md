# Security Audit - Social Network API

Phạm vi: `POST /auth/login`, `POST /auth/refresh` và `GET /posts/{id}`.
Các điểm dưới đây là những nơi dữ liệu hoặc credential có thể bị lộ trong
quá trình gửi request, xử lý, lưu trữ và trả response.

| # | Điểm có thể lộ | Tác động | Giảm thiểu |
| --- | --- | --- | --- |
| 1 | Mật khẩu trong request login bị ghi vào application, proxy, APM hoặc debug log. | Kẻ có log có thể chiếm tài khoản, nhất là khi mật khẩu được dùng lại. | Không log body hoặc header nhạy cảm; lọc/redact ở gateway, APM và exception handler; chỉ ghi mã sự kiện cần thiết. |
| 2 | Access/refresh token bị ghi log, gửi trong URL, analytics, crash report hoặc telemetry. | Token bearer có thể bị phát lại để chiếm phiên. | Chỉ gửi access token trong `Authorization`; chỉ gửi refresh token trong body của `/auth/refresh`; không ghi credential; redact các trường token; bắt buộc HTTPS. |
| 3 | JWT payload chứa PII, email, secret hoặc dữ liệu hồ sơ. | Payload JWT ký thường chỉ được mã hóa Base64URL, ai lấy token cũng đọc được claims. | Chỉ lưu `sub`, `iss`, `aud`, `iat`, `exp`, `jti` và claims quyền tối thiểu; không đưa mật khẩu/secret/PII không cần thiết vào token. |
| 4 | Token được lưu trong `localStorage` hoặc `sessionStorage` của trình duyệt. | XSS hoặc script bên thứ ba bị xâm nhập có thể đọc và đánh cắp token. | Với web app, ưu tiên BFF hoặc cookie `HttpOnly`, `Secure`, `SameSite` phù hợp; bảo vệ CSRF khi dùng cookie và phòng XSS. |
| 5 | Câu trả lời login khác nhau theo email tồn tại, mật khẩu sai, tài khoản khóa hoặc thời gian xử lý. | Attacker dò tài khoản và trạng thái người dùng. | Dùng cùng status/message `401 invalid_credentials`, xử lý thời gian gần đồng đều, không xác nhận email có tồn tại; giới hạn tốc độ login. |
| 6 | Không giới hạn login/refresh hoặc phản hồi rate-limit để lộ dữ liệu vận hành quá chi tiết. | Credential stuffing, brute force, gây quá tải; lỗi chi tiết hỗ trợ dò cấu hình. | Rate-limit theo tài khoản và IP với ngưỡng phù hợp; trả `429` chung và `Retry-After`; không khóa tài khoản theo cách dễ bị lợi dụng DoS. |
| 7 | Refresh token dùng lại sau khi bị lộ hoặc không bị thu hồi khi logout/rotation. | Kẻ tấn công duy trì phiên dài hạn và tiếp tục xin access token. | Refresh token opaque hoặc JWT có `jti`; rotate một lần mỗi lần dùng; phát hiện reuse; lưu trạng thái phiên/revocation; thu hồi cả token liên quan khi logout hoặc có sự cố. |
| 8 | JWT được xác minh bằng thuật toán lấy từ token, thiếu kiểm tra `iss`, `aud`, `exp` hoặc loại token. | Token giả, token của dịch vụ khác hoặc refresh token bị chấp nhận làm access token. | Whitelist thuật toán cố định; kiểm chữ ký, issuer, audience, thời hạn, `jti` và claim phân biệt `typ`/`token_use`; tách khóa cho mục đích khác nhau. |
| 9 | `GET /posts/{id}` chỉ kiểm tra `posts:read` mà bỏ qua quyền trên object. | BOLA: người dùng đổi ID và đọc bài followers/private hoặc bài thuộc tenant khác. | Kiểm tra visibility, owner, quan hệ follow/share và tenant trên từng bài; không coi scope là bằng chứng quyền object; trả cùng `404` cho bài không tồn tại và bài không được phép xem. |
| 10 | Body lỗi, stack trace, SQL hoặc thông tin token/ID nội bộ được trả về client. | Rò chi tiết triển khai, dữ liệu hoặc thông tin giúp tấn công tiếp. | Dùng error schema chung; không trả stack trace/SQL/secret/claims nhạy cảm; log nội bộ có kiểm soát và không ghi credential. |

## Các giả định được ghi trong OpenAPI

- API chỉ chạy qua HTTPS.
- `/auth/login` là public, không cần scope trước; credential sai trả lỗi chung.
- `/auth/refresh` dùng refresh token có scope `session:refresh`, rotate token khi thành công.
- `/posts/{id}` cần access token scope `posts:read` và kiểm tra quyền trên từng bài.
- JWT access token ngắn hạn; cấu hình thuật toán, issuer, audience, thời hạn và thu hồi thuộc trách nhiệm triển khai.
