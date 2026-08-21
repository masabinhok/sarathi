import type { Metadata } from "next";
import {
  DM_Sans,
  IBM_Plex_Sans_Devanagari,
  JetBrains_Mono,
  Newsreader,
} from "next/font/google";
import "./globals.css";

// Display face. Newsreader was drawn for news screens, which is what the notices
// half of this product is; used for the wordmark, headlines, and nothing smaller.
const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  weight: ["400", "500"],
});

const dmSans = DM_Sans({
  variable: "--font-dmsans",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
});

// Dates, source labels, form numbers: everything that is a code rather than a
// sentence is set in mono so it is scannable and column-aligned.
const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  weight: ["400", "500"],
});

// DM Sans carries no Devanagari, and the university's own name is written in it.
const deva = IBM_Plex_Sans_Devanagari({
  variable: "--font-deva",
  subsets: ["devanagari", "latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Sarathi — IOE Entrance and Admission Assistant",
  description:
    "Ask about the IOE BE/BArch entrance exam and admission, answered from official notices with every date in both Bikram Sambat and Gregorian.",
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
      className={`${newsreader.variable} ${dmSans.variable} ${jetbrains.variable} ${deva.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="bg-paper text-ink">{children}</body>
    </html>
  );
}
