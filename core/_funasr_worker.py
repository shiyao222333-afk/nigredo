"""
⚗️ FunASR 子进程 worker（隔离原生崩溃）

原因：本机父进程（经 WorkBuddy 启动的 Python）继承的环境块高达 ~340KB，远超
Windows 进程环境块约 32K 的上限；若把该巨型环境块传给子进程，子进程 C 运行库
（ucrtbase）初始化时会缓冲区溢出 -> 段错误 0xC0000005（无法被 try 捕获、会杀进程）。
故模型加载 + 转写放在本子进程里，且只接收「精简合法的小环境块」（见 FunASRBackend._clean_env）；
父进程在子进程崩了时自动重启重试，主进程永不被拖垮。

模型选型：
- paraformer（默认）：Paraformer-zh，纯中文、句子级真实时间轴（sentence_info）。
- funasr_nano：FunAudioLLM/Fun-ASR-Nano-2512，中英混说 SOTA，字符级时间戳
  （timestamps：每字 start/end 秒），本 worker 在子进程内聚合成句子级片段，
  输出与 paraformer 统一的 {"text", "sentences":[{start,end,text}]} 结构，
  保证上层 _parse 不用改、时间轴（G2 自检）不丢。

用法：
    python _funasr_worker.py <audio_path> [language] [model] [device]
    model:   paraformer | funasr_nano    （默认 paraformer）
    device:  cpu | cuda | auto           （默认 cpu；auto=有显卡用 cuda 否则 cpu）
stdout 仅输出一行 JSON：{"text": "...", "sentences": [{"start":s,"end":e,"text":"..."}, ...]}
或出错时 {"error": "..."}。其余日志（含模型下载进度）全部走 stderr。
"""
import sys
import os
import json
import re

# 本 worker 以脚本方式运行，sys.path[0] 会是 core/ 目录；该目录下存在与标准库同名的
# queue.py，会遮蔽 stdlib `queue`，导致 funasr/torch 的 `from queue import Queue` 失败。
# 移除自身目录，避免遮蔽（worker 仅需 venv 内的 funasr/torch，不需要 core/ 在路径上）。
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR in sys.path:
    sys.path.remove(_SCRIPT_DIR)

# 句末标点（用于把字符级时间戳聚合成句子级片段）
_SENT_END = set("。！？!?；\n")


def group_nano_timestamps(ts: list) -> list:
    """把 FunASR-Nano 的字符级时间戳聚合成句子级片段。

    ts: [{"token": str, "start_time": float, "end_time": float}, ...]（秒）。
    按句末标点切句；每句取组内最小 start / 最大 end。时间轴原样保留。
    任何异常都返回 []，由调用方退回单段兜底（绝不伪造时间轴）。
    """
    if not ts:
        return []
    sentences = []
    cur_text = []
    cur_start = None
    cur_end = None
    for t in ts:
        tok = (t.get("token") or "").strip()
        try:
            st = float(t.get("start_time") or 0)
            en = float(t.get("end_time") or 0)
        except (TypeError, ValueError):
            st = en = 0.0
        if not tok:
            continue
        cur_text.append(tok)
        cur_start = st if cur_start is None else min(cur_start, st)
        cur_end = en if cur_end is None else max(cur_end, en)
        if tok in _SENT_END:
            if cur_text:
                sentences.append({
                    "start": round(cur_start, 2),
                    "end": round(cur_end, 2),
                    "text": "".join(cur_text).strip(),
                })
            cur_text, cur_start, cur_end = [], None, None
    if cur_text:
        sentences.append({
            "start": round(cur_start, 2),
            "end": round(cur_end, 2),
            "text": "".join(cur_text).strip(),
        })
    return [s for s in sentences if s["text"]]


def main():
    audio = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "zh"
    model = sys.argv[3] if len(sys.argv) > 3 else "paraformer"
    device_arg = sys.argv[4] if len(sys.argv) > 4 else "cpu"

    # 先把 torch 的 lib 目录直接放进 PATH 最前面，避免 torch import 时自己调用
    # os.add_dll_directory（其内部在本机会触发 ucrtbase 的坏指针 -> WinError 206/段错误）。
    import torch as _t  # noqa: F401  仅用于定位 torch/lib 路径
    torch_lib = os.path.join(os.path.dirname(_t.__file__), "lib")
    if torch_lib not in os.environ.get("PATH", ""):
        os.environ["PATH"] = torch_lib + os.pathsep + os.environ.get("PATH", "")

    if device_arg == "auto":
        device = "cuda" if _t.cuda.is_available() else "cpu"
    else:
        device = device_arg

    from funasr import AutoModel

    if model == "funasr_nano":
        amodel = AutoModel(
            model="FunAudioLLM/Fun-ASR-Nano-2512",
            vad_model="fsmn-vad",
            device=device,
            disable_update=True,
        )
        res = amodel.generate(input=audio)
        top = res[0] if res else {}
        raw_text = top.get("text", "") or ""
        # FunASR-Nano 返回字符级时间戳；本 worker 聚合为句子级，输出统一结构。
        sentences = group_nano_timestamps(top.get("timestamps") or [])
        if not sentences and raw_text:
            # 兜底：时间戳缺失时退回单段（无时间轴，但绝不伪造）
            sentences = [{"start": 0.0, "end": 0.0, "text": raw_text.strip()}]
        print(json.dumps({"text": raw_text, "sentences": sentences}, ensure_ascii=False))
        return

    # 默认：Paraformer-zh（中文模型；language 仅作占位，不传给 generate）
    model_obj = AutoModel(
        model="paraformer-zh",
        vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
        punc_model="iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
        device="cpu",
        disable_update=True,
    )
    # sentence_timestamp=True -> 返回 sentence_info，每句带真实 start/end(ms) + 逐字 timestamp
    res = model_obj.generate(input=audio, sentence_timestamp=True, batch_size_s=300)
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
