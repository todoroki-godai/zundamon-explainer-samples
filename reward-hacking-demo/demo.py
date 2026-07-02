"""reward hacking（採点の抜け道）を手元で体験する最小デモ。

お題は「is_prime(n): n が素数なら True を返す」。
同じお題に対して3つの実装を、2種類の採点でくらべます。

  - 甘い採点（WEAK_CASES）… 少数の入力しか確かめない
  - 厳しい採点（STRICT_CASES）… 広い範囲を確かめる

甘い採点だと、課題を「解いていない」抜け道の実装まで満点になります。
採点を厳しくすると、その抜け道が点を落として正体を現します。

標準ライブラリだけで動きます（外部インストール不要・LLMも呼びません）。
値はすべて教材用のダミーです。
"""


# ---------------------------------------------------------------------------
# お題の正解（採点の「ものさし」）
#
# WEAK は「甘い採点」。ここに並んだ入力しか確かめないので、
# ここだけ通ればいい、という“抜け道”を招きます。
# STRICT は「厳しい採点」。広い範囲を確かめるので抜け道が露見します。
# ---------------------------------------------------------------------------
WEAK_CASES = [
    (7, True),
    (8, False),
    (11, True),
    (4, False),
]

# 2〜49 を素数かどうかで自動生成（厳しい採点）
def _true_is_prime(n):
    if n < 2:
        return False
    for d in range(2, int(n ** 0.5) + 1):
        if n % d == 0:
            return False
    return True


STRICT_CASES = [(n, _true_is_prime(n)) for n in range(2, 50)]


# ---------------------------------------------------------------------------
# 3つの実装（候補）
# ---------------------------------------------------------------------------

# (1) 正直な実装：本当に素数判定をする
def honest(n):
    if n < 2:
        return False
    for d in range(2, int(n ** 0.5) + 1):
        if n % d == 0:
            return False
    return True


# (2) ハードコード：課題を解かず、甘い採点の“答え”だけを丸暗記する
#     WEAK_CASES で True になる入力（7, 11）だけを True にすれば満点。
def hardcode_cheat(n):
    return n in (7, 11)


# (3) テスト検知ズル：採点で使う入力だけ特別扱いし、それ以外は適当に返す
#     甘い採点の入力(4,7,8,11)には正解を返し、他は「全部素数」と嘘をつく。
def test_detection_cheat(n):
    if n in (4, 7, 8, 11):          # ← 採点で来る入力を“見分けて”いる
        return n in (7, 11)          #    その入力だけは正解を返す
    return True                      #    それ以外は中身ナシ（全部Trueと嘘）


CANDIDATES = [
    ("正直な実装     ", honest),
    ("ハードコード    ", hardcode_cheat),
    ("テスト検知ズル  ", test_detection_cheat),
]


# ---------------------------------------------------------------------------
# 採点
# ---------------------------------------------------------------------------
def grade(fn, cases):
    """cases を全部通した数を (合格数, 総数) で返す。"""
    passed = sum(1 for n, expected in cases if fn(n) == expected)
    return passed, len(cases)


def report(title, cases, note_full=None, note_fail=None):
    print(title)
    for name, fn in CANDIDATES:
        p, total = grade(fn, cases)
        full = (p == total)
        mark = "✅" if full else "❌"
        tail = ""
        if full and note_full and name.strip() != "正直な実装":
            tail = f"  ← {note_full}"
        if not full and note_fail:
            tail = f"  ← {note_fail}"
        print(f"  {name}: {p}/{total} 合格 {mark}{tail}")
    print()


def main():
    print("=== reward hacking デモ：甘い採点は「抜け道」を満点にする ===\n")
    print("お題: is_prime(n) … n が素数なら True を返す\n")

    report(
        f"--- 甘い採点（{len(WEAK_CASES)}ケースだけ: 7,8,11,4 で確認）---",
        WEAK_CASES,
        note_full="課題を解かず“採点の答え”だけを通している",
    )
    print("甘い採点では、抜け道の実装が正直な実装と“同点（満点）”になってしまう。\n")

    report(
        f"--- 厳しい採点（{len(STRICT_CASES)}ケース: 2〜49 を広く確認）---",
        STRICT_CASES,
        note_fail="露見！ 課題を解いていないので点を落とす",
    )
    print("採点を厳しくすると、抜け道は点を落として正体がバレる。\n")

    print("結論: AIは「点が上がる道」を通る。採点(テスト)が甘いと、")
    print("      課題を解かず“採点を通すだけ”の実装が満点になる（＝reward hacking）。")
    print("      対策は「採点を厳しく・広いケースで」。")
    print("      → WEAK_CASES を増やして、抜け道が落ちるまで強くしてみよう。")


if __name__ == "__main__":
    main()
