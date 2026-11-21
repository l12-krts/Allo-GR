import type { CSSProperties, ElementType, ComponentPropsWithRef, ReactElement } from "react";

export interface AlloAxes {
  /** 100–900 */
  weight?: number;
  /** 0 sharp … 50 friendly (default) … 100 round */
  roundness?: number;
  /** "auto" follows the font size (default), "none" keeps the Text design, or a value 9–32 */
  opticalSize?: "auto" | "none" | number;
  /** use the obliques */
  oblique?: boolean;
  /** OpenType features: { ss01: true, tnum: true } or a font-feature-settings string */
  features?: string | Record<string, boolean | number>;
}

export declare const alloFontFamily: string;
export declare function alloStyle(axes?: AlloAxes): CSSProperties;

export type AlloProps<T extends ElementType = "span"> = AlloAxes & { as?: T } & Omit<
    ComponentPropsWithRef<T>,
    keyof AlloAxes | "as"
  >;

export declare const Allo: <T extends ElementType = "span">(props: AlloProps<T>) => ReactElement | null;
export default Allo;
