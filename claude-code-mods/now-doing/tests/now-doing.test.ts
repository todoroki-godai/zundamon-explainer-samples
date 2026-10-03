import { describe, expect, test } from "claude-code/testing";

const usage = { input_tokens: 40, output_tokens: 12, cache_creation_input_tokens: 0, cache_read_input_tokens: 0 };
const props = { hasSurvey: false, isWorking: true, maxRows: 10, bodyColumns: 120 };

describe("now-doing", () => {
  test("the band follows the goal, the latest ask and the current step", async ($, on) => {
    // Hooks registered here run after the mod and stub what Claude Code would answer.
    const asked: string[] = [];
    on("session.start", ($, e) => ({ cwd: e.cwd }));
    on("session.usage", () => ({
      value: { startedAt: 0, rateLimits: [], context: { tokens: 44_000, window: 200_000, percent: 22 } },
    }));
    on("prompt.submit", ($, e) => ({ text: e.text }));
    on("model.complete", ($, e) => {
      asked.push(e.prompt);
      const text = e.prompt.includes("こんな感じ")
        ? "1行目: 「ログイン画面の不具合を直す」\n2行目: 現状の共有"
        : "ログイン画面の不具合を直す\nログイン画面のバグ修正依頼";
      return { value: { isAnswered: true, text, usage } };
    });
    on("tool.call", () => ({ result: { text: "ok" } }));
    on("turn.complete", () => ({ text: "" }));

    await $.session.start({ surface: "terminal", isInteractive: true, cwd: "/work" } as any);
    await $.prompt.submit({ text: "ログイン画面のバグを直して。\n再現手順は…", wait: false, origin: { kind: "composer" } } as any);

    const ui = await $.ui.mount({ plugin: "now-doing", surface: "terminal", component: "AbovePrompt", props } as any);
    expect(await ui.find({ type: "Text", text: /^ログイン画面の不具合を直す$/ })).toBeDefined();
    expect(await ui.find({ type: "Text", text: /^ログイン画面のバグ修正依頼$/ })).toBeDefined();
    expect(await ui.find({ type: "Text", text: /考え中（0手目）/ })).toBeDefined();
    expect(await ui.find({ type: "Text", text: /記憶 22%/ })).toBeDefined();
    expect(await ui.find({ type: "Text", text: /入力 40 \/ 出力 12 トークン（1回）/ })).toBeDefined();
    expect(asked[0]).toContain("これまでの目的: （まだ無い）");

    await $.tool.call({ tool: "Bash", command: "npm test", description: "テストを実行" } as any);
    expect(await ui.find({ type: "Text", text: /Bash: テストを実行（1手目）/ })).toBeDefined();

    await $.turn.complete({ reason: "answer", answer: "ok", durationMs: 1 } as any);
    expect(await ui.find({ type: "Text", text: /待機中（1手で完了）/ })).toBeDefined();

    // 短い相づちでは、直近だけが変わり、目的は残る。モデルが付けた「1行目:」とかぎ括弧は落とす。
    await $.prompt.submit({ text: "こんな感じ", wait: false, origin: { kind: "composer" } } as any);
    expect(asked[1]).toContain("これまでの目的: ログイン画面の不具合を直す");
    expect(await ui.find({ type: "Text", text: /^ログイン画面の不具合を直す$/ })).toBeDefined();
    expect(await ui.find({ type: "Text", text: /^現状の共有$/ })).toBeDefined();
    expect(await ui.find({ type: "Text", text: /（2回）/ })).toBeDefined();
    await ui.unmount();
  });

  test("when the summary fails, the goal and the latest ask show the words as typed", async ($, on) => {
    on("prompt.submit", ($, e) => ({ text: e.text }));
    on("model.complete", () => ({ deny: "no model in this test" }));
    await $.prompt.submit({ text: "請求書の集計を直して", wait: false, origin: { kind: "composer" } } as any);
    const ui = await $.ui.mount({ plugin: "now-doing", surface: "terminal", component: "AbovePrompt", props } as any);
    expect(await ui.find({ type: "Text", text: /^目的 $/ })).toBeDefined();
    expect(await ui.find({ type: "Text", text: /^請求書の集計を直して$/ })).toBeDefined();
    await ui.unmount();
  });

  test("a prompt that is not typed by the person leaves the band alone", async ($, on) => {
    on("prompt.submit", ($, e) => ({ text: e.text }));
    // The mod yields the band with next(e); this stands for what Claude Code draws there.
    on("ui.render", ($, e) => {
      const { Text } = $.ui.resolve(e);
      return Text({ children: "(engine)" });
    });
    await $.prompt.submit({ text: "background task finished", wait: false, origin: { kind: "bridge" } } as any);
    const ui = await $.ui.mount({ plugin: "now-doing", surface: "terminal", component: "AbovePrompt", props } as any);
    expect(await ui.find({ type: "Text", text: /\(engine\)/ })).toBeDefined();
    expect(await ui.find({ type: "Text", text: /直近/ })).toBeUndefined();
    await ui.unmount();
  });
});
