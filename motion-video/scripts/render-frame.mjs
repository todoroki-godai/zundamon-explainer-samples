// Host Chromium measurements found that display:none flushing did not fix raster
// history. --disable-partial-raster is set by both callers; wait two rAFs here.
export async function renderFrame(page, frame) {
 await page.evaluate(async f => {
  window.__render(f);
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
 }, frame);
}
