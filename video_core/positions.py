import random
from typing import Tuple
from .params import Position

def calc_position(is_text: bool, video_w:int, video_h:int, badge_w:int, badge_h:int, position:Position) -> Tuple[str,str,str]:
    positions = [
        "верх-лево","верх-центр","верх-право",
        "центр-лево","центр-центр","центр-право",
        "низ-лево","низ-центр","низ-право"
    ]
    pos = random.choice(positions) if position=="Случайная" else position
    coords = {
        "верх-лево": (0.05*video_w, 0.05*video_h),
        "верх-центр": ((video_w-badge_w)/2, 0.05*video_h),
        "верх-право": (max(0, video_w-badge_w-0.05*video_w), 0.05*video_h),
        "центр-лево": (0.05*video_w, (video_h-badge_h)/2),
        "центр-центр": ((video_w-badge_w)/2, (video_h-badge_h)/2),
        "центр-право": (max(0, video_w-badge_w-0.05*video_w), (video_h-badge_h)/2),
        "низ-лево": (0.05*video_w, max(0, video_h-badge_h-0.05*video_h)),
        "низ-центр": ((video_w-badge_w)/2, max(0, video_h-badge_h-0.05*video_h)),
        "низ-право": (max(0, video_w-badge_w-0.05*video_w), max(0, video_h-badge_h-0.05*video_h)),
    }
    x,y = coords[pos]
    x = max(0, min(x, video_w-badge_w))
    y = max(0, min(y, video_h-badge_h))

    if is_text and True:
        dirs = [("t*20","0"),("-t*20","0"),("0","t*20"),("0","-t*20"),("t*20","t*20"),("-t*20","t*20"),("t*20","-t*20"),("-t*20","-t*20")]
        mx,my = random.choice(dirs)
        xs = f"{int(x)}+{mx}" if mx!="0" else str(int(x))
        ys = f"{int(y)}+{my}" if my!="0" else str(int(y))
        xs = xs.replace("+-","-"); ys = ys.replace("+-","-")
    else:
        xs,ys = str(int(x)), str(int(y))
    return xs,ys,pos


