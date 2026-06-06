# 🎯 AI 英语口语练习 (AI English Speaking Practice)

基于 Claude API 的 AI 英语口语对话练习工具 — 在模拟真实场景中与 AI 角色对话，获得实时语法纠正、发音评分和课后学习报告。

## ✨ 功能介绍

| 功能 | 说明 |
|------|------|
| 🎬 **场景化对话** | 6 个预设场景：咖啡店、酒店、餐厅、购物、看医生、工作面试，每个场景有独立角色、推荐词汇和语法重点 |
| 🎤 **语音输入** | 浏览器录音，通过 OpenAI Whisper 转写为文字 |
| 🤖 **AI 对话引擎** | Claude API 驱动的角色扮演对话，根据难度级别调整语言风格 |
| ✏️ **实时语法纠正** | AI 检测并纠正语法/用词/礼貌用语错误，附带中文解释 |
| 🔊 **语音合成** | Edge-TTS 将 AI 回复合成为语音，支持自动播放 |
| 📊 **发音评分** | 基于对话表现的动态发音评分 |
| 📝 **课后总结** | 综合评分、语法薄弱点分析、发音重点、词汇积累、改进建议 |

## 🛠️ 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **前端框架** | Vue 3 (Composition API) + TypeScript | SPA 应用 |
| **UI 组件库** | Naive UI 2.x | 卡片、标签、进度、消息提示等 |
| **图标** | @vicons/antd | Ant Design 图标集 |
| **构建工具** | Vite 6 | 开发服务器 + 生产打包 |
| **路由** | Vue Router 4 (Hash 模式) | 前端路由 |
| **后端框架** | FastAPI (Python 3.12) | RESTful API |
| **AI 对话** | Anthropic Claude API (claude-sonnet-4-6) | 角色扮演对话生成、语法纠正、学习总结 |
| **语音识别** | OpenAI Whisper API | 语音转文字 |
| **语音合成** | Edge-TTS | 文字转语音（免费、高质量） |
| **数据存储** | JSON 文件 (MVP) → SQLite (v1.1) | 对话记录持久化 |

## 📦 第三方依赖

### 前端 (Node.js)

| 包名 | 版本 | 用途 |
|------|------|------|
| `vue` | ^3.5.0 | 前端框架 |
| `vue-router` | ^4.4.0 | 路由管理 |
| `naive-ui` | ^2.39.0 | UI 组件库 |
| `@vicons/antd` | ^0.12.0 | 图标库 |
| `vite` | ^6.0.0 | 构建工具 |
| `@vitejs/plugin-vue` | ^5.1.0 | Vite Vue 插件 |
| `typescript` | ~5.6.0 | 类型检查 |
| `vue-tsc` | ^2.2.0 | Vue TypeScript 编译器 |

### 后端 (Python)

| 包名 | 版本 | 用途 |
|------|------|------|
| `fastapi` | >=0.110.0 | Web 框架 |
| `uvicorn[standard]` | >=0.27.0 | ASGI 服务器 |
| `python-multipart` | >=0.0.9 | 文件上传（音频） |
| `python-dotenv` | >=1.0.0 | 环境变量加载 |
| `anthropic` | >=0.40.0 | Claude API SDK |
| `openai` | >=1.60.0 | Whisper API SDK |
| `edge-tts` | >=6.1.0 | 微软 Edge TTS 合成 |

## 💡 原创功能说明

本项目在以下方面进行了自主设计与开发：

- **完整应用架构** — Vue 3 SPA + FastAPI 的全栈架构设计，包括组件树设计、路由规划、API 接口设计、状态流转
- **对话引擎** — 基于 Claude API 的角色扮演对话系统，包含 System Prompt 设计、JSON Schema 约束、上下文窗口管理（最近 10 轮）、降级模拟模式
- **语法纠正展示** — 前端 ChatBubble 组件以删除线原文 + 绿色纠正 + 中文解释的方式呈现语法纠正
- **语音交互链路** — MediaRecorder → Whisper STT → Claude 对话 → Edge-TTS → 自动播放的完整语音闭环
- **发音评分算法** — 基于 AI 纠正数量的动态评分模型（0 错误 8.5 分，1 错误 7.0 分，递增扣分）
- **6 个场景设计** — 每个场景包含角色设定、System Prompt、推荐词汇表、语法重点，覆盖初/中两个难度级别
- **课后报告 UI** — 综合评分的环形进度条 + 语法薄弱点（含出现次数和例句）+ 发音重点（含音素和练习词）+ 改进建议的分段展示
- **优雅降级** — 未配置 API Key 时自动切换到模拟模式，所有功能不报错、给出明确提示

