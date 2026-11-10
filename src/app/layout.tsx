import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { AmbientEffects } from "../components/motion/AmbientEffects";
import { SmoothScroll } from "../components/motion/SmoothScroll";
import { TransitionLoaderGate } from "../components/loader/TransitionLoaderGate";

const displayFont = localFont({
  src: [
    { path: "../../public/fonts/PlayfairDisplay-Regular.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/PlayfairDisplay-Bold.woff2", weight: "700", style: "normal" }
  ],
  variable: "--cv-font-display",
});

const bodyFont = localFont({
  src: [
    { path: "../../public/fonts/Inter-Regular.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/Inter-Medium.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/Inter-SemiBold.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/Inter-Bold.woff2", weight: "700", style: "normal" }
  ],
  variable: "--cv-font-body",
});

const syneFont = localFont({
  src: [
    { path: "../../public/fonts/Syne-400.woff2", weight: "400", style: "normal" },
    { path: "../../public/fonts/Syne-500.woff2", weight: "500", style: "normal" },
    { path: "../../public/fonts/Syne-600.woff2", weight: "600", style: "normal" },
    { path: "../../public/fonts/Syne-700.woff2", weight: "700", style: "normal" },
    { path: "../../public/fonts/Syne-800.woff2", weight: "800", style: "normal" }
  ],
  variable: "--cv-font-syne",
});

export const metadata: Metadata = {
  title: "CardioVanta | Intelligent Cardiovascular Insight",
  description: "A premium cardiovascular intelligence platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body className={`${bodyFont.variable} ${displayFont.variable} ${syneFont.variable}`}>
        {children}
        <TransitionLoaderGate />
        <AmbientEffects />
        <SmoothScroll />
      </body>
    </html>
  );
}
