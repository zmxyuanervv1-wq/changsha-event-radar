# 长沙活动雷达 · V1 后端采集 MVP

## 当前实现
- FastAPI + SQLite 活动数据库
- 活动列表、搜索、分类、详情 API
- 来源采集日志
- 每天 08:00（Asia/Shanghai）定时采集
- 手动触发采集 API：`POST /api/collect`
- 活动核实状态：待核实 / 来源已发布 / 官方已确认
- 第一批采集入口：长沙本地宝活动汇总与活动资讯页

## 启动
Python 3.10+
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
打开 `http://127.0.0.1:8000` 使用网站首页；打开 `http://127.0.0.1:8000/docs` 查看 API。首页会尝试从后端读取活动数据，若尚无采集数据则显示内置演示卡片。

Windows 用户也可双击 `run.bat`。macOS/Linux 可运行 `bash run.sh`。

## API
- `GET /api/health`
- `GET /api/events`
- `GET /api/events?category=展览`
- `GET /api/events?q=音乐`
- `GET /api/events/{id}`
- `GET /api/logs`
- `POST /api/collect` 手动执行一次采集
- `PATCH /api/events/{id}/verification?status=官方已确认`

## 重要限制与上线前工作
1. 采集器目前是通用 HTML 解析 MVP。网站页面结构变化、反爬限制、网络不可达都会导致采集失败；失败会记入日志。
2. 采集器不会把抓到的页面直接标成“官方已确认”，新数据一律为“待核实”。日期、价格和地点提取是规则初筛，可能不完整，需人工检查原文。
3. 第一批来源是长沙本地宝的公开活动列表/资讯页。继续增加长沙晚报、文旅部门、场馆和票务平台时，应逐站检查 robots、服务条款、授权及页面结构；优先使用官方 API/RSS/公开数据，不绕过登录、验证码或访问限制。
4. 当前未集成大模型 API，也没有从社交平台/公众号私域内容抓取。若需要 AI 结构化抽取，可在后续接入你选择的模型服务并配置密钥，不要把密钥写进前端。
5. 收藏目前仍由前端浏览器 localStorage 保存；若将来做多设备/公开用户系统，再增加用户认证与云端收藏。
6. 这套程序必须部署在持续运行的服务器/云平台上，才能保证每天 08:00 自动执行。仅在本地电脑关机时不会运行。
7. 请先本地测试采集结果，再部署；不要把未经核实的活动直接当作真实推荐。

## 目录
- `app/main.py` API 与定时任务
- `app/collector.py` 采集逻辑
- `app/database.py` SQLite 初始化
- `requirements.txt` 依赖


## Railway 部署（建议方案）
本项目已加入 Dockerfile 和 railway.toml，可从 GitHub 仓库部署到 Railway。

1. 将整个项目文件夹上传到你自己的 GitHub 新仓库（不要上传 `.env` 或数据库文件）。
2. 登录 Railway，选择 New Project → Deploy from GitHub Repo，授权并选择该仓库。
3. 部署成功后，在服务 Settings / Networking 中生成 Public Domain。
4. 在服务中添加 Volume，挂载路径设为 `/data`。数据库路径已设置为 `/data/events.db`，这样数据可以保留。
5. 在 Variables 中确认 `TZ=Asia/Shanghai`、`COLLECT_HOUR=8`、`COLLECT_MINUTE=0`。
6. 等部署状态变为 Healthy，打开 Railway 生成的域名；`/api/health` 应返回 `ok: true`。

提示：Railway 的服务与存储按平台当前套餐计费；请先查看账户费用和用量设置。部署后建议设置用量提醒/预算限制。Railway 的公开域名需在 Networking 中生成。

## 真实运行的前提
- 自动采集任务随常驻 Web 服务运行，每天北京时间 08:00 执行。
- Railway 服务必须保持运行；若暂停/超额/服务异常，定时任务不会执行。
- 采集来源当前只是 MVP，采集成功率取决于源站页面结构和访问规则；需持续检查日志并补充可靠来源。
