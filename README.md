# 🎯 AI 英语口语练习 (AI English Speaking Practice)

基于 讯飞 API 的 AI 英语口语对话练习工具 — 在模拟真实场景中与 AI 角色对话，获得实时语法纠正、发音评分、语音回听和课后学习报告。支持 Duolingo 风格的学习激励系统（目标打卡、连续天数、XP 等级、成就徽章）。

## 🎥 Demo 演示视频

👉 **[点击观看完整演示（Bilibili）](https://www.bilibili.com/video/BV1esE461ELt/)**

## ✨ 功能介绍

### 🎬 场景化对话
| 场景 | 难度 | 角色 |
|------|------|------|
| ☕ 咖啡店点单 | 初级 | 👨‍🍳 咖啡师 |
| 🏨 酒店入住 | 初级 | 🏨 前台接待 |
| 🍽️ 餐厅点餐 | 初级 | 🍽️ 服务员 |
| 🛍️ 商场购物 | 初级 | 🛍️ 导购 |
| 🏥 看医生 | 中级 | 👨‍⚕️ 医生 |
| 🏠 租房看房 | 中级 | 🏠 房东/中介 |
| 💼 工作面试 | 中级 | 💼 HR |
| 🎓 学术讨论 | 高级 | 👨‍🏫 教授 |
| 🎤 英语辩论 | 高级 | 👨‍⚖️ 辩论裁判 |

每个场景包含独立角色设定、System Prompt、推荐词汇表和语法重点，支持**难度筛选**和**进度追踪**。

### 🎤 语音交互

| 功能 | 说明 |
|------|------|
| 🔊 **语音输入** | 浏览器端 16kHz PCM/WAV 录制 → 讯飞实时语音识别 |
| 🎙️ **录音回听** | 用户语音持久化存储，对话中/刷新/历史回放均可播放 |
| 🔊 **AI 语音合成** | 多样 Edge-TTS 音色，自动播放 AI 回复 |

### 🤖 AI 对话引擎

| 功能 | 说明 |
|------|------|
| 💬 **流式回复** | SSE 流式传输，AI 回复逐字呈现 |
| ✏️ **实时语法纠正** | 检测语法/用词/礼貌用语错误，附带中文解释 |
| 🔄 **重新生成** | 对 AI 回复不满意可一键重新生成 |
| 📋 **一键复制** | 复制 AI 回复文本 |
| ⚡ **快捷回复** | 输入框上方显示场景相关的建议回复 |

### 📊 学习激励系统

| 功能 | 说明 |
|------|------|
| 🎯 **目标设定** | 每日/每周练习分钟目标，进度圈实时显示 |
| 🔥 **连续打卡** | 自动/手动打卡，火焰动画激励 |
| ⭐ **成就徽章** | 连续 3/7/30 天、累计时长、完成次数、高分评价等 9 种徽章 |
| 🏆 **XP 等级** | 基于练习时长和评分的经验值系统，升级解锁新场景 |
| 📅 **学习热力图** | GitHub 风格 7×52 贡献矩阵，展示全年练习分布 |
| 📈 **评分趋势** | 30 天综合评分折线图 |

### 📝 学习报告

| 功能 | 说明 |
|------|------|
| 🎯 **综合评分** | 对话级 1-10 分评分，彩色环形进度 |
| ✅ **表现亮点** | AI 总结的语法/表达方面的进步 |
| 📝 **语法薄弱点** | 高频错误类型、建议和例句 |
| 🔊 **发音重点** | 需重点练习的音素和练习词汇 |
| 💡 **改进建议** | 个性化的后续学习建议 |
| 📥 **导出报告** | 一键下载独立 HTML 格式学习报告 |

### 🎨 UI/UX 设计

| 特性 | 说明 |
|------|------|
| 🌿 **Duolingo 风格** | 翠绿主色调 `#58CC02` + 暖橙强调色 `#FF9600` |
| 🌙 **完整暗色模式** | Spotify/Linear 级别暗色方案，300ms 平滑过渡 |
| ✨ **微交互动画** | 撒花特效、骨架屏加载、弹簧消息入场、录音波形 |
| 📱 **响应式布局** | 适配桌面和移动端 |
| 🔤 **Inter 字体** | 专业级英文字体，优秀可读性 |

---

## 🛠️ 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| **前端框架** | Vue 3.5 (Composition API) + TypeScript | SPA 应用 |
| **UI 组件库** | Naive UI 2.x | 组件库 + 主题系统 |
| **图标** | @vicons/antd | Ant Design 图标集 |
| **构建工具** | Vite 6 | 开发服务器 + 生产打包 |
| **路由** | Vue Router 4 (Hash 模式) | 前端路由 |
| **后端框架** | FastAPI (Python 3.12) | RESTful API + SSE 流式 |
| **数据库** | SQLite (WAL 模式) | 对话/目标/打卡持久化 |
| **AI 对话** | Anthropic Claude API | 角色扮演 + 语法纠正 + 学习总结 |
| **语音识别** | 讯飞语音听写 API (WebSocket) | 实时语音转文字 |
| **语音合成** | Edge-TTS | 多音色文字转语音（免费） |
| **设计系统** | CSS 自定义属性 (60+ tokens) | 亮/暗主题统一设计令牌 |

---

## 📦 第三方依赖

### 前端

| 包名 | 版本 | 用途 |
|------|------|------|
| `vue` | ^3.5.0 | 前端框架 |
| `vue-router` | ^4.4.0 | 路由管理 |
| `naive-ui` | ^2.39.0 | UI 组件库 |
| `@vicons/antd` | ^0.12.0 | 图标库 |
| `vite` | ^6.0.0 | 构建工具 |
| `@vitejs/plugin-vue` | ^5.1.0 | Vite Vue 插件 |
| `typescript` | ~5.6.0 | 类型检查 |

### 后端

| 包名 | 版本 | 用途 |
|------|------|------|
| `fastapi` | >=0.110.0 | Web 框架 |
| `uvicorn[standard]` | >=0.27.0 | ASGI 服务器 |
| `python-multipart` | >=0.0.9 | 文件上传（音频） |
| `python-dotenv` | >=1.0.0 | 环境变量加载 |
| `anthropic` | >=0.40.0 | Claude API SDK |
| `openai` | >=1.60.0 | DeepSeek API（兼容接口） |
| `edge-tts` | >=6.1.0 | 微软 Edge TTS 合成 |
| `websockets` | >=12.0 | 讯飞 WebSocket STT |

---

## 💡 原创功能设计

本项目在以下方面进行了自主设计与开发：

- **完整全栈架构** — Vue 3 SPA + FastAPI 架构设计，包括组件树、路由规划、API 接口设计
- **对话引擎** — 基于 Claude API 的角色扮演系统，System Prompt 设计、JSON Schema 约束、流式 SSE 传输
- **语音交互闭环** — 前端 PCM/WAV 录制 → 讯飞 WebSocket STT → Claude 对话 → Edge-TTS → 自动播放，全链路自主实现
- **WAV 编码** — 浏览器端纯 JS 手写 WAV 编码器（44 字节文件头 + 16-bit PCM），无需 ffmpeg
- **发音评分算法** — 基于 AI 纠正数量的动态评分模型
- **持续激励系统** — 目标打卡、滑动窗口连续天数计算、XP/等级曲线、成就徽章自动颁发
- **学习热力图** — 纯 SVG 实现的 GitHub 风格贡献矩阵
- **语音持久化** — 用户录音保存至磁盘，支持跨会话回放
- **暗色模式** — 完整 CSS 自定义属性设计系统，60+ 令牌覆盖亮/暗双主题，300ms 平滑过渡
- **9 个场景设计** — 覆盖初/中/高三个难度级别，每个场景含角色、Prompt、词汇、语法重点
- **优雅降级** — API Key 未配置时自动切换模拟模式

---

## 🚀 安装与运行

### 前提条件

- **Node.js** >= 18
- **Python** >= 3.10
- **Git**

### 1. 克隆项目

```bash
git clone git@github.com:kl06021015-lang/demo.git
cd demo
```

### 2. 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:  venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
```

### 3. 配置 API Key

编辑 `backend/.env`：

```env


# 讯飞语音识别 — https://console.xfyun.cn
XFYUN_APP_ID=your-app-id
XFYUN_API_KEY=your-api-key
XFYUN_API_SECRET=your-api-secret

# DeepSeek API (对话引擎)
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

> 未配置 API Key 也能启动应用，AI 对话使用模拟模式。

### 4. 启动后端

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

后端运行在 `http://localhost:8000`，API 文档：`http://localhost:8000/docs`

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端运行在 `http://localhost:3000`，API 自动代理到后端。

---

## 📐 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                     浏览器 (Browser)                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │           Vue 3 SPA (Vite :3000)                         │ │
│  │  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │ │
│  │  │  Home  │ │ Practice │ │Dashboard │ │ Summary  │      │ │
│  │  │ 场景   │ │  对话页   │ │ 学习报告  │ │  课后总结 │      │ │
│  │  └────────┘ └──────────┘ └──────────┘ └──────────┘      │ │
│  │  ┌──────────┐ ┌───────────┐                              │ │
│  │  │ History  │ │Pronunciation│ (即将推出)                   │ │
│  │  │ 练习记录  │ │  发音练习   │                             │ │
│  │  └──────────┘ └───────────┘                              │ │
│  │                                                          │ │
│  │  Components: ChatBubble · AudioRecorder · TypingBubble  │ │
│  │             TimeSeparator · QuickReplies · Skeleton*    │ │
│  │             HeatmapChart · ScoreTrendChart · Confetti   │ │
│  │             FlameAnimation                               │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          │  /api/*                             │
│                          ▼  (Vite Proxy)                       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │           FastAPI Server (Uvicorn :8000)                  │ │
│  │                                                          │ │
│  │  Routes: scenes · conversations · dashboard · goals     │ │
│  │          checkins · audio · export · stream              │ │
│  │                                                          │ │
│  │  Services:                                               │ │
│  │  ┌──────────────┐ ┌─────────────────┐ ┌──────────────┐  │ │
│  │  │ Conversation │ │  SpeechService  │ │ SceneManager │  │ │
│  │  │   Engine     │ │  iFlytek STT   │ │ scenes.json  │  │ │
│  │  │ (Claude API) │ │  Edge TTS      │ │              │  │ │
│  │  └──────────────┘ └─────────────────┘ └──────────────┘  │ │
│  │                                                          │ │
│  │  Database (SQLite):                                      │ │
│  │  ┌──────────────┐ ┌──────────┐ ┌──────────┐            │ │
│  │  │ conversations│ │  goals   │ │ checkins │            │ │
│  │  │   + turns    │ │          │ │          │            │ │
│  │  └──────────────┘ └──────────┘ └──────────┘            │ │
│  │                                                          │ │
│  │  File Storage:                                           │ │
│  │  ┌──────────────────────────────────────────┐           │ │
│  │  │  data/audio/{session_id}/turn_NNN.wav    │           │ │
│  │  └──────────────────────────────────────────┘           │ │
│  └──────────────────────────────────────────────────────────┘ │
│           │                    │                               │
│           ▼                    ▼                               │
│    ┌─────────────┐    ┌─────────────────┐                     │
│    │  Claude API │    │  iFlytek / Edge │                     │
│    │  (对话引擎)   │    │  (语音识别/合成) │                     │
│    └─────────────┘    └─────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 项目结构

```
english-practice/
├── README.md
├── .gitignore
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── main.py                   # FastAPI 入口 & 全部路由
│   ├── services.py               # 核心业务逻辑
│   ├── database.py               # SQLite 数据库层
│   └── data/
│       ├── scenes.json           # 场景数据 (9 个)
│       ├── english_practice.db   # SQLite 数据库
│       └── audio/                # 用户语音录音 (运行时生成)
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    └── src/
        ├── main.ts               # Vue 应用入口
        ├── App.vue               # 根布局 + 导航 + 主题
        ├── api.ts                # API 调用 & TypeScript 类型
        ├── router.ts             # 路由配置
        ├── styles/
        │   └── theme.css         # 设计系统 (60+ CSS 自定义属性)
        ├── composables/
        │   ├── useTheme.ts       # 暗/亮主题管理 + Naive UI 集成
        │   └── useScrollAnchor.ts # 智能滚动锚点
        ├── views/
        │   ├── Home.vue          # 场景选择页
        │   ├── Practice.vue      # 对话练习页
        │   ├── Dashboard.vue     # 学习报告页
        │   ├── Summary.vue       # 课后总结页
        │   └── History.vue       # 练习记录页
        └── components/
            ├── ChatBubble.vue        # 聊天气泡 (头像/纠错/操作)
            ├── AudioRecorder.vue     # 语音录制 (PCM+WAV)
            ├── chat/
            │   ├── TypingBubble.vue  # AI 正在输入动画
            │   ├── TimeSeparator.vue # 消息时间分隔线
            │   └── QuickReplies.vue  # 快捷回复建议
            ├── dashboard/
            │   ├── HeatmapChart.vue   # GitHub 风格贡献热力图
            │   └── ScoreTrendChart.vue # 30 天评分趋势图
            ├── animations/
            │   ├── ConfettiEffect.vue # 撒花动画
            │   └── FlameAnimation.vue # 连续打卡火焰
            └── skeleton/
                ├── SkeletonCard.vue   # 卡片骨架屏
                ├── SkeletonLine.vue   # 文本行骨架屏
                └── SkeletonBubble.vue # 聊天气泡骨架屏
```

---

## 🔌 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/scenes` | 获取所有场景 |
| `POST` | `/api/conversations` | 创建新对话 |
| `GET` | `/api/conversations` | 对话历史列表 |
| `GET` | `/api/conversations/{id}` | 获取完整对话记录 |
| `DELETE` | `/api/conversations/{id}` | 删除对话 |
| `POST` | `/api/conversations/{id}/message` | 发送消息 (文本/语音) |
| `POST` | `/api/conversations/{id}/message/stream` | 流式发送消息 (SSE) |
| `POST` | `/api/conversations/{id}/end` | 结束对话并生成总结 |
| `GET` | `/api/conversations/{id}/export` | 导出 HTML 学习报告 |
| `GET` | `/api/dashboard` | 学习统计仪表盘 |
| `GET` | `/api/goals` | 获取活跃目标 |
| `POST` | `/api/goals` | 设定学习目标 |
| `POST` | `/api/checkins` | 记录打卡 |
| `GET` | `/api/checkins` | 打卡历史 |
| `GET` | `/api/audio/{session_id}/{filename}` | 播放用户语音录音 |

---

## 📄 License

MIT
