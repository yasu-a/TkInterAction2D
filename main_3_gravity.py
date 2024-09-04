import ctypes
import time
import tkinter
from dataclasses import dataclass


# ------------------------------------------
#  物体のデータ型の定義と関連する処理
# ------------------------------------------


# 物体を定義するデータ型Solid
# このSolidクラスを使って壁・床・キャラクターの物理演算・描画のためのデータ管理をすべて実現する
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


# ちなみに変数の定義の後のコロン「:」は「この変数にはこの型の値が入るよ」というヒントを書くPythonの機能
# プログラムの動作上で特に意味はない、わかりやすいだけ
# strは文字列・intは整数・floatは小数・自分で定義した型も書くことができてContactはさっき上で定義したデータ型


# ------------------------------------------
#  ステージ
# ------------------------------------------


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
    "____-_______________",
    "___-________________",
    "__-_______o----o____",
    "_-__________________",
    "______o_____________",
    "ooo-----oooo-----ooo",  # 一番下はプレイヤーがスタートする床oが一つ以上必要
]

# ------------------------------------------
#  すべての物体を記憶するリストと関連する処理
# ------------------------------------------

# すべての物体を記憶するリスト
objects: list[Solid] = []  # Solid型の値のリスト


# リストの中からタグで物体を検索する
def get_object_by_tag(tag):
    for obj in objects:
        if obj.tag == tag:
            return obj
    raise ValueError(f"タグ\"{tag}\"を持つ物体が見つかりません")


# リストの中から固定された物体（fixed=True）を繰り返す
def iter_fixed():
    for obj in objects:
        if obj.fixed:
            yield obj


# リストの中から固定されていない物体（fixed=False）を繰り返す
def iter_movable():
    for obj in objects:
        if not obj.fixed:
            yield obj


# ------------------------------------------
#  物体の初期化
# ------------------------------------------

BLOCK_SIZE = 30  # 床ブロックの大きさ（ピクセル）

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
# |       j列目
# |
# |  STAGE
# |
# | i行目
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

# ------------------------------------------
#  描画処理
# ------------------------------------------

FPS = 60  # 描画の最大フレームレート


# メイン（描画処理）
def main_render():
    # 描画にかかった時間を知るために描画開始時刻を記録する
    t_start = time.time()

    # すべて消す
    cvs.delete("all")

    # プレイヤーの位置に応じて画面を動かすときに使う座標データの生成
    player = get_object_by_tag(tag="player")  # プレイヤーのタグを持つ物体を取得
    screen_x = player.x - 300  # 座標データを生成（下で使う）
    screen_y = player.y - 300  # 座標データを生成（下で使う）

    # すべての物体を位置x,y・サイズw,h・色colorに基づいて描画
    for obj in objects:
        cvs.create_rectangle(
            obj.x - screen_x,
            obj.y - screen_y,
            obj.x + obj.w - screen_x,
            obj.y + obj.h - screen_y,
            outline=obj.color,
            fill="",
        )

    # 画面の上にデバッグ情報を表示
    player = get_object_by_tag(tag="player")  # プレイヤーのタグを持つ物体を取得
    cvs.create_text(
        10,
        0,
        text=", ".join([
            f"v=({player.vx:+7.2f}, {player.vy:+7.2f})",
            f"x=({player.x:+6.2f}, {player.y:+6.2f})",
        ]),
        fill="red",
        anchor="nw",  # テキストの配置位置は左上の角（North West）を基準にする
        font=("Consolas", 11, "bold"),  # きれいな等幅フォントで有名なConsolas・フォントサイズ11・太字
    )

    # 描画にかかった時間を知るために描画終了時刻を記録する
    t_end = time.time()

    # イベントループにこの処理を予約して繰り返す
    t_delta = t_end - t_start  # 処理にかかった時間（秒）
    t_rest = 1 // FPS - t_delta  # 1 / FPS 秒間隔で描画するために次の描画を待つ時間（秒）
    root.after(max(1, int(t_rest * 1000)), main_render)  # root.afterでt_rest秒後に描画を予約
    # max(1, ...): 処理が重くてt_restがほぼ0やマイナスの時でも最低1ミリ秒は待つ


# ------------------------------------------
#  物理演算
# ------------------------------------------

G = 900  # 重力加速度（重力の強さ）

t_physics = time.time()  # 物理演算で使うタイマー変数


# メイン（物理演算）
def main_physics():
    global t_physics

    # イベントループにこの処理を予約して繰り返す
    root.after(20, main_physics)

    # t_physicsを使って現在のループと前のループの時刻差t_deltaを出す
    t_now = time.time()
    t_delta = t_now - t_physics
    t_physics = t_now

    # 固定されていない物体に対して重力を与える
    for obj in iter_movable():  # すべての固定されていない物体に対して
        obj.vy += G * t_delta

    # 位置計算
    for obj in iter_movable():  # すべての固定されていない物体に対して
        # 運動の法則 x = vt を適用
        obj.x += obj.vx * t_delta
        obj.y += obj.vy * t_delta


# ------------------------------------------
#  キー入力処理
# ------------------------------------------

# メイン（キー入力処理）
def main_key():
    def is_pressed(key):
        return ctypes.windll.user32.GetAsyncKeyState(key) & 0x8000

    if is_pressed(65):  # A
        get_object_by_tag(tag="player").x -= 5  # 左方向への移動を予定する
    if is_pressed(68):  # D
        get_object_by_tag(tag="player").x += 5  # 右方向への移動を予定する

    # イベントループにこの処理を予約して繰り返す
    root.after(50, main_key)


# ------------------------------------------
#  起動処理
# ------------------------------------------

root = tkinter.Tk()
cvs = tkinter.Canvas(root, bg="white", height=650, width=800)
cvs.pack()
main_render()  # 描画処理開始
main_physics()  # 物理演算開始
main_key()  # キー処理開始
root.mainloop()
