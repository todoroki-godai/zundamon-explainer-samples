#!/usr/bin/env python3
"""丸投げ版：ブラウザを開きっぱなしで増殖する“悪い例”（シミュレーション）。

本物では headless ブラウザを起動するが、ここでは依存ゼロで「閉じ忘れて積み上がる」だけを再現する。
python unsafe.py を実行すると、開いたブラウザが片付けられず40個まで積み上がる様子が見える。
"""
from __future__ import annotations

opened: list[str] = []  # 開いたブラウザ。誰も閉じない。


def run_one_test(i: int) -> None:
    # 本来は「ブラウザを開く → ゲームを触る → 結果を見る」。だが“閉じる”処理が無い。
    browser = f"browser#{i}"
    opened.append(browser)  # 開きっぱなし


def main() -> None:
    for i in range(1, 41):  # テストを40回まわす
        run_one_test(i)
        if i % 8 == 0:
            print(f"  ...いま開いてるブラウザ: {len(opened)} 個")
    print(f"\n結果: ブラウザ {len(opened)} 個が開きっぱなし → PC悲鳴 😱")
    print("（テストのたびに開いて、閉じる人がいないから積み上がった）")


if __name__ == "__main__":
    main()
