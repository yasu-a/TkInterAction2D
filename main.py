import copy
import time
import tkinter
import ctypes
from dataclasses import dataclass, field
import random


@dataclass
class Solid:
    tag: str
    x: float
    y: float
    w: float
    h: float
    fixed: bool
    color: str
    vx: float = 0.0
    vy: float = 0.0
    m: float = 1.0
    fx: float = 0.0
    fy: float = 0.0
    friction_x: float = 0.3
    friction_y: float = 0.0
    obstacle_on_surface: list["None | Solid"] = field(
        default_factory=lambda: [None, None, None, None])


X_POS, X_NEG, Y_POS, Y_NEG = range(4)

STAGE = [
    "".join(random.choices("_oo--", k=100)) if i % 3 == 0 else "_" * 100
    for i in reversed(range(100))
]

objects = []


def get_object_by_tag(tag):
    for obj in objects:
        if obj.tag == tag:
            return obj
    raise ValueError(f"Object with tag {tag} not found")


def iter_fixed():
    for obj in objects:
        if obj.fixed:
            yield obj


def iter_movable():
    for obj in objects:
        if not obj.fixed:
            yield obj


def collide(obj_1: Solid, obj_2: Solid):
    x1 = obj_1.x + obj_1.w / 2
    y1 = obj_1.y + obj_1.h / 2
    w1 = obj_1.w
    h1 = obj_1.h
    x2 = obj_2.x + obj_2.w / 2
    y2 = obj_2.y + obj_2.h / 2
    w2 = obj_2.w
    h2 = obj_2.h
    return abs(x1 - x2) < (w1 + w2) / 2 and abs(y1 - y2) < (h1 + h2) / 2


BLOCK_SIZE = 30

objects.append(
    Solid(
        tag="player",
        x=STAGE[-1].find("o") * BLOCK_SIZE + BLOCK_SIZE / 2,
        y=(len(STAGE) - 3) * BLOCK_SIZE + BLOCK_SIZE / 2,
        w=BLOCK_SIZE * 0.4,
        h=BLOCK_SIZE * 0.8,
        fixed=False,
        color="red",
    )
)

for i in range(len(STAGE)):
    for j in range(len(STAGE[i])):
        if STAGE[i][j] == "o":  # wall
            objects.append(
                Solid(
                    tag=f"block",
                    x=j * BLOCK_SIZE,
                    y=i * BLOCK_SIZE,
                    w=BLOCK_SIZE,
                    h=BLOCK_SIZE,
                    fixed=True,
                    color="black",
                )
            )
        if STAGE[i][j] == "-":  # bridge
            objects.append(
                Solid(
                    tag=f"bridge",
                    x=j * BLOCK_SIZE,
                    y=i * BLOCK_SIZE,
                    w=BLOCK_SIZE,
                    h=BLOCK_SIZE * 0.1,
                    fixed=True,
                    color="black",
                )
            )


def main_render():
    cvs.delete("all")

    player = get_object_by_tag(tag="player")
    screen_x = player.x - 300
    screen_y = player.y - 300

    for obj in objects:
        cvs.create_rectangle(
            obj.x - screen_x,
            obj.y - screen_y,
            obj.x + obj.w - screen_x,
            obj.y + obj.h - screen_y,
            fill=obj.color,
        )

    # draw player's geometry on canvas
    player = get_object_by_tag(tag="player")
    obs = list(map(int, map(bool, player.obstacle_on_surface)))
    cvs.create_text(
        10,
        0,
        text=f"v=({player.vx:5.2f}, {player.vy:5.2f}), x=({player.x:6.2f}, {player.y:6.2f}), jump={player_jump}, move={player_move}, surface={obs}",
        fill="red",
        anchor="nw",
        font=("Consolas", 12, "bold"),
    )

    root.after(33, main_render)


player_jump = False
player_move = 0
G = 12
COLLIDE_EPSILON = 1
PLAYER_MOVE_POWER = 200
COLLIDE_SOLVE_FACTOR = 0.002
PLAYER_JUMP_POWER = 400


def find_obstacle(obj_movable, axis, sign):
    obj_movable_copy = copy.deepcopy(obj_movable)
    setattr(
        obj_movable_copy,
        f"{axis}",
        getattr(obj_movable_copy, f"{axis}") + sign * COLLIDE_EPSILON,
    )
    for obj_fixed in iter_fixed():
        if obj_fixed.tag == "bridge" and obj_movable.vy < 0:
            continue
        if not collide(obj_movable, obj_fixed) and collide(obj_movable_copy, obj_fixed):
            return obj_fixed


