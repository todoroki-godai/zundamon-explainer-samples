# 一言の依頼から、15〜45秒のCM・解説動画（MP4）を作るスキル

動画の要点：「動画を作って」と一言頼むだけで、Claude が**世界観・ビート（速さ）・声**を選び、**台詞に合わせた場面を毎回書き下ろして**、声つきの MP4 まで仕上げる。

このフォルダは、その仕組みを **Claude Code のスキル**としてそのまま置ける形にした教材です。

## 何ができるか

- 一言の依頼（例:「ずんだマートの週末セールのCMを作って」）から、15〜45秒の MP4 を1本作る
- 決めるのは4つの軸：**型**（話の順番。`bin/motion-video list` で一覧）・**世界観**（色と質感）・**ビート**（速さと雰囲気）・**声**（語り口）
- 場面（HTML + JS）は、台詞の内容に合わせて Claude が毎回書く。決まったテンプレートに文字を流し込むのではない
- 作った動画を機械で点検する（文字が読めるか・声が無音でないか・黒い画面がないか）。最後に1秒ごとのコマ一覧 `review/sheet.png` を作るので、目でも確かめる

## 置き方

次のどちらか。

1. スキルとして置く：このフォルダを `~/.claude/skills/motion-video/` にコピーし、中で `npm install`
2. Claude Code でこのフォルダを開き、`SKILL.md` を読ませる

## 必要なもの

コードを読んで、実際に使っているものだけを挙げます。

| 必要なもの | 何に使う | 備考 |
|---|---|---|
| Node.js | 画面の撮影・点検（`playwright-core`） | `npm install` で入る |
| Chromium headless shell | 場面を1コマずつ撮る | `npx playwright-core install chromium-headless-shell` |
| ffmpeg / ffprobe | 連結・音声との合成・点検 | 別途インストール |
| Python 3 + `numpy` + `Pillow` | 音声・ビートの生成、点検 | `pip install numpy pillow` |
| Blender（**任意**） | `threeD: "blender"` を指定した時の導入3D（90コマ）だけ | 使わなければ不要。同梱の見本は使いません |
| `GOOGLE_GENERATIVE_AI_API_KEY` | Gemini の読み上げ（TTS）で声を作る | 環境変数で渡す |

**かかるお金**：声の生成で Gemini の API を呼ぶため、API の利用料がかかります。料金は変わり得るので、公式の料金ページで確認してください。それ以外（撮影・合成・点検）は手元の計算だけです。

**外部に送るもの**：Gemini の読み上げに送るのは、台詞・読み上げの指示・設定・API キーだけです。

## 使い方

Claude Code に頼みます。

```
ずんだマートの週末セールのCMを作って
```

Claude は `SKILL.md` の手順で進めます。

1. `bin/motion-video list` で型・世界観・ビート・声を選ぶ
2. `recipes/<型>.md` を読み、場面の順序・動き・台詞の長さを決める
3. `bin/motion-video new <作業フォルダ> --from channel-promo` で見本を写し、依頼に合わせて台詞と場面を書き直す
4. `bin/motion-video build <作業フォルダ>` で、音声・撮影・合成・点検までを一気に実行
5. 点検が赤なら直して再 build。`review/sheet.png` と `out.mp4` を見て確かめる

### 先にお金をかけずに試す（ドライラン）

API キーなしで、声の代わりにダミー音声（試験用。納品には使えない）で最後まで通せます。

```
npm install
npx playwright-core install chromium-headless-shell
bin/motion-video new /tmp/mv-demo --from channel-promo
MOTION_VIDEO_TTS_MOCK=1 bin/motion-video build /tmp/mv-demo
```

実際に走らせた最後の出力（ダミー音声・Blender なしの見本）：

```
PASS new /tmp/mv-demo
PASS auxiliary known syntax and 6 themes
PASS coverage 615 frames sampled every third frame; render order and fonts
PASS 尺=20.50s 台詞ごとの声=5 相関最小=0.999014 無音=0 黒コマ=0 総尺=OK
```

`/tmp/mv-demo/out.mp4` と `/tmp/mv-demo/review/sheet.png` ができます。

## 直し方のコツ

動画を見て「ここが違う」と感じたら、**感じたことを一言で** Claude に伝えるのが一番早いです。

- 「文字が小さくて読めない」「この場面が長い」「派手すぎる」など、見た印象のまま言う
- どこが悪いのか分からないときは、「**お手本と何がちがう？**」と聞く。Claude が自分の動画と、狙っていた動画との差を挙げてくれる
- 声が気に入らないときは、その行の `take`（整数）を上げて build し直すと、同じ台詞で別の読み方になる
- 世界観・ビート・声は `brief.json` の名前を変えるだけで切り替わる（`presets/` の中身が一覧）

## 見本（`examples/channel-promo/`）

チャンネル紹介の場面を、入力（`brief.json`・`scene.html`・`scene.js`）だけ置いています。画像・動画・音声などの生成物は含みません（build で作られます）。

## 同梱のテスト

`tests/` には、外部に依存しない3本だけ入れています。

```
python3 tests/test_tts.py
python3 tests/test_check_silence.py
node tests/coverage_logic.test.mjs
```

## 注意

- 教材用のスキルです。API キーをファイルに書かず、環境変数で渡してください
- 点検は「既知の種類の欠陥だけ」を検出します（迂回可能）。最後は必ず `review/sheet.png` を目で確かめてください
