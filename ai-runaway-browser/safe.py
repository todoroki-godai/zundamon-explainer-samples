#!/usr/bin/env python3
"""安全な任せ方：作法＋番犬＋自分の分だけ片付け（シミュレーション）。

動画③の3つを実装で示す:
  ① 作法    … いちばん軽い設定で開く（本物の起動引数は末尾メモ）
  ② 番犬    … 同時に開いている数を見張り、しきい値を超えたら止める
  ③ 片付け  … 全消しでなく「自分が開いた分」だけ閉じる（隣の作業を巻き添えにしない）

python safe.py で、開いてる数が数個でピタッと安定するのが見える。
"""
from __future__ import annotations

import contextlib

MAX_CONCURRENT = 8  # 番犬：同時に開く数がこれを超えたら異常とみなす


class BrowserPool:
    def __init__(self) -> None:
        self._mine: list[str] = []  # 自分が開いた分だけ覚える（巻き添え防止）

    def in_use(self) -> int:
        return len(self._mine)

    def launch(self) -> str:
        # ① 作法：いちばん軽い設定で開く（実物の起動引数は末尾メモ）
        browser = f"browser#{len(self._mine) + 1}"
        self._mine.append(browser)
        # ② 番犬：開きすぎていたら暴走の前に止める
        if len(self._mine) > MAX_CONCURRENT:
            raise RuntimeError(f"ブラウザが {len(self._mine)} 個！暴走の前に停止します")
        return browser

    def close(self, browser: str) -> None:
        if browser in self._mine:
            self._mine.remove(browser)

    @contextlib.contextmanager
    def session(self):
        browser = self.launch()
        try:
            yield browser
        finally:
            self.close(browser)  # 終わったら必ず閉じる（開きっぱなしにしない）

    def cleanup(self) -> None:
        # ③ 片付け：全消しでなく“自分の分”だけ閉じる
        self._mine.clear()


def demo_normal() -> None:
    print("【安全版】テストを40回。使い終わるたびに閉じる:")
    pool = BrowserPool()
    peak = 0
    for i in range(1, 41):
        with pool.session():
            peak = max(peak, pool.in_use())
    print(f"  同時に開いた最大 = {peak} 個（40個まで積み上がらない）✅")


def demo_watchdog() -> None:
    print("\n【番犬テスト】わざと閉じずに開き続けると:")
    pool = BrowserPool()
    try:
        for _ in range(40):
            pool.launch()  # 閉じない＝暴走パターン
    except RuntimeError as e:
        print(f"  番犬が作動 → {e}")
        print(f"  （{pool.in_use()} 個で停止。40個まで増える前に止められた）")
    finally:
        pool.cleanup()  # 自分の分だけ片付け


if __name__ == "__main__":
    demo_normal()
    demo_watchdog()

# ───────────────────────────────────────────────────────────
# 本物（Playwright）でやる場合の“作法”と“番犬”のレシピ:
#
#   from playwright.sync_api import sync_playwright
#
#   LAUNCH_ARGS = [
#       "--disable-gpu",            # 絵を描く機能オフ＝省エネ（重い画面で固まりにくい）
#       "--disable-dev-shm-usage",  # 共有メモリ枯渇で固まるのを防ぐ
#       "--no-sandbox",
#   ]
#   with sync_playwright() as p:
#       browser = p.chromium.launch(headless=True, args=LAUNCH_ARGS)  # ① 作法
#       try:
#           page = browser.new_page()
#           ...  # 使う
#       finally:
#           browser.close()         # 必ず閉じる
#
#   # ② 番犬（別ループ or cron で定期実行）:
#   #   import subprocess
#   #   n = int(subprocess.run(["pgrep", "-fc", "chrome-headless-shell"],
#   #                          capture_output=True, text=True).stdout or 0)
#   #   if n > MAX_CONCURRENT: 起動を止める
#   #
#   # ③ 片付け:
#   #   全消しの broadcast kill（pkill -f chrome-headless-shell）は、
#   #   隣で動いている別の作業のブラウザまで巻き添えにする。
#   #   自分が起動した PID だけを覚えておいて、それだけ閉じる。
# ───────────────────────────────────────────────────────────
