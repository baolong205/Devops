# Supabase + Vercel CI/CD

Website giới thiệu cá nhân tĩnh, đọc danh sách kỹ năng và ghi lời nhắn vào Supabase.

## Chạy local

1. Tạo project tại [Supabase](https://supabase.com), mở SQL Editor và chạy toàn bộ file `supabase/schema.sql`.
2. Sao chép `.env.local.example` thành `.env.local`, điền URL và anon key của project.
3. Thay hai placeholder trong `index.html` bằng giá trị trong `.env.local`, sau đó mở `index.html` bằng Live Server.

Anon key được phép xuất hiện ở frontend. Không dùng `service_role` key trong website.

## Cấu hình GitHub Actions

Tạo các repository secrets sau trong **Settings > Secrets and variables > Actions**:

| Secret | Giá trị |
| --- | --- |
| `SUPABASE_URL` | Project URL của Supabase |
| `SUPABASE_ANON_KEY` | Publishable/anon key của Supabase |
| `VERCEL_TOKEN` | Token tạo trong Vercel Account Settings |
| `VERCEL_ORG_ID` | Organization ID trong `.vercel/repo.json` |
| `VERCEL_PROJECT_ID` | Project ID trong `.vercel/repo.json` |

Sau khi push lên nhánh `main`, workflow `.github/workflows/deploy.yml` sẽ thay placeholder, build và deploy production lên Vercel. Có thể chạy thủ công bằng **Actions > Deploy to Vercel > Run workflow**.

## Kết nối Jenkins với GitHub

Jenkins chạy bằng Docker Compose tại `http://localhost:8080`. Cấu hình hiện tại đã cài plugin GitHub và pipeline, đồng thời Jenkins sẽ đọc pipeline từ file `Jenkinsfile` trong repository.

1. Chạy `docker compose up -d --build` để khởi động Jenkins.
2. Mở `http://localhost:8080`, hoàn tất setup wizard và tạo một **Pipeline**.
3. Trong pipeline, chọn **Pipeline script from SCM**, SCM là **Git**, repository URL là `https://github.com/baolong205/Devops.git`, branch là `*/main`, script path là `Jenkinsfile`.
4. Trong GitHub vào **Settings > Webhooks > Add webhook**:
	- Payload URL: `https://<jenkins-public-host>/github-webhook/`
	- Content type: `application/json`
	- Events: **Just the push event**
	- Active: bật
5. Nếu repository là private, thêm GitHub Personal Access Token vào Jenkins tại **Manage Jenkins > Credentials > System > Global credentials**, loại **Username with password**, username là GitHub username và password là token. Chọn credential đó trong pipeline SCM.

`localhost` chỉ dùng để truy cập Jenkins từ máy cá nhân. GitHub không thể gọi webhook tới `localhost`; cần một hostname/IP công khai có HTTPS hoặc tunnel như ngrok/Cloudflare Tunnel.

## Kết nối Jenkins với Vercel

1. Tạo token Vercel ở [Vercel Account Settings > Tokens](https://vercel.com/account/tokens).
2. Trong Jenkins, vào **Manage Jenkins > Credentials > System > Global credentials** và tạo 3 secret text credentials:
   - `vercel-token`
   - `vercel-org-id`
   - `vercel-project-id`
3. Giá trị `vercel-org-id` và `vercel-project-id` lấy từ file `.vercel/repo.json` trong repo.
4. Khi push lên GitHub hoặc chạy **Build Now**, Jenkins sẽ tự chạy stage `Deploy to Vercel` và deploy lên Vercel production.

Ví dụ giá trị hiện tại trong repo:

- `VERCEL_ORG_ID`: `team_pQxWlQjkLXzxOMVVh8XyNAwe`
- `VERCEL_PROJECT_ID`: `prj_sMRuThjd9LGY0bWylFqwDRCaxpO4`

## Thông báo deploy qua Telegram

1. Tạo bot bằng `@BotFather` trên Telegram và lưu bot token.
2. Lấy chat ID của tài khoản/nhóm nhận thông báo.
3. Trong Jenkins, tạo hai credential loại **Secret text**:
	- ID `telegram-bot-token`: bot token.
	- ID `telegram-chat-id`: chat ID nhận thông báo.
4. Pipeline sẽ gửi thông báo bắt đầu deploy, kết quả thành công hoặc thất bại. Tin nhắn lỗi dẫn tới build Jenkins Console Output để xem chi tiết; lỗi gửi Telegram không làm fail deployment.