import copy
import time
import tkinter
import ctypes
from dataclasses import dataclass, field
import random


# ---------------------
# 物体の型Solidの定義
# ---------------------

# 物体を定義するSolidクラス
# このSolidクラスを使って壁・床・キャラクターの物理演算を全部実現できる
@dataclass
class Solid:
    tag: str  # 物体につけるタグ（物体の検索に使う）
    x: float  # x座標
    y: float  # y座標
    w: float  # 幅
    h: float  # 高さ
    fixed: bool  # 動かない物体ならTrue
    color: str  # 色（現時点ではすべての物体は単色の四角形。画像を格納するフィールドを作れば画像も表示できるけどそれは後で考えようかな）
    vx: float = 0.0  # x速度
    vy: float = 0.0  # y速度
    m: float = 1.0  # 質量
    fx: float = 0.0  # x方向に加える力
    fy: float = 0.0  # y方向に加える力
    friction_x: float = 0.3  # 水平方向に擦れるときの摩擦 0が最大 1が摩擦なし
    friction_y: float = 0.0  # 垂直方向に擦れるときの摩擦
    obstacle_on_surface: list["None | Solid"] = field(
        default_factory=lambda: [None, None, None, None],
    )  # 物体中心から4方向の面が別の物体に接しているか 接して入ればその物体・接していなければNone
    #    下の定数を使う(X_POS, X_NEG, Y_POS, Y_NEG)
    #    obstacle_on_surface[X_POS]はx軸方向正の方向の接触物体を示す


X_POS, X_NEG, Y_POS, Y_NEG = range(4)

# ステージ
# 床：o 橋：- 空気：_
# （橋は下から貫通できる床）
STAGE = [
    "_________________o-o",
    "____________________",
    "____________o_______",
    "____________o_______",
    "________________o___",
    "________________o___",
    "____________________",
    "___________________o",  # カンマ「,」忘れに注意！
    "__________o--_---o_o",
    "___________________o",
    "____________________",
    "____________o----o__",
    "____________________",
    "____________________",
    "__________o----o____",
    "____________________",
    "____________________",
    "ooo-----oooo-----ooo",  # 一番下はプレイヤーがスタートする床oが一つ以上必要
]
# ランダム生成
# STAGE = [
#     "".join(random.choices("_oo--", k=10))
#     if i % 3 == 0 else "_" * 10
#     for i in reversed(range(10))
# ]

# -------------------------------------
# すべての物体を記憶するリストと関係する処理
# -------------------------------------

# すべての物体を記憶するリスト
objects = []


# タグで物体を検索する
def get_object_by_tag(tag):
    for obj in objects:
        if obj.tag == tag:
            return obj
    raise ValueError(f"タグ\"{tag}\"を持つ物体が見つかりません")


# 固定された物体を繰り返す
def iter_fixed():
    for obj in objects:
        if obj.fixed:
            yield obj


# 固定されていない物体を繰り返す
def iter_movable():
    for obj in objects:
        if not obj.fixed:
            yield obj


# 2つの物体が衝突しているかどうかを返す
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


# -------------------------------------
# 物体の初期化
# -------------------------------------

BLOCK_SIZE = 30  # 床ブロックの大きさ

# プレイヤーを作って追加
objects.append(
    Solid(
        tag="player",  # タグはplayer
        x=STAGE[-1].find("o") * BLOCK_SIZE + BLOCK_SIZE / 2,  # スタート時のx座標はステージの一番下の床のところ
        y=(len(STAGE) - 3) * BLOCK_SIZE + BLOCK_SIZE / 2,  # スタート時のy座標はステージの一番下の床の上
        w=BLOCK_SIZE * 0.3,
        h=BLOCK_SIZE * 0.7,
        fixed=False,  # プレイヤーは動く（固定オブジェクトではない）
        color="red",  # 赤色で表示
    )
)

# すべての床・橋をそれぞれ作って追加
# +--------->
# |       j
# |
# |  STAGE
# |
# | i
# v
for i in range(len(STAGE)):  # STAGEのi行目
    for j in range(len(STAGE[i])):  # STAGEのj列目
        if STAGE[i][j] == "o":  # 床
            objects.append(
                Solid(
                    tag=f"block",  # タグはblock
                    x=j * BLOCK_SIZE,
                    y=i * BLOCK_SIZE,
                    w=BLOCK_SIZE,
                    h=BLOCK_SIZE,
                    fixed=True,  # 床は固定オブジェクト
                    color="black",
                )
            )
        if STAGE[i][j] == "-":  # 橋
            objects.append(
                Solid(
                    tag=f"bridge",  # タグはbridge
                    x=j * BLOCK_SIZE,
                    y=i * BLOCK_SIZE,
                    w=BLOCK_SIZE,
                    h=BLOCK_SIZE * 0.1,
                    fixed=True,  # 橋は固定オブジェクト
                    color="black",
                )
            )


