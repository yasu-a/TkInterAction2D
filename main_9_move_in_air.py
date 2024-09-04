import copy
import ctypes
import time
import tkinter
from dataclasses import dataclass, field


# ------------------------------------------
#  物体のデータ型の定義と関連する処理
# ------------------------------------------

# ある物体から4方向の面がほかの物体に接触しているかどうかを管理するデータ型Contact
@dataclass
class Contact:
    x_pos: "Solid | None" = None  # その物体から見てx軸プラス方向に接触している物体（接触している物体が無いならNone・初期値はNone）
    x_neg: "Solid | None" = None  # x軸マイナス方向
    y_pos: "Solid | None" = None  # y軸プラス方向
    y_neg: "Solid | None" = None  # y軸マイナス方向


# ちなみにposはポジティブ（プラス）のこと・negはネガティブ（マイナス）のこと

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
    contact: Contact = field(default_factory=Contact)  # 接触物体の記録用（初期値は毎回`Contact()`を実行して生成する）


# ちなみに変数の定義の後のコロン「:」は「この変数にはこの型の値が入るよ」というヒントを書くPythonの機能
# プログラムの動作上で特に意味はない、わかりやすいだけ
# strは文字列・intは整数・floatは小数・自分で定義した型も書くことができてContactはさっき上で定義したデータ型


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
    return abs(x1 - x2) <= (w1 + w2) / 2 and abs(y1 - y2) <= (h1 + h2) / 2


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
    contact = "".join([  # 接触を文字列で表示するために接触方向を矢印で表した文字列を作る
        "<" if player.contact.x_neg else "-",
        "^" if player.contact.y_neg else "-",
        "v" if player.contact.y_pos else "-",
        ">" if player.contact.x_pos else "-",
    ])
    cvs.create_text(
        10,
        0,
        text=", ".join([
            f"v=({player.vx:+7.2f}, {player.vy:+7.2f})",
            f"x=({player.x:+6.2f}, {player.y:+6.2f})",
            f"jump={jump_flag}",
            f"move={move_flag}",
            f"contact={contact}",
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

move_flag = 0  # プレイヤーの移動が予定されているかどうかを表すフラグ、ただしその値は予定する移動の勢いを表す数値
jump_flag = False  # プレイヤーのジャンプが予定されているかどうかを表すフラグ
G = 900  # 重力加速度（重力の強さ）
MOVE_VEL = 100  # プレイヤーが移動する速さ
JUMP_VEL = 450  # プレイヤーがジャンプする瞬間に加える速さ
MOVE_VEL_FACTOR_AIR = 0.3  # プレイヤーが空中で移動する速さは地上の何倍かを表す
COLLIDE_EPS = 1  # 物理演算で使う定数（物体をちょっと動かして衝突を見るときにどのくらい動かすか）
COLLIDE_SOLVE_FACTOR = 0.01  # 物理演算で使う定数（めり込んだ衝突を解消するためにどのくらい動きを元に戻していくか）


# 物体obj_movableから軸axis（"x"か"y"）に沿ってsign（-1か+1）の方向を見たときにほかの物体に接触していればその物体を返す
# 物体がほかの物体の面に接しsているかを調べる
# 物体objから(dx,dy)方向に見てほかの物体に接触していればその物体を返す
# 接触していなければ何も返さない（Noneを返す）
# dxとdyは-1,0,+1のどれかを指定する
def find_obstacle(obj, dx, dy):
    # 物体obj_movableのコピーを作る
    obj_copy = copy.copy(obj)
    # obj_movableを(dx, dy)方向にちょっと（COLLIDE_EPSだけ）動かしてみる
    obj_copy.x += dx * COLLIDE_EPS
    obj_copy.y += dy * COLLIDE_EPS
    # すべての固定された物体に対して
    for obj_fixed in iter_fixed():
        # 今までぶつかっていなかったのにちょっと動かしてみたらぶつかったときは衝突と判断して衝突相手の物体を返す
        if not collide(obj, obj_fixed) and collide(obj_copy, obj_fixed):
            return obj_fixed


t_physics = time.time()  # 物理演算で使うタイマー変数


# メイン（物理演算）
def main_physics():
    global jump_flag, move_flag, t_physics

    # t_physicsを使って現在のループと前のループの時刻差t_deltaを出す
    t_now = time.time()
    t_delta = t_now - t_physics
    t_physics = t_now

    # 接触判定を計算する
    for obj in iter_movable():  # すべての固定されていない物体に対して
        obj.contact.x_pos = find_obstacle(obj, +1, 0)
        obj.contact.x_neg = find_obstacle(obj, -1, 0)
        obj.contact.y_pos = find_obstacle(obj, 0, +1)
        obj.contact.y_neg = find_obstacle(obj, 0, -1)

    # 床についていなかったら重力を与える
    for obj in iter_movable():  # すべての固定されていない物体に対して
        if not obj.contact.y_pos:
            obj.vy += G * t_delta

    # プレイヤーアクションに従って速度を与える
    player = get_object_by_tag(tag="player")  # プレイヤーのタグがついた物体を取得
    if player.contact.y_pos:  # 地面についていたら
        if jump_flag:  # ジャンプが予定されていたら
            player.vy -= JUMP_VEL
        if move_flag != 0:  # 移動が予定されていたら
            vel = MOVE_VEL * move_flag
            if player.vx * vel <= 0 or abs(player.vx) < abs(vel):  # 移動方向が変わるときもしくは移動速度に達していないとき
                player.vx = vel
        else:  # 移動が予定されていなかったら
            player.vx *= 0.1  # 減速する
    else:  # 空中にいたら
        if move_flag != 0:  # 移動が予定されていたら
            vel = MOVE_VEL * move_flag * MOVE_VEL_FACTOR_AIR  # 空中でもちょっと動ける
            if player.vx * vel <= 0 or abs(player.vx) < abs(vel):
                player.vx = vel

    # 速度補正：ほかの物体と接触している方向に移動する速度は0にする
    for obj in iter_movable():  # すべての固定されていない物体に対して
        if obj.contact.x_pos and obj.vx > 0:  # x軸プラス方向
            obj.vx = 0
        if obj.contact.x_neg and obj.vx < 0:  # x軸マイナス方向
            obj.vx = 0
        if obj.contact.y_pos and obj.vy > 0:  # y軸プラス方向
            obj.vy = 0
        if obj.contact.y_neg and obj.vy < 0:  # y軸マイナス方向
            obj.vy = 0

    # 位置計算
    for obj in iter_movable():  # すべての固定されていない物体に対して
        # 運動前の物体のコピーを保存
        obj_prev = copy.copy(obj)

        # 運動の法則 x = vt を適用
        obj.x += obj.vx * t_delta
        obj.y += obj.vy * t_delta

        # めり込み解決
        #  物体が進みすぎて固定物体にめり込んでいる可能性がある
        #  ここでめり込んだ物体を少しずつ前に戻して衝突を無かったことにする
        for obj_fixed in iter_fixed():  # すべての固定されている物体に対して
            if not collide(obj_prev, obj_fixed) and collide(obj, obj_fixed):
                # ↑ 運動前は衝突してなかったけど運動後に衝突したら
                while collide(obj, obj_fixed):  # 衝突している間
                    # 物体の運動を少しずつ巻き戻す
                    obj.x -= obj.vx * t_delta * COLLIDE_SOLVE_FACTOR
                    obj.y -= obj.vy * t_delta * COLLIDE_SOLVE_FACTOR

    # イベントループにこの処理を予約して繰り返す
    root.after(20, main_physics)


# ------------------------------------------
#  キー入力処理
# ------------------------------------------

# メイン（キー入力処理）
def main_key():
    global jump_flag, move_flag

    def is_pressed(key):
        return ctypes.windll.user32.GetAsyncKeyState(key) & 0x8000

    move_flag = 0  # いったん移動の予定フラグをクリア
    jump_flag = False  # いったんジャンプの予定フラグをクリア
    if is_pressed(65):  # A
        move_flag = -1  # 左方向への移動を予定する
    if is_pressed(68):  # D
        move_flag = +1  # 右方向への移動を予定する
    if is_pressed(32):  # Space
        jump_flag = True  # ジャンプを予定する
    if is_pressed(16):  # Shift
        move_flag *= 2  # 予定された移動を大きくする（走る）

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
