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

    # イベントループにこの処理を予約して繰り返す
    root.after(33, main_render)


# メイン（キー処理）
def main_key():
    def is_pressed(key):
        return ctypes.windll.user32.GetAsyncKeyState(key) & 0x8000

    if is_pressed(65):  # A
        get_object_by_tag(tag="player").x -= 10
    if is_pressed(68):  # D
        get_object_by_tag(tag="player").x += 10
    if is_pressed(27):  # Escape
        root.destroy()  # ゲーム終了

    # イベントループにこの処理を予約して繰り返す
    root.after(50, main_key)


root = tkinter.Tk()
cvs = tkinter.Canvas(root, bg="white", height=650, width=800)
cvs.pack()
main_render()  # 描画処理開始
main_key()  # キー処理開始
root.mainloop()
