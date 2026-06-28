# CODEBUDDY.md

## 项目信息

- **项目名称**: Nigredo · 馏析
- **描述**: 外部数据采集引擎
- **本地路径**: `D:\nigredo\`
- **GitHub**: `shiyao222333-afk/nigredo`

## Python 环境

- **Python**: 3.13.12（managed）
- **路径**: `C:\Users\Lenovo\.workbuddy\binaries\python\versions\3.13.12\python.exe`
- **虚拟环境**: `C:\Users\Lenovo\.workbuddy\binaries\python\envs\default`
- **安装命令**: `C:\Users\Lenovo\.workbuddy\binaries\python\envs\default/bin/pip install -r requirements.txt`

## 启动

```bash
cd D:\nigredo
streamlit run app.py
```

- Web UI: `http://127.0.0.1:8502`

## 项目结构

```
nigredo/
├── app.py              # Streamlit 主入口
├── pages/              # UI 页面
├── core/               # 核心逻辑（Streamlit-free）
├── platforms/          # 平台适配器
├── prompts/            # LLM Prompt 模板
├── utils/              # 工具
├── config/             # 配置
├── BLUEPRINT.md        # 项目宪法
├── PROJECT_PLAN.md     # 版本路线图
├── FLOWCHART.md        # 流程框图
├── CHANGELOG.md        # 变更记录
├── README.md           # 对外介绍
├── .env.example        # 环境变量模板
└── requirements.txt
```

## 关联项目

| 项目 | 路径 | 关系 |
|------|------|------|
| Citrinitas | `D:\citrinitas\` | 知识引擎——Nigredo 数据最终注入 Qdrant |
| Rubedo | `D:\rubedo\` | SOP 自动化——通过 API 调用 Nigredo |
| Albedo | `D:\albedo\` | 矛盾检测 |
| OpusMagnum | `D:\opus-magnum\` | 总蓝图 |

## Git 操作

- **Push**: 在 PowerShell 中执行，token 作为用户名
- `git remote set-url origin "https://<TOKEN>@github.com/shiyao222333-afk/nigredo.git"`