# -------------------------------------
# 描画処理
# -------------------------------------

# メイン（描画処理）
def main_render():
    cvs.delete("all")

    # プレイヤーの位置に応じて画面を動かすときに使う座標データの生成
    player = get_object_by_tag(tag="player")  # プレイヤーを取得
    screen_x = player.x - 300  # 座標データを生成（下で使う）
    screen_y = player.y - 300  # 座標データを生成（下で使う）

    # すべての物体を位置x,yと幅wと高さhと色colorに基づいて描画
    for obj in objects:
        cvs.create_rectangle(
            obj.x - screen_x,
            obj.y - screen_y,
            obj.x + obj.w - screen_x,
            obj.y + obj.h - screen_y,
            fill=obj.color,
        )

    # 画面の上にデバッグ情報を表示
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

    # イベントループにこの処理を予約して繰り返す
    root.after(33, main_render)


# -------------------------------------
# ゲームの処理
# -------------------------------------

player_jump = False  # プレイヤーのジャンプが予定されているかどうかを表すフラグ
player_move = 0  # プレイヤーの移動が予定されているかどうかを表し、その値は移動量
G = 12  # 重力加速度（重力の強さ）
PLAYER_MOVE_POWER = 200  # プレイヤーが移動する勢い
PLAYER_JUMP_POWER = 400  # プレイヤーがジャンプする勢い
COLLIDE_EPSILON = 1  # 物理演算で使う定数（物体をちょっと動かして衝突を見るときにどのくらい動かすか）
COLLIDE_SOLVE_FACTOR = 0.002  # 物理演算で使う定数（めり込んだ衝突を解消するためにどのくらい動きを元に戻していくか）


# 物体obj_movableから軸axis（"x"か"y"）に沿ってsign（-1か+1）の方向を見たときにほかの物体に接触していればその物体を返す
# 接触していなければ何も返さない（Noneを返す）
def find_obstacle(obj_movable, axis, sign):
    # 物体obj_movableのコピーを作る
    obj_movable_copy = copy.deepcopy(obj_movable)
    # obj_movableを軸axisに沿ってsignの方向にちょっと動かしてみる
    setattr(
        obj_movable_copy,
        f"{axis}",
        getattr(obj_movable_copy, f"{axis}") + sign * COLLIDE_EPSILON,
    )
    # 何かにぶつかったらぶつかった物体を返す
    for obj_fixed in iter_fixed():
        # 橋は物体が下から突っ込んだとき（移動方向が上向きのとき）は貫通できるので衝突に含めない
        if obj_fixed.tag == "bridge" and obj_movable.vy < 0:
            continue
        # 今までぶつかっていなかったのにちょっと動かしてみたらぶつかったときは衝突と判断して衝突相手の物体を返す
        if not collide(obj_movable, obj_fixed) and collide(obj_movable_copy, obj_fixed):
            return obj_fixed


t_physics_pre = time.time()  # 物理演算で使うタイマー変数


