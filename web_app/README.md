# Web 面板开发

基于 FastAPI + Socket.IO (ASGI) 的 Web 服务，为 seseget 提供可视化操作面板。

## 架构总览

```
seseget(core) ──调用接口──> FastAPI 后端 <──托管静态文件── React SPA (Vite 构建)
```

- 前端是独立项目 [web_frontend](../web_frontend)，构建后产物复制到 `static/` 目录，由 FastAPI 统一提供

## 开发环境

### 前提条件

- Python 3.11+
- Node.js 22+

### 1. 克隆项目并安装依赖

```bash
# 创建虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate.bat
# Linux / macOS
source .venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt -r web_app/requirements.txt

# 安装前端依赖
cd web_frontend
npm install
cd ..
```

### 2. 启动开发环境（两个终端）

```bash
# 终端 1: 启动后端
python -m web_app

# 终端 2: 启动前端
cd web_frontend
npm run dev
```

访问 http://localhost:3000 进入 Web 面板（Vite 自动代理 API 请求到后端）

### 3. 构建生产版本

```bash
cd web_frontend
npm run build        # 编译 TypeScript + Vite 打包 + 自动复制到 web_app/static/

# 生产环境运行
cd ..
python -m web_app --prod --host 0.0.0.0 --port 12450
```

## API
文档开发中
