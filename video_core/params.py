from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Literal, Dict, Any

FormatType = Literal["1:1", "9:16", "16:9"]
BadgeBehavior = Literal["Исчезновение", "Луп до конца", "Обрезать по короткому"]
Position = Literal[
    "Случайная","верх-лево","верх-центр","верх-право",
    "центр-лево","центр-центр","центр-право",
    "низ-лево","низ-центр","низ-право"
]

@dataclass
class TextParams:
    enabled: bool = False
    content: str = ""
    fontfile: Optional[Path] = None
    auto_font: bool = True
    level: Literal["Подпись","Заголовок"] = "Подпись"
    fontsize: int = 24
    position: Position = "Случайная"

@dataclass
class BadgeParams:
    enabled: bool = False
    path: Optional[Path] = None
    random_scale: bool = False
    scale_percent: int = 30
    position: Position = "Случайная"
    behavior: BadgeBehavior = "Исчезновение"

@dataclass
class EffectsParams:
    cut: bool = False
    contrast: bool = True
    color_shift: bool = False
    noise: bool = False
    brightness_sat: bool = True
    crop_edges: bool = False
    geom: bool = True
    time_mod: bool = True
    overlays: bool = True
    codec_random: bool = True
    profile_strong: bool = False
    safe_mode: bool = True
    color_mod: bool = False
    hidden_pattern: bool = False

@dataclass
class JobParams:
    input_path: Path
    output_path: Path
    copies: int = 1
    fmt: FormatType = "9:16"
    text: TextParams = field(default_factory=TextParams)
    badge: BadgeParams = field(default_factory=BadgeParams)
    effects: EffectsParams = field(default_factory=EffectsParams)
    fixed_duration_sec: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


