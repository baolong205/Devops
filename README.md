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
