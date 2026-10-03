export type NowDoingAsk = { text: string; brief: string | null };
export type NowDoingAct = { label: string; steps: number; working: boolean };
export type NowDoingCost = { input: number; output: number; calls: number };

declare module "claude-code" {
  interface PluginState {
    "now-doing": {
      goal: string;
      ask: NowDoingAsk;
      act: NowDoingAct;
      cost: NowDoingCost;
      ctx: number;
    };
  }
}
