# 长沙活动雷达｜Render 部署版

本版本改为 **Render 网站服务 + Supabase PostgreSQL 数据库 + GitHub Actions 每日定时触发**。
这样网站即使在 Render 免费方案下休眠，也不会依赖本地磁盘保存活动数据；每日采集由 GitHub Actions 在北京时间 08:00（UTC 00:00）发起。

## 需要你完成的账号授权步骤
1. 将本项目全部文件上传到 GitHub 仓库（包括 `app/` 文件夹和 `.github/workflows/daily-collect.yml`）。
2. 在 Supabase 创建一个新项目，复制 PostgreSQL 连接串（优先使用 Session pooler / Transaction pooler 提供的连接串，按 Supabase 当前说明选择）。连接串作为 Render 的 `DATABASE_URL`，不要公开或发给别人。
3. 在 Render 选择 New → Blueprint，连接 GitHub 仓库并部署 `render.yaml`。首次部署时按提示填写 `DATABASE_URL`。
4. 部署完成后，复制 Render 网站域名。
5. 在 GitHub 仓库 Settings → Secrets and variables → Actions 新增：
   - `SITE_URL`：Render 网站完整地址，例如 `https://你的服务名.onrender.com`（末尾不要加 `/`）
   - `COLLECT_SECRET`：Render 服务 Environment 中自动生成的同名密钥值
6. 在 GitHub Actions 页面手动运行一次 `Daily Changsha Event Collection`，确认日志成功。以后每天北京时间 08:00 自动运行。

## API
- `GET /api/health`
- `GET /api/events`
- `GET /api/events?category=展览`
- `GET /api/events?q=音乐`
- `GET /api/events/{id}`
- `GET /api/logs`
- `POST /api/collect`（必须带 `X-Collect-Secret` 请求头）
- `PATCH /api/events/{id}/verification?status=官方已确认`

## 重要说明
- Render 免费 Web Service 可能休眠，首次访问可能需要等待唤醒；免费服务的运行与资源限制以 Render 当前官方价格说明为准。
- Supabase 免费数据库有容量、暂停和使用限制，具体以其当前套餐说明为准。
- GitHub Actions 定时任务可能有调度延迟，不保证精确到 08:00:00。
- 当前采集器仍是 MVP，只从已配置的公开网页来源做通用 HTML 解析；可能因反爬、页面改版或源站限制而失败。活动默认标记为“待核实”，不能把未核实内容当成官方确认。
- 不要把 `DATABASE_URL`、`COLLECT_SECRET` 提交到公开仓库或发在聊天里。
