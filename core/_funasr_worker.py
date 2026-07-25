"""
⚗️ FunASR 子进程 worker（隔离原生崩溃）

原因：本机父进程（经 WorkBuddy 启动的 Python）继承的环境块高达 ~340KB，远超
Windows 进程环境块约 32K 的上限；若把该巨型环境块传给子进程，子进程 C 运行库
（ucrtbase）初始化时会缓冲区溢出 -> 段错误 0xC0000005（无法被 try 捕获、会杀进程）。
故模型加载 + 转写放在本子进程里，且只接收「精简合法的小环境块」（见 FunASRBackend._clean_env）；
父进程在子进程崩了时自动重启重试，主进程永不被拖垮。

模型选型：用 Paraformer-zh（而非 SenseVoiceSmall）。原因：SenseVoiceSmall 在 funasr 1.3.23
的 generate 只返回整段文本（key/text 两字段），根本不吐时间轴；Paraformer-zh 原生支持
sentence_timestamp，返回每句的真实 start/end（毫秒）+ 逐字 timestamp，这才是「带真实时间轴」
的字幕。中文 CER 同样是 SOTA 级别，识别质量足够。

用法：
    python _funasr_worker.py <audio_path> [language]
stdout 仅输出一行 JSON：{"text": "...", "sentences": [{"start":s,"end":e,"text":"..."}, ...]}
或出错时 {"error": "..."}。其余日志（含模型下载进度）全部走 stderr。
"""
import sys
import os
import json

# 本 worker 以脚本方式运行，sys.path[0] 会是 core/ 目录；该目录下存在与标准库同名的
# queue.py，会遮蔽 stdlib `queue`，导致 funasr/torch 的 `from queue import Queue` 失败。
# 移除自身目录，避免遮蔽（worker 仅需 venv 内的 funasr/torch，不需要 core/ 在路径上）。
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR in sys.path:
    sys.path.remove(_SCRIPT_DIR)


def main():
    audio = sys.argv[1]
    # Paraformer 是中文模型；language 仅作占位以保持调用约定一致，不传给 generate。

    # 先把 torch 的 lib 目录直接放进 PATH 最前面，避免 torch import 时自己调用
    # os.add_dll_directory（其内部在本机会触发 ucrtbase 的坏指针 -> WinError 206/段错误）。
    import torch as _t  # noqa: F401  仅用于定位 torch/lib 路径
    torch_lib = os.path.join(os.path.dirname(_t.__file__), "lib")
    if torch_lib not in os.environ.get("PATH", ""):
        os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")

    from funasr import AutoModel
    model = AutoModel(
        model="paraformer-zh",
        vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        device="cpu",
        disable_update=True,
    )
    # sentence_timestamp=True -> 返回 sentence_info，每句带真实 start/end(ms) + 逐字 timestamp
    res = model.generate(input=audio, sentence_timestamp=True, batch_size_s=300)
    top = res[0] if res else {}
    raw_text = top.get("text", "") or ""
    sentences = []
    for s in top.get("sentence_info", []) or []:
        try:
            st = float(s.get("start", 0)) / 1000.0
            en = float(s.get("end", 0)) / 1000.0
        except Exception:
            st = en = 0.0
        txt = (s.get("text", "") or "").strip()
        if txt:
            sentences.append({"start": round(st, 2), "end": round(en, 2), "text": txt})
    print(json.dumps({"text": raw_text, "sentences": sentences}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 普通异常可捕获：以非零码退出，父进程重试
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(2)