# メイン（物理演算）
def main_physics():
    global player_jump, player_move, t_physics_pre

    # t_physics_preを使って現在のループと前のループの時刻差を出す
    t_physics_cur = time.time()
    t_delta = t_physics_cur - t_physics_pre
    t_physics_pre = t_physics_cur

    # 接触判定を計算する
    for obj in iter_movable():  # すべての固定されていない物体に対して
        obj.obstacle_on_surface[X_POS] = find_obstacle(obj, "x", +1)
        obj.obstacle_on_surface[X_NEG] = find_obstacle(obj, "x", -1)
        obj.obstacle_on_surface[Y_POS] = find_obstacle(obj, "y", +1)
        obj.obstacle_on_surface[Y_NEG] = find_obstacle(obj, "y", -1)

    # 床についていなかったら重力を与える
    for obj in iter_movable():  # すべての固定されていない物体に対して
        if not obj.obstacle_on_surface[Y_POS]:
            obj.fy += obj.m * G  # ニュートンの運動方程式 F=ma

    # プレイヤーアクションに従って移動力を与える
    player = get_object_by_tag(tag="player")
    if player.obstacle_on_surface[Y_POS]:  # 地面についているとき
        if player_jump:  # ジャンプが予定されていたら
            player.fy -= PLAYER_JUMP_POWER
        if player_move != 0:  # 移動が予定されていたら
            player.fx += PLAYER_MOVE_POWER * player_move
    else:  # 空中にいるとき
        if player_move != 0:  # 移動が予定されていたら
            player.fx += PLAYER_MOVE_POWER * player_move / abs(player_move) * 0.02  # 空中でもちょっと動ける
    player_jump = False  # ジャンプの予定をクリア
    player_move = 0  # 移動の予定をクリア

    # 速度計算
    for obj_movable in iter_movable():  # すべての固定されていない物体に対して
        # ニュートンの運動方程式 F = ma から a を逆算
        ax = obj_movable.fx / obj_movable.m
        ay = obj_movable.fy / obj_movable.m
        obj_movable.fx = obj_movable.fy = 0  # 撃力をクリア

        # 速度を加速度にしたがって加速
        obj_movable.vx += ax
        obj_movable.vy += ay

        # ただし衝突する方向に進もうとしているときは速度をクリア
        if obj_movable.obstacle_on_surface[X_POS] and obj_movable.vx > 0:
            obj_movable.vx = 0
        if obj_movable.obstacle_on_surface[X_NEG] and obj_movable.vx < 0:
            obj_movable.vx = 0
        if obj_movable.obstacle_on_surface[Y_POS] and obj_movable.vy > 0:
            obj_movable.vy = 0
        if obj_movable.obstacle_on_surface[Y_NEG] and obj_movable.vy < 0:
            obj_movable.vy = 0

    # 摩擦
    for obj_movable in iter_movable():  # すべての固定されていない物体に対して
        # X軸方向について接触があれば摩擦に応じて減速
        obstacle = obj_movable.obstacle_on_surface[Y_POS] or obj_movable.obstacle_on_surface[Y_NEG]
        if obstacle:
            obj_movable.vx *= 1 - obstacle.friction_x
        # Y軸方向について接触があれば摩擦に応じて減速
        obstacle = obj_movable.obstacle_on_surface[X_POS] or obj_movable.obstacle_on_surface[X_NEG]
        if obstacle:
            obj_movable.vy *= 1 - obstacle.friction_y

    # 位置計算
    for obj_movable in iter_movable():  # すべての固定されていない物体に対して
        # 運動の法則 x = vt
        obj_movable.x += obj_movable.vx * t_delta
        obj_movable.y += obj_movable.vy * t_delta

    # めり込み解決
    #  今までの処理は衝突を考えていないので、固定されていない物体が進みすぎて固定物体にめり込んでいる可能性がある
    #  ここでめり込んだ物体を衝突しなかったことになるまで少しずつ前に戻す
    for obj_movable in iter_movable():  # すべての固定されていない物体に対して
        for obj_fixed in iter_fixed():  # すべての固定されている物体に対して
            if obj_fixed.tag == "bridge":  # 橋は下から貫通できるからめり込んでもいい
                if obj_movable.vy <= 0:
                    continue
            while collide(obj_movable, obj_fixed):  # 衝突している間
                # 物体を少し戻す
                obj_movable.x -= obj_movable.vx * t_delta * COLLIDE_SOLVE_FACTOR
                obj_movable.y -= obj_movable.vy * t_delta * COLLIDE_SOLVE_FACTOR

    # イベントループにこの処理を予約して繰り返す
    root.after(10, main_physics)


# メイン（キー処理）
def main_key():
    global player_jump, player_move

    def is_pressed(key):
        return ctypes.windll.user32.GetAsyncKeyState(key) & 0x8000

    if is_pressed(65):  # A
        player_move = -1  # 左方向への移動を予定する
    if is_pressed(68):  # D
        player_move = +1  # 右方向への移動を予定する
    if is_pressed(32):  # Space
        player_jump = True  # ジャンプを予定する
    if is_pressed(16):  # Shift
        player_move *= 1.8  # 予定された移動を大きくする（走る）
    if is_pressed(27):  # Escape
        root.destroy()  # ゲーム終了

    # イベントループにこの処理を予約して繰り返す
    root.after(50, main_key)


root = tkinter.Tk()
cvs = tkinter.Canvas(root, bg="white", height=650, width=800)
cvs.pack()
main_render()  # 描画処理開始
main_physics()  # 物理演算開始
main_key()  # キー処理開始
root.mainloop()
