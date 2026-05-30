# financial-helper

财税票据自动处理：发票上传识别、合规审核、会计凭证生成与 Excel 导出。

## 架构

- **后端** `apps/api` — FastAPI，端口 **8001**
- **前端** `apps/web` — Next.js，端口 **3001**
- **数据** `data/` — 本地媒体与 JSON 索引（已 gitignore）

## 快速开始

### 1. 后端

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 填入 PADDLEOCR_TOKEN、DEEPSEEK_API_KEY 等
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### 2. 前端

```bash
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev
```

浏览器打开 http://localhost:3001

支持上传 **PDF 发票**（自动转 PNG 后 OCR，多页会逐页识别并合并文本）。

### 3. 环境变量

| 变量 | 说明 |
|------|------|
| `PADDLEOCR_TOKEN` | PaddleOCR AI Studio API Token |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `COMPANY_BUYER_NAME` / `COMPANY_BUYER_TAX_ID` | 购买方合规校验（可选） |

## API 概览

见 [contracts/openapi.yaml](contracts/openapi.yaml)。

## 文档

- **[使用说明](docs/使用说明.md)**（安装、配置、操作指南）
- [设计方案](docs/财税票据自动处理-设计方案.md)
- [规则与数据结构](docs/规则与数据结构.md)
- [功能验证记录](功能点.md)

## 配置安全

请勿将 `apps/api/.env`、`apps/web/.env.local` 提交到仓库；仅使用 `.env.example` / `.env.local.example` 作为模板。
