import type { Metadata } from "next";
import {
  IBM_Plex_Sans_Devanagari,
  Inter,
  JetBrains_Mono,
} from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

// Dates, source tags, form numbers, model ids: everything that is a code rather than a
// sentence is set in mono so it is scannable and column-aligned.
const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  weight: ["400", "500"],
});

// Inter carries no Devanagari, and the university's own name is written in it.
const deva = IBM_Plex_Sans_Devanagari({
  variable: "--font-deva",
  subsets: ["devanagari", "latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Sarathi — IOE Entrance and Admission Assistant",
  description:
    "Ask about the IOE BE/BArch entrance exam and admission process, answered from official notices, alongside a live feed of what the campuses have published.",
};

// Runs before first paint so a dark-mode visitor never sees a white flash.
const THEME_SCRIPT = `
try {
  var saved = localStorage.getItem("ioe.theme");
  var dark = saved ? saved === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "dark" : "light";
} catch (e) {}
`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      data-theme="light"
      className={`${inter.variable} ${jetbrains.variable} ${deva.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="bg-feed text-ink">{children}</body>
    </html>
  );
}
