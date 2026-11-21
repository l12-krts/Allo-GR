// Allo GR for React: the font's CSS, plus a component and a style helper for its axes.
// Plain ESM, no build step; React is a peer dependency. Import the CSS once at your app's root:
//   import "allo-gr";
import { createElement, forwardRef } from "react";

export const alloFontFamily = '"Allo", system-ui, sans-serif';

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/**
 * Style for Allo with its axes.
 *   weight       100–900 (font-weight)
 *   roundness    0 sharp … 50 friendly … 100 round ("ROND"), default 50
 *   opticalSize  "auto" (follows font size, default), "none" (Text design), or 9–32
 *   oblique      true for the obliques
 *   features     OpenType features, e.g. { ss01: true, tnum: true } or "ss01, tnum"
 */
export function alloStyle({ weight, roundness, opticalSize, oblique, features } = {}) {
  const style = { fontFamily: alloFontFamily };
  if (weight != null) style.fontWeight = weight;
  if (oblique) style.fontStyle = "italic";
  const axes = [];
  if (roundness != null) {
    style["--allo-rond"] = clamp(Number(roundness), 0, 100);
  }
  axes.push('"ROND" var(--allo-rond, 50)');
  if (typeof opticalSize === "number") axes.push(`"opsz" ${clamp(opticalSize, 9, 32)}`);
  else if (opticalSize === "none") style.fontOpticalSizing = "none";
  style.fontVariationSettings = axes.join(", ");
  if (features) {
    style.fontFeatureSettings =
      typeof features === "string"
        ? features
        : Object.entries(features)
            .map(([tag, on]) => `"${tag}" ${on === true ? 1 : on === false ? 0 : on}`)
            .join(", ");
  }
  return style;
}

/**
 * <Allo as="h1" weight={700} roundness={100}>Καλημέρα</Allo>
 * Any other prop goes to the element; `style` is merged last.
 */
export const Allo = forwardRef(function Allo(
  { as = "span", weight, roundness, opticalSize, oblique, features, style, ...props },
  ref
) {
  return createElement(as, {
    ref,
    ...props,
    style: { ...alloStyle({ weight, roundness, opticalSize, oblique, features }), ...style },
  });
});

export default Allo;