t_physics_pre = time.time()


def main_physics():
    global player_jump, player_move, t_physics_pre

    t_physics_cur = time.time()
    t_delta = t_physics_cur - t_physics_pre
    t_physics_pre = t_physics_cur

    # 接触判定
    for obj in iter_movable():
        obj.obstacle_on_surface[X_POS] = find_obstacle(obj, "x", +1)
        obj.obstacle_on_surface[X_NEG] = find_obstacle(obj, "x", -1)
        obj.obstacle_on_surface[Y_POS] = find_obstacle(obj, "y", +1)
        obj.obstacle_on_surface[Y_NEG] = find_obstacle(obj, "y", -1)

    # 床についていなかったら重力を与える
    for obj in iter_movable():
        if not obj.obstacle_on_surface[Y_POS]:
            obj.fy += obj.m * G

    # プレイヤーアクションに従って移動力を与える
    player = get_object_by_tag(tag="player")
    if player.obstacle_on_surface[Y_POS]:
        if player_jump:
            player.fy -= PLAYER_JUMP_POWER
        if player_move != 0:
            player.fx += PLAYER_MOVE_POWER * player_move
    else:
        if player_move != 0:
            player.fx += PLAYER_MOVE_POWER * player_move / abs(player_move) * 0.02  # 空中でもちょっと動ける
    player_jump = False
    player_move = 0

    # 速度計算
    for obj_movable in iter_movable():
        # ニュートンの運動方程式
        ax = obj_movable.fx / obj_movable.m
        ay = obj_movable.fy / obj_movable.m
        obj_movable.fx = obj_movable.fy = 0  # 撃力としてすべて加速度に変換

        obj_movable.vx += ax
        obj_movable.vy += ay

        if obj_movable.obstacle_on_surface[X_POS] and obj_movable.vx > 0:
            obj_movable.vx = 0
        if obj_movable.obstacle_on_surface[X_NEG] and obj_movable.vx < 0:
            obj_movable.vx = 0
        if obj_movable.obstacle_on_surface[Y_POS] and obj_movable.vy > 0:
            obj_movable.vy = 0
        if obj_movable.obstacle_on_surface[Y_NEG] and obj_movable.vy < 0:
            obj_movable.vy = 0

    # 摩擦
    for obj_movable in iter_movable():
        obstacle = obj_movable.obstacle_on_surface[X_POS] or obj_movable.obstacle_on_surface[X_NEG]
        if obstacle:
            obj_movable.vy *= 1 - obstacle.friction_y
        obstacle = obj_movable.obstacle_on_surface[Y_POS] or obj_movable.obstacle_on_surface[Y_NEG]
        if obstacle:
            obj_movable.vx *= 1 - obstacle.friction_x

    # 位置計算
    for obj_movable in iter_movable():
        obj_movable.x += obj_movable.vx * t_delta
        obj_movable.y += obj_movable.vy * t_delta

    # めり込み解決
    for obj_movable in iter_movable():
        for obj_fixed in iter_fixed():
            if obj_fixed.tag == "bridge":
                if obj_movable.vy <= 0:
                    continue
            while collide(obj_movable, obj_fixed):
                obj_movable.x -= obj_movable.vx * t_delta * COLLIDE_SOLVE_FACTOR
                obj_movable.y -= obj_movable.vy * t_delta * COLLIDE_SOLVE_FACTOR

    root.after(5, main_physics)


def main_key():
    global player_jump, player_move

    def is_pressed(key):
        return ctypes.windll.user32.GetAsyncKeyState(key) & 0x8000

    if is_pressed(65):  # A
        player_move = -1
    if is_pressed(68):  # D
        player_move = +1
    if is_pressed(32):  # Space
        player_jump = True
    if is_pressed(16):  # Shift
        player_move *= 1.8
    if is_pressed(27):  # Escape
        root.destroy()

    root.after(50, main_key)


root = tkinter.Tk()
cvs = tkinter.Canvas(root, bg="white", height=650, width=800)
cvs.pack()
main_render()
main_physics()
main_key()
root.mainloop()
