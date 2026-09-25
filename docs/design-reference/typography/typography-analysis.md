# CardioVanta Typography Analysis

## 1. Source Evidence
[OBSERVED FROM REFERENCE]
Chrome DevTools screenshots confirm the following exact font families are in use on the reference site:
- **Display/Headings:** `Mayo Clinic Serif Display` (variants: `MayoClinicSerifDisplay-Light`, `MayoClinicSerifDisplay-Bold`)
- **Body:** `Mayo Clinic Sans` (variant: `MayoClinicSans-Regular`)

## 2. Display Font Analysis
[OBSERVED FROM REFERENCE]
- **Serif style:** Transitional/Modern serif with sharp, precise bracketed serifs.
- **Stroke contrast:** High contrast between thick stems and thin hairlines, especially visible in the Bold weight.
- **Apparent weight:** Light (approx. 300) for large hero text, Bold (approx. 700) for section headings.
- **Proportions:** Moderately condensed with a generous x-height.
- **Terminal shapes:** Teardrop terminals on lowercase letters (e.g., 'a', 'c').
- **Line-height:** Tight line-height (approx. 1.08 - 1.25) to keep large text grouped.
- **Visual hierarchy:** Heavy reliance on scale and stark weight contrast (Light vs Bold) rather than color to establish hierarchy.

[RECOMMENDATION FOR CARDIOVANTA]
- Use the Light (300) weight for massive, calm hero statements to evoke approachability and premium care.
- Use the Bold (700) weight for structural page headings to evoke institutional authority.

## 3. Body Font Analysis
[OBSERVED FROM REFERENCE]
- **Sans-serif character:** Clean, contemporary, highly legible humanist/neo-grotesque hybrid.
- **x-height:** Large x-height for optimal readability at small sizes.
- **Stroke uniformity:** Low stroke contrast, very uniform stems.
- **Apparent weight:** Regular (approx. 400).
- **Spacing:** Comfortable, slightly open letter-spacing.
- **Line-height:** Generous line-height (approx 1.4) for long-form reading.

[RECOMMENDATION FOR CARDIOVANTA]
- Use a modern sans for all functional UI elements, data tables, and numerical outputs where precision is paramount.

## 4. Observed Reference Metrics
[OBSERVED FROM REFERENCE]
- **Hero Heading (H1):** 48px size, 52px line-height (1.08), 300 weight.
- **Section Heading (H2):** 32px size, 40px line-height (1.25), 700 weight.
- **Body Paragraph (P):** 20px size, 28px line-height (1.4), 400 weight.

[RECOMMENDATION FOR CARDIOVANTA]
- Scale down body text slightly for dense medical UI forms (e.g., 16px body, 14px labels) while keeping the generous H1/H2 display proportions.

## 5. Recommended CardioVanta Typography System
[RECOMMENDATION FOR CARDIOVANTA]
- **Hero display (H1):** Mayo Clinic Serif Display, 300 weight, 48px, line-height 1.1, tight letter-spacing (-0.02em).
- **Page title:** Mayo Clinic Serif Display, 300 weight, 36px, line-height 1.2.
- **Section heading (H2):** Mayo Clinic Serif Display, 700 weight, 24px-32px, line-height 1.25.
- **Subsection heading (H3):** modern sans, 600 weight, 20px, line-height 1.3.
- **Body:** modern sans, 400 weight, 16px, line-height 1.5.
- **Body emphasis:** modern sans, 600 weight, 16px.
- **Labels:** modern sans, 500-600 weight, 14px.
- **Inputs:** modern sans, 400 weight, 16px.
- **Buttons:** modern sans, 600 weight, 16px.
- **Navigation:** modern sans, 500 weight, 14px.
- **Helper text:** modern sans, 400 weight, 12px.
- **Warning text:** modern sans, 500 weight, 14px.
- **Metadata:** modern sans, 400 weight, 12px.
- **Probability number:** modern sans, 700 weight, 64px, tabular numerals.
- **Explanation values:** modern sans, 400 weight, 14px, tabular numerals.
- **Technical feature identifiers:** monospace or modern sans, 400 weight, 12px.

## 6. Responsive Typography
[RECOMMENDATION FOR CARDIOVANTA]
- Mobile H1: scale down from 48px to 32px.
- Mobile H2: scale down from 32px to 24px.
- Base UI text (inputs/buttons) remains at minimum 16px on mobile to prevent iOS zooming.

## 7. Local Font Implementation
[RECOMMENDATION FOR CARDIOVANTA]
- **Strategy:** Use Next.js `next/font/local` utility.
- **Path:** Place authorized fonts at `frontend/public/fonts/MayoClinicSerifDisplay-Light.woff2` and `MayoClinicSerifDisplay-Bold.woff2`.
- The `localFont` function will generate a CSS custom property (e.g., `--cv-font-display`) which can be applied in `globals.css` or layout wrappers.
- No runtime requests to Mayo Clinic or Google Fonts dependencies are permitted.

## 8. Exact vs Approximate Usage
[RECOMMENDATION FOR CARDIOVANTA]
- **Exact:** If the authorized `.woff2` files are supplied in the repository, the CSS variable `--cv-font-display` will explicitly map to the local `Mayo Clinic Serif Display` font stack.
- **Approximate:** If the files are missing, the build must fallback to a standard system serif stack (e.g., `Georgia, "Times New Roman", serif`) for development.
- **IMPORTANT:** Exact rendering absolutely requires authorized local font files. Do NOT scrape, download, or reconstruct proprietary webfonts from external websites under any circumstances.

## 9. Brand Integration
[RECOMMENDATION FOR CARDIOVANTA]
- Deep red and near-black typography paired with the editorial Serif creates **"Editorial Healthcare Authority"**.
- The clean modern sans used for data, coupled with tabular numerals and subtle circuit logo motifs, creates **"Modern Clinical Technology"**.
- The stark contrast between the humanistic serif headings and precise sans UI creates a balanced, premium feel unique to CardioVanta, distinguishing it from generic clinical templates.

## 10. Typography Do / Don't
[RECOMMENDATION FOR CARDIOVANTA]
- **DO** use the Serif for large, calming, authoritative headers.
- **DO** use the Sans for all clinical data, inputs, and functional UI.
- **DO** preserve the generous whitespace and restrained layout of the reference.
- **DO NOT** use the Serif font for small UI labels, buttons, or data tables.
- **DO NOT** mimic the Mayo Clinic blue color palette, Mayo logo, or layout exactness. CardioVanta must remain visually distinct.
- **DO NOT** use the Serif font if the authorized local assets are not present; use the system fallback instead of stealing webfonts.