使用第三方库实现的功能：Naive UI 提供 UI 组件（卡片、标签、弹窗等），Vue Router 提供路由，Claude API 提供 AI 对话生成，Whisper 提供语音识别，Edge-TTS 提供语音合成。

## 🚀 安装与运行

### 前提条件

- **Node.js** >= 18
- **Python** >= 3.10
- **Git** (可选，用于克隆仓库)

### 1. 克隆项目

```bash
git clone git@github.com:kl06021015-lang/demo.git
cd demo
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

### 3. 获取 API Key

- **Anthropic API Key**: 访问 [console.anthropic.com](https://console.anthropic.com) 注册并获取
- **OpenAI API Key**: 访问 [platform.openai.com](https://platform.openai.com) 注册并获取

> **提示**: 未配置 API Key 也能启动应用，AI 对话将使用模拟模式。

编辑 `backend/.env`：

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
```

### 4. 启动后端

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端运行在 `http://localhost:8000`，API 文档自动生成于 `http://localhost:8000/docs`

### 5. 启动前端

```bash
cd frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
```

前端运行在 `http://localhost:3000`，API 请求自动代理到后端。

### 6. 验证

1. 打开浏览器访问 `http://localhost:3000`
2. 选择一个场景卡片（如「咖啡店点单」）
3. 开始用英文与 AI 对话
4. 点击「结束对话」查看课后总结

## 📐 架构概览

```
┌─────────────────────────────────────────────────────┐
│                    浏览器 (Browser)                    │
│  ┌─────────────────────────────────────────────────┐ │
│  │              Vue 3 SPA (Vite Dev Server :3000)   │ │
│  │  ┌──────┐  ┌──────────┐  ┌──────────┐          │ │
│  │  │ Home │  │ Practice │  │ Summary  │          │ │
│  │  │ 场景  │  │  对话页   │  │  总结页   │          │ │
│  │  └──────┘  └──────────┘  └──────────┘          │ │
│  │       AudioRecorder  ·  ChatBubble              │ │
│  └─────────────────────────────────────────────────┘ │
│                         │  /api/*                     │
│                         ▼  (Vite Proxy)               │
│  ┌─────────────────────────────────────────────────┐ │
│  │          FastAPI Server (Uvicorn :8000)          │ │
│  │  routes: scenes · conversations · message · end │ │
│  │  ┌──────────────┐  ┌───────────────────────┐    │ │
│  │  │ Conversation │  │    SpeechService      │    │ │
│  │  │   Engine     │  │  Whisper STT · TTS    │    │ │
│  │  │ (Claude API) │  │                       │    │ │
│  │  └──────────────┘  └───────────────────────┘    │ │
│  │  ┌──────────────┐  ┌───────────────────────┐    │ │
│  │  │ Conversation │  │     SceneManager      │    │ │
│  │  │   Manager    │  │   (scenes.json)       │    │ │
│  │  │ (JSON files) │  │                       │    │ │
│  │  └──────────────┘  └───────────────────────┘    │ │
│  └─────────────────────────────────────────────────┘ │
│           │                    │                      │
│           ▼                    ▼                      │
│    ┌─────────────┐    ┌──────────────┐               │
│    │  Claude API │    │ OpenAI/Edge  │               │
│    │  (对话/AI)   │    │ (语音/合成)   │               │
│    └─────────────┘    └──────────────┘               │
└─────────────────────────────────────────────────────┘
```

## 🎬 Demo 视频

> 📺 [Demo 视频链接]（TODO: 上传至 B站/云盘后填入链接）

## 📁 项目结构

```
english-practice/
├── README.md
├── .gitignore
├── 作品提交规范.md
├── backend/
│   ├── .env.example          # API Key 配置模板
│   ├── requirements.txt      # Python 依赖
│   ├── main.py               # FastAPI 入口 & 路由
│   ├── services.py           # 核心业务逻辑
│   └── data/
│       ├── scenes.json       # 场景数据
│       └── conversations/    # 对话记录（运行时生成）
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    └── src/
        ├── main.ts           # Vue 应用入口
        ├── App.vue           # 根布局
        ├── api.ts            # API 调用 & 类型定义
        ├── router.ts         # 路由配置
        ├── views/
        │   ├── Home.vue      # 场景选择页
        │   ├── Practice.vue  # 对话练习页
        │   └── Summary.vue   # 课后总结页
        └── components/
            ├── AudioRecorder.vue  # 语音录制组件
            └── ChatBubble.vue     # 聊天气泡组件
```

## 📄 License

MIT
