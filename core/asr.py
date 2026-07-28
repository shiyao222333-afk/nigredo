"""
⚗️ Nigredo — 模块化 ASR 后端

把「语音识别」抽象成统一接口，同一套调用可切换不同引擎，
切换只改配置（ASR_BACKEND），不动任何业务代码。

接口约定（所有后端必须返回）：
    transcribe(audio_path, language="zh") -> [{"start": float, "end": float, "text": str}, ...]
    start/end 单位为秒；text 为片段文本（已 strip）。

后端注册表（ASR_BACKEND 取值）：
    "whisper"    → WhisperBackend    faster-whisper / ctranslate2（原兜底引擎，保留）
    "funasr"     → FunASRBackend     阿里 FunASR Paraformer-zh（中文 SOTA，原生句子级真实时间轴）
    "fireredasr" → FireRedASRBackend 小红书 FireRedASR（中文最强，预留，尚未安装）
    "funasr_nano"→ FunASRNanoBackend  阿里 FunASR-Nano（中英混说 SOTA，GPU 优先；需 CUDA torch + 权重）

想加新引擎：在 _REGISTRY 注册一个 ASRBackend 子类即可。
"""
import logging
import os
import re
from abc import ABC, abstractmethod

from config import ASR_BACKEND


def _clip_duration(path: str) -> float:
    """读取音频时长（秒）；读不到返回 0.0。"""
    try:
        import soundfile as sf
        return float(sf.info(path).duration)
    except Exception:
        return 0.0


logger = logging.getLogger(__name__)


class ASRBackend(ABC):
    """所有 ASR 后端的抽象基类。"""

    #: 后端标识，与 ASR_BACKEND 配置对应，仅用于日志/调试
    name: str = "base"

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "zh") -> list[dict]:
        """
        把音频转写成带时间轴的片段。

        返回: [{"start": float, "end": float, "text": str}, ...]
        start/end 单位：秒。
        """
        raise NotImplementedError


class WhisperBackend(ASRBackend):
    """原 faster-whisper 引擎，封装既有 transcribe_with_whisper。"""

    name = "whisper"

    def transcribe(self, audio_path: str, language: str = "zh") -> list[dict]:
        from core.subtitle import transcribe_with_whisper
        return transcribe_with_whisper(audio_path, language)


