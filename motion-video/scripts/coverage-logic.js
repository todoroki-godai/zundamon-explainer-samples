// Shared by the browser sweep and browser-free Node tests.
globalThis.motionCoverageLogic = Object.freeze({
  parseRgb(value) {
    const match = /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*(0|1|0?\.\d+)\s*)?\)$/.exec(value);
    if (!match || (value.startsWith('rgba(') !== (match[4] !== undefined))) return null;
    const color = match.slice(1, 4).map(Number);
    const alpha = match[4] === undefined ? 1 : Number(match[4]);
    return color.every(channel => channel <= 255) && alpha <= 1 ? [...color, alpha] : null;
  },
  sameOpaqueColor(actual, expected) {
    const parts = this.parseRgb(actual);
    return parts !== null && parts[3] >= 0.999 && /^#[0-9a-f]{6}$/i.test(expected) &&
      parts.slice(0, 3).every((channel, index) => channel === parseInt(expected.slice(1 + index * 2, 3 + index * 2), 16));
  },
  effectiveOpacity(styles) {
    if (styles.some(style => style.display === 'none' || style.visibility !== 'visible')) return 0;
    return styles.reduce((opacity, style) => opacity * Number(style.opacity), 1);
  },
  hasInternalOverflow({scrollWidth, scrollHeight, clientWidth, clientHeight}) {
    return scrollWidth > clientWidth + 1 || scrollHeight > clientHeight + 1;
  },
  opacityFailure(samples) {
    return samples.some(sample => sample.own > 0.5) && !samples.some(sample => sample.effective > 0.5);
  },
  occludedFraction(fraction) {
    return fraction <= 0.005;
  }
});
