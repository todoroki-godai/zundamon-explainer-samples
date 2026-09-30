
const FPS = 30; let BEAT = 15;               // 120BPM = 15フレーム/拍
const T = s => Math.round(s * FPS);       // 秒→フレーム
const eo = x => 1 - Math.pow(1 - clamp(x), 3);            // easeOutCubic
const eb = x => { x = clamp(x); const c = 1.70158; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); }; // easeOutBack
const ei = x => Math.pow(clamp(x), 3);
const $ = id => document.getElementById(id);
// 出入り: 開始 a から d フレームで入り、終了 b の d フレーム前から抜ける
const inout = (f, a, b, d = 8) => clamp((f - a) / d) * (1 - clamp((f - (b - d)) / d));

window.__render = function (f) {
  if(!window.motion.initialized){const p=window.motion.brief.palette;for(const key of ["bg","fg","surface","on-surface","accent","on-accent","em","accent2","warn"])document.documentElement.style.setProperty("--"+key,p[key]);document.documentElement.style.setProperty("--font",p.font);window.motion.initialized=true;}
  BEAT=60*FPS/window.motion.timeline.bpm;
  const starts=window.motion.timeline.lines.map(line=>line.start);
  const S={s1:[starts[0],starts[1]],s2:[starts[1],starts[2]],s3:[starts[2],starts[3]],s4:[starts[3],starts[4]],s5:[starts[4],window.motion.timeline.main_frames]};
  const pulse = Math.exp(-(f % BEAT) / 4);                 // 拍ごとの脈動
  $('grid').style.transform = `translate(${-(f * 2) % 120}px,${-(f) % 120}px)`;
  put('glow', 960, 540, { s: 1 + 0.06 * pulse, o: 0.7 + 0.3 * pulse });

  // s1
  let [a, b] = S.s1;
  put('s1a', 960, 400, { s: eb((f - a) / 10), o: inout(f, a, b) });
  put('s1b', 960, 640 + 60 * (1 - eo((f - a - BEAT * 2) / 10)), { o: inout(f, a + BEAT * 2, b) });
  $('q').style.transform = `translateY(${-30 * pulse}px) rotate(${10 * pulse}deg)`;

  // s2
  [a, b] = S.s2;
  put('s2a', 960, 260, { o: inout(f, a, b), s: eb((f - a) / 10) });
  const cmd = '> claude --model 新しいモデル';
  const n = Math.floor(clamp((f - a - 6) / 30) * cmd.length);
  $('s2t').textContent = cmd.slice(0, n) + ((Math.floor(f / 8) % 2) ? '▍' : '');
  put('s2t', 960 + 400 * (1 - eo((f - a) / 12)), 520, { o: inout(f, a, b) });
  put('s2b', 960, 800, { s: eb((f - a - BEAT * 4) / 10), o: inout(f, a + BEAT * 4, b) });

  // s3
  [a, b] = S.s3;
  put('s3a', 560 - 700 * (1 - eo((f - a) / 10)), 380, { r: -4, o: inout(f, a, b) });
  put('s3b', 1360 + 700 * (1 - eo((f - a - BEAT * 2) / 10)), 380, { r: 4, o: inout(f, a + BEAT * 2, b) });
  const st = (f - a - BEAT * 4);
  put('s3c', 960, 740, { s: st < 0 ? 0 : 2.4 - 1.4 * eo(st / 6), r: -6, o: st < 0 ? 0 : inout(f, a + BEAT * 4, b, 4) });

  // s4
  [a, b] = S.s4;
  put('s4a', 960, 300, { o: inout(f, a, b) });
  const lvk = clamp((f - a - BEAT * 2) / (BEAT * 3));
  $('s4lv').textContent = 'LV ' + (lvk < 1 ? '1' : '2') + (lvk < 1 ? '' : ' ↑');
  put('s4lv', 960, 530, { o: inout(f, a, b), s: lvk >= 1 ? 1 + 0.25 * Math.exp(-(f - a - BEAT * 5) / 5) : 1 });
  put('s4bar', 960, 760, { o: inout(f, a, b) });
  $('s4fill').style.width = (lvk < 1 ? 10 + 90 * eo(lvk) : 100) + '%';

  // s5
  [a, b] = S.s5;
  put('s5a', 960, 430, { s: eb((f - a) / 12), o: clamp((f - a) / 8) });
  put('s5b', 960, 720, { s: (f < a + BEAT * 5 ? 0 : eb((f - a - BEAT * 5) / 10)) * (1 + 0.06 * pulse), o: f < a + BEAT * 5 ? 0 : 1 });
};
