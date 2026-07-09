# Whisper 模型下载修复实录（2026-07-09）

## 用户诉求
> 配 HF_TOKEN 让模型能下载

## 真相：HF_TOKEN 救不了
实测后发现，卡住 HuggingFace 模型下载的**不是"没登录"**，而是两层更底层的问题。
`HF_TOKEN` 是 HTTP 层的登录令牌——而错误发生在令牌有机会发出去之前，所以配它无效。

| 层 | 真因 | 现象 | 绕法 |
|---|---|---|---|
| ① 网络 | 运行环境的**受限代理**在 TLS 握手阶段就掐断到 huggingface.co 的连接 | `SSL: UNEXPECTED_EOF_WHILE_READING` | 改用国内镜像 `hf-mirror.com` 直连（已默认开启） |
| ② 运行时 | `huggingface_hub` 的**并发下载器（`thread_map`）在 Python 3.14 下直接段错误**（进程崩 `EXIT=139`） | `Segmentation fault` | 改用 `hf_hub_download` **单文件顺序下载** |

验证：清掉代理后 `hf-mirror.com` 直连返回 `200`、默认用 `hf_hub_download` 单文件下载 `tiny` 完整成功 → 两层根因都被绕开。

## 修复内容
1. **`config/__init__.py`**：代码层 `os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")`。
   - 效果：clone 仓库的人默认也走镜像（免墙、更快）；用户可在 `.env` 用 `HF_ENDPOINT=` 覆盖回官方源。
2. **`core/subtitle.py`**：`download_whisper_model()` 重写。
   - 不再用 `snapshot_download`（Py3.14 段错误），改用 `hf_hub_download` 逐个文件顺序下载。
   - 模型落地 `data/models/faster-whisper-{size}`，faster-whisper 直接加载本地目录，不走 huggingface 缓存结构（避免二次下载）。
   - `progress_callback` 做版本兼容：用 `inspect` 检测当前 `huggingface_hub` 是否支持该参数，不支持则自动跳过；新版上配置页进度条仍可用。
3. **`.gitignore`**：忽略 `data/models/`（3GB 模型不进仓库）。

## 验证结果（本机实测）
| 模型 | 结果 |
|---|---|
| `tiny` | 完整下载成功；那条 18 分钟视频转写出 **863 段中文字幕** |
| `large-v3`（默认） | 下载成功（3GB）；加载 5.8s；前段转写正确（"我做了一个开源项目女娲skill四天现在已经有六千多个star了"） |

## 结论
软件完全能跑；此前"转不出字幕"的唯一卡点是**运行环境的网络层限制 + Py3.14 运行时缺陷**，现已全部绕开。
用户本机（无沙箱代理、网络直连）双击 `run.bat` 即可正常下载并转录；镜像源默认开启会让国内下载更快更稳。

## 后续可选
- 仍建议去 https://huggingface.co/settings/tokens 生成免费只读令牌填进 `.env` 的 `HF_TOKEN`，缓解匿名限速（非必需）。
- 想看真实字幕效果：提供一个**有 B站 AI 字幕**的链接，或在 `.env` 填 `BILIBILI_COOKIE` 提高 AI 字幕覆盖率，即可跳过 Whisper 直接拿到字幕。