class FunASRBackend(ASRBackend):
    """阿里 FunASR（Paraformer-zh）引擎。

    特性：中文 ASR SOTA（CER 同顶级）；**原生支持句子级真实时间轴**
    （generate 传 sentence_timestamp=True 返回每句的真实 start/end 毫秒）。
    依赖：PyTorch(CPU) + funasr。首次会下载模型（paraformer-zh 及 VAD/PUNC 配套）。

    为什么不用 SenseVoiceSmall：在 funasr 1.3.23 上，SenseVoiceSmall.generate 只返回
    整段文本（key/text 两字段），完全不吐时间轴；为了「带真实时间轴」字幕，选 Paraformer-zh。

    ⚠️ 本机父进程（经 WorkBuddy 启动的 Python）继承的环境块高达 ~340KB，远超 Windows
    进程环境块约 32K 的实际上限；若把该巨型环境块传给子进程，子进程 C 运行库
    （ucrtbase）初始化解析环境块时会缓冲区溢出 -> 段错误 0xC0000005（无法被 try 捕获、
    会杀进程）。故模型加载+推理放在独立子进程（_funasr_worker.py），且子进程只接收
    「精简合法的小环境块」；本后端自动重试，主进程永不被拖垮。
    """

    name = "funasr"

    #: 子进程偶发段错误时的重试上限
    MAX_RETRIES = 3

    #: 模型与设备（子类 FunASRNanoBackend 覆盖以切换引擎）
    MODEL = "paraformer"
    DEVICE = "cpu"

    @staticmethod
    def _map_language(language: str) -> str:
        """SenseVoice 支持 auto/zh/en/yue/ja/ko，把通用 zh/en 映射过去，其余交给 auto。"""
        if language.startswith("zh"):
            return "zh"
        if language.startswith("en"):
            return "en"
        return "auto"

    def transcribe(self, audio_path: str, language: str = "zh") -> list[dict]:
        import os
        import sys
        import json
        import subprocess

        worker = os.path.join(os.path.dirname(__file__), "_funasr_worker.py")
        lang = self._map_language(language)
        # 关键修复（2026-07-22 定位）：绝不把父进程的「巨型环境块」传给子进程。
        # 本机父进程（经 WorkBuddy 启动的 Python）继承的环境块高达 ~340KB，远超
        # Windows 进程环境块约 32K 的实际上限；CreateProcess 起子进程后，子进程的
        # C 运行库（ucrtbase）在初始化解析环境块时会缓冲区溢出 -> 段错误 0xC0000005，
        # 且无法被 try/except 捕获、直接杀进程（表现为子进程必崩 3221225477）。
        # 直接在本机 Git Bash 里跑 worker 之所以成功，正是因为那时环境块小且干净。
        # 故这里显式构造一个「精简且合法」的环境块：仅保留系统必需变量 + 一个精简
        # PATH（torch/lib + venv Scripts + System32/Windows）；worker 内部还会再前置
        # 一次 torch/lib 以绕开 add_dll_directory 的坏指针（WinError 206）。
        env = self._clean_env()
        cmd = f'"{sys.executable}" "{worker}" "{audio_path}" "{lang}" "{self.MODEL}" "{self.DEVICE}"'
        last_err = "unknown"
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=900,
                    env=env,
                )
            except subprocess.TimeoutExpired:
                last_err = f"子进程超时(attempt {attempt})"
                logger.warning(last_err)
                continue
            if proc.returncode == 0:
                try:
                    data = json.loads(proc.stdout.strip().splitlines()[-1])
                except Exception:
                    last_err = f"子进程输出无法解析(attempt {attempt})"
                    logger.warning(last_err)
                    continue
                if "error" in data:
                    last_err = f"子进程异常: {data['error']}"
                    logger.warning(last_err)
                    continue
                # 成功：用 Paraformer 返回的真实句子时间轴（不再做任何伪造铺排）
                return self._parse(data, audio_path)
            # 段错误(exit 139/3221225477) 或其它非零退出：重试
            last_err = f"子进程退出码 {proc.returncode}(attempt {attempt})"
            logger.warning(last_err)
        raise RuntimeError(f"FunASR 连续 {self.MAX_RETRIES} 次失败: {last_err}")

    #: 子进程仅保留的系统/运行必需环境变量。其余（BILIBILI_*/QDRANT_*/ALEMBIC_*
    #  WHISPER_* 及被 WorkBuddy 注入的超大 PATH 等）一律不传给子进程，避免环境块
    #  超限触发 ucrtbase 初始化段错误。
    _ENV_KEEP = (
        "SystemDrive", "SystemRoot", "windir", "ComSpec",
        "TEMP", "TMP", "TMPDIR",
        "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "USERNAME", "LOGNAME",
        "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER",
        "PATHEXT", "OS",
        "HF_ENDPOINT", "HF_TOKEN",   # 模型下载走国内镜像（可选，小且安全）
        "LANG", "LC_ALL", "PYTHONIOENCODING", "PYTHONUTF8",
    )

    @classmethod
    def _clean_env(cls) -> dict:
        """构造一个精简、合法的子进程环境块（核心修复：环境块绝不可过大）。"""
        env = {}
        for k in cls._ENV_KEEP:
            if k in os.environ:
                env[k] = os.environ[k]
        env["PATH"] = cls._minimal_path()
        return env

    @staticmethod
    def _minimal_path() -> str:
        """仅包含 torch 原生库 + venv 可执行目录 + Windows 系统目录的最小 PATH。

        不依赖父进程那串被注入的超大 PATH；torch/lib 前置保证原生 DLL 优先解析，
        venv Scripts 保证 funasr/torch 等可被发现，System32/Windows 提供 ucrtbase 等系统库。
        """
        import sys
        venv = os.path.dirname(os.path.dirname(sys.executable))
        torch_lib = os.path.join(venv, "Lib", "site-packages", "torch", "lib")
        if not os.path.isdir(torch_lib):
            # 兜底：torch 非标准路径安装时，import 一次定位（CPU 版 import 稳定）
            try:
                import torch as _t  # noqa: F401
                torch_lib = os.path.join(os.path.dirname(_t.__file__), "lib")
            except Exception:
                pass
        parts = [
            torch_lib,
            os.path.join(venv, "Scripts"),
            r"C:\Windows\System32",
            r"C:\Windows",
        ]
        return os.pathsep.join(parts)

    @staticmethod
    def _strip_sensevoice_tags(text: str) -> str:
        """去掉 SenseVoice 的内部标签，如 <|zh|><|neutral|><|bgm|><|woitn|>。"""
        return re.sub(r"<\|[^|]*\|>", "", text or "").strip()

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """按中英文句末标点切句（保留标点），过滤空串。"""
        parts = re.split(r"(?<=[。！？!?；;\n])", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _parse(data: dict, audio_path: str) -> list[dict]:
        """把 FunASR（Paraformer）的返回整理成统一片段格式。

        关键：使用 Paraformer sentence_timestamp 返回的真实句子时间轴（sentence_info），
        每句 start/end 是音频里的真实毫秒位置换算成秒，**绝不做「均匀铺」伪造时间轴**。
        若某次返回意外没有句子时间轴，则退回单段（start=end=0，明确标记无时间轴），
        不会用假时间轴糊弄。
        """
        sentences = data.get("sentences") or []
        if sentences:
            segs = [
                {"start": float(s["start"]), "end": float(s["end"]), "text": s["text"]}
                for s in sentences
                if str(s.get("text", "")).strip()
            ]
            if segs:
                return segs
        # 兜底（理论上 Paraformer 走不到）：无真实句子时间轴，退回单段且无时间轴
        raw_text = data.get("text", "") or ""
        clean = FunASRBackend._strip_sensevoice_tags(raw_text).strip()
        if clean:
            return [{"start": 0.0, "end": 0.0, "text": clean}]
        return []


class FireRedASRBackend(ASRBackend):
    """小红书 FireRedASR 引擎（中文 CER≈3%，业界最强）。

    预留位：本次仅做接口占位，未安装依赖、未实现。需要时用
    `pip install fireredasr` 并补全 transcribe 即可，无需改动调用方。
    """

    name = "fireredasr"

    def transcribe(self, audio_path: str, language: str = "zh") -> list[dict]:
        raise NotImplementedError(
            "FireRedASR 后端已预留但尚未实现：请先 `pip install fireredasr` "
            "并在 FireRedASRBackend.transcribe 中接入模型推理。"
        )


class FunASRNanoBackend(FunASRBackend):
    """阿里 FunASR-Nano-2512（中英混说 SOTA，GPU 优先）。

    为什么用它替代 Paraformer-zh：
    - Paraformer-zh 是纯中文模型，词表无英文，视频里的英文专名（Godot/Unity）
      会被音译成一串中文字（「够呆」），顺流到炼真/熔知变成噪声。
    - FunASR-Nano 原生中英混说，视频说 Godot 直接写 Godot，从根上消除音译噪声；
      中文 CER 也更低（约 8% vs Paraformer 同级），且带字符级时间戳（可聚合成句子级）。

    前置（需用户确认的安装动作，未就绪时本后端会优雅失败、不崩）：
    - 在 Nigredo venv 安装 CUDA 版 torch（当前是 CPU 版）。
    - 首次会自动下载 FunAudioLLM/Fun-ASR-Nano-2512 权重（约数百 MB）。

    DEVICE="auto"：worker 内自动选 cuda（可用时）否则 cpu。其余（子进程隔离、
    精简环境、重试、时间轴解析）全部复用 FunASRBackend，不重复造轮子。
    """

    name = "funasr_nano"
    MODEL = "funasr_nano"
    DEVICE = "auto"


# === 注册表 + 工厂 ===
_REGISTRY = {
    "whisper": WhisperBackend,
    "funasr": FunASRBackend,
    "funasr_nano": FunASRNanoBackend,
    "fireredasr": FireRedASRBackend,
}

_INSTANCES: dict = {}


def available_backends() -> list[str]:
    """返回当前已注册的所有后端名称（供 UI/配置页展示）。"""
    return list(_REGISTRY.keys())


def get_asr_backend(name: str = None) -> ASRBackend:
    """
    按名称（或配置 ASR_BACKEND）返回 ASR 后端单例。

    name 显式传入时优先（用于测试/强制指定），否则用配置。
    不同后端各自缓存单例，模型只加载一次。
    """
    key = (name or ASR_BACKEND).strip().lower()
    if key not in _REGISTRY:
        raise ValueError(
            f"未知 ASR_BACKEND={key!r}，可选: {available_backends()}"
        )
    if key not in _INSTANCES:
        _INSTANCES[key] = _REGISTRY[key]()
        logger.info(f"ASR 后端已初始化: {key}")
    return _INSTANCES[key]
