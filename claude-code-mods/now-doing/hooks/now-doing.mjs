// now-doing: 入力欄の上に「目的 / 直近 / いま / 記憶領域」を枠つきで出す。
// 直近と作業の行は手元の出来事から組み立てるのでトークンを使わない。
// SUMMARIZE が true のときだけ、発言1件につき1回、小さいモデルで目的の更新と発言の言い直しをする。
const SUMMARIZE = true;
const SUMMARY_MODEL = "haiku";
const SUMMARY_INPUT_CHARS = 1500;
const LABEL_CHARS = 70;
const SUMMARY_SYSTEM = [
  "2行だけ返す。前置き・番号・かぎ括弧は付けない。",
  "1行目: これまでの目的と新しい発言を踏まえた、会話全体の目的を30字以内の日本語で。",
  "新しい発言が相づち・確認・短い返事・報告なら、これまでの目的をそのまま返す。",
  "2行目: 新しい発言を30字以内の日本語で言い直す。",
].join("\n");

// Held by the host, so the values survive a hot reload of this file.
const goal = { plugin: "now-doing", key: "goal" };
const ask = { plugin: "now-doing", key: "ask" };
const act = { plugin: "now-doing", key: "act" };
const cost = { plugin: "now-doing", key: "cost" };
const ctx = { plugin: "now-doing", key: "ctx" };

export function register(on) {
  on("session.start", async ($, e, next) => {
    const result = await next(e);
    await readContext($);
    return result;
  });

  on("prompt.submit", async ($, e, next) => {
    const text = oneLine(String(e.text ?? ""));
    const isTyped = e.origin?.kind === "composer" && text !== "" && !text.startsWith("/");
    if (isTyped) {
      await $.state.set(ask, { text, brief: null });
      await $.state.set(act, { label: "考え中", steps: 0, working: true });
      const { value: purpose } = await $.state.get(goal);
      // 要約を使わない／失敗したときも目的の行が空にならないよう、最初の発言を仮の目的にする。
      if (!purpose) await $.state.set(goal, text);
    }
    const result = await next(e);
    if (isTyped && SUMMARIZE) {
      // 要約は飾り。失敗しても目的と直近の行は原文のまま出るので、ここで握りつぶす。
      await summarize($, text).catch(() => {});
    }
    return result;
  });

  on("turn.start", async ($, e, next) => {
    if (!e.agentId) {
      const { value: now } = await $.state.get(act);
      if (now) await $.state.set(act, { ...now, working: true });
    }
    return next(e);
  });

  on("tool.call", async ($, e, next) => {
    if (!e.agentId) {
      // main-loop calls only, not subagents
      const { value: now } = await $.state.get(act);
      await $.state.set(act, { label: labelFor(e), steps: (now?.steps ?? 0) + 1, working: true });
    }
    return next(e);
  });

  on("turn.complete", async ($, e, next) => {
    const result = await next(e);
    if (!e.agentId) {
      const { value: now } = await $.state.get(act);
      if (now) await $.state.set(act, { ...now, working: false });
      await readContext($);
    }
    return result;
  });

  on("ui.render", { component: "AbovePrompt" }, async ($, e, next) => {
    const { value: purpose } = await $.state.get(goal);
    const { value: request } = await $.state.get(ask);
    const { value: now } = await $.state.get(act);
    const { value: spent } = await $.state.get(cost);
    const { value: percent } = await $.state.get(ctx);
    if (e.props.hasSurvey || !request) {
      return next(e);
    }
    const { Box, Text } = $.ui.resolve(e);
    return band(Box, Text, purpose, request, now, spent, percent);
  });
}

async function readContext($) {
  const { context } = await $.session.usage();
  if (!context?.window) return;
  const percent = context.percent ?? Math.round(((context.tokens ?? 0) / context.window) * 100);
  await $.state.set(ctx, percent);
}

async function summarize($, text) {
  const { value: purpose } = await $.state.get(goal);
  const r = await $.model.complete({
    model: SUMMARY_MODEL,
    system: SUMMARY_SYSTEM,
    prompt: `これまでの目的: ${purpose && purpose !== text ? purpose : "（まだ無い）"}\n新しい発言: ${text.slice(0, SUMMARY_INPUT_CHARS)}`,
    maxTokens: 120,
    timeoutMs: 8000,
  });
  const { value: spent } = await $.state.get(cost);
  await $.state.set(cost, {
    input: (spent?.input ?? 0) + (r.usage?.input_tokens ?? 0),
    output: (spent?.output ?? 0) + (r.usage?.output_tokens ?? 0),
    calls: (spent?.calls ?? 0) + 1,
  });
  if (!r.isAnswered) return;
  const [first, second] = r.text.split("\n").map(tidy).filter((line) => line !== "");
  if (first) await $.state.set(goal, first);
  const { value: request } = await $.state.get(ask);
  // 要約を待つ間に次の発言が来ていたら、古い言い直しは捨てる。
  if (second && request?.text === text) {
    await $.state.set(ask, { text, brief: second });
  }
}

function band(Box, Text, purpose, request, now, spent, percent) {
  const rows = [];
  if (purpose) rows.push(row(Box, Text, "目的", "magenta", purpose));
  rows.push(row(Box, Text, "直近", "cyan", request.brief ?? request.text));
  if (now) {
    const state = now.working ? `${now.label}（${now.steps}手目）` : `待機中（${now.steps}手で完了）`;
    rows.push(row(Box, Text, "いま", now.working ? "yellow" : "green", state));
  }
  const notes = [];
  if (typeof percent === "number") notes.push(`記憶 ${percent}%`);
  if (spent?.calls) notes.push(`要約に使った分 入力 ${spent.input} / 出力 ${spent.output} トークン（${spent.calls}回）`);
  if (notes.length > 0) {
    rows.push(Text({ dimColor: true, wrap: "truncate-end", children: notes.join(" · ") }));
  }
  // 枠で囲み、上に1行あけて、Claude の回答と帯の境目を見分けやすくする。
  return Box({
    flexDirection: "column",
    marginTop: 1,
    paddingX: 1,
    borderStyle: "round",
    borderColor: "cyan",
    borderDimColor: true,
    children: rows,
  });
}

function row(Box, Text, name, color, body) {
  return Box({
    flexDirection: "row",
    children: [
      Text({ color, bold: true, children: `${name} ` }),
      Text({ wrap: "truncate-end", children: body }),
    ],
  });
}

function labelFor(e) {
  const tool = String(e.tool);
  const name = tool.startsWith("mcp__") ? tool.split("__").slice(1).join(" ") : tool;
  const input = e.input ?? e;
  const detail =
    input.description ?? input.summary ?? baseName(input.file_path) ?? input.command ?? input.skill ?? input.url ?? input.pattern;
  if (typeof detail !== "string" || detail === "") return name;
  return `${name}: ${clip(oneLine(detail), LABEL_CHARS)}`;
}

function baseName(path) {
  if (typeof path !== "string" || path === "") return undefined;
  return path.split("/").pop();
}

function oneLine(text) {
  return text.replace(/\s+/g, " ").trim();
}

// モデルが付けがちな「1行目:」やかぎ括弧を落とす。
function tidy(line) {
  return oneLine(line)
    .replace(/^[12]行目\s*[:：]\s*/, "")
    .replace(/^[「『"]+|[」』"]+$/g, "");
}

function clip(text, max) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}
