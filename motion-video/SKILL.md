---
name: motion-video
description: 一言の依頼から世界観・ビート・声を選び、台詞専用の場面を書き下ろして15〜45秒のMP4を作る。
---

# Motion video

1. `bin/motion-video list` で型・世界観・ビート・声を選ぶ。型は話の順番、世界観は色と質感、ビートは速さと雰囲気、声は語り口で選ぶ。
2. `recipes/<型>.md` を読み、場面の順序・動き・図・台詞の長さを決める。
3. `bin/motion-video new <作業dir> --from channel-promo` で完全な見本を写す。`brief.json` の4軸・台詞を依頼に合わせ、`scene.html` と必要な `scene.js`・画像を書き下ろす。台詞の内容に合わせて図、動き、拍の脈動、場面の重なりを作る。日本語の改行位置は自分で決めて `<br>` を置く。`__render(frame)` は任意のフレームを単独で呼んでも同じ画になるように書く。文字は `.t-on-bg`、`.t-on-surface`、`.t-on-accent` のどれかを付け、強調 `.em` は `.t-on-bg` の中に置く。色は CSS 変数を使う。`window.motion.brief` と `window.motion.timeline` の `bpm`・開始フレームを読む。
動く要素の `backface-visibility:hidden` は見た目に必要な場合だけ使う。撮影側は各フレームで描画ツリーを再生成してから撮る。
4. `bin/motion-video build <作業dir>` を実行する。build は音声と timeline を作り、その作業ディレクトリの scene を全表示区間の3フレームごとに検査してから撮影・合成・check をする。
5. `bin/motion-video check <作業dir>` が赤なら原因を直して再 build する。build の最後に作る `<作業dir>/review/sheet.png`（1 秒ごとのコマ一覧）を開き、**全コマで文字が読めることを目で確かめる**。読めなければ場面を直して build し直す。`out.mp4` も再生して台詞と動きの対応を確認する。
声が気に入らない・無音で赤になったら、その行の整数 `take` を上げて build し直す（既定は 0）。

API キーは `GOOGLE_GENERATIVE_AI_API_KEY` で渡す。試験時のみ `MOTION_VIDEO_TTS_MOCK=1` を使う。モック音声は納品用には使わない。`threeD: "blender"` は導入90フレームが必要な場合だけ指定する。外部送信は Gemini TTS の台詞・読み上げ指示・設定・認証だけ。

機械で止める文字の欠陥は、標本の画素比較で可視画素が文字箱の 0.5% 以下の文字。幅または高さが 0〜1px の文字は画素比較から外す。`scale(0)` で消した文字、部分的な覆い（覆い 50〜90%、可視 3〜30%）、文字要素自身の `::before` / `::after` による覆いは advisory で、全コマ一覧を目視で確認する。検査は既知の種別のみ検出・迂回可能。全面ワイプで文字が隠れる間は、その文字を `visibility:hidden` にする。
