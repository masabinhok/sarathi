import type { Metadata } from "next";
import {
  IBM_Plex_Mono,
  IBM_Plex_Sans,
  IBM_Plex_Sans_Devanagari,
  Source_Serif_4,
} from "next/font/google";
import "./globals.css";
import Masthead from "@/components/Masthead";

// Plex is a technical family drawn for engineering documentation, and its Devanagari
// companion is metrically compatible — so Nepali and English sit at equal weight in the
// same line rather than one looking bolted on.
const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const plexDeva = IBM_Plex_Sans_Devanagari({
  variable: "--font-plex-deva",
  subsets: ["devanagari", "latin"],
  weight: ["400", "500", "600"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  weight: ["400", "600"],
});

export const metadata: Metadata = {
  title: "IOE Admission Assistant",
  description:
    "Answers about the IOE BE/BArch entrance examination and admission process, from official notices.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${plexSans.variable} ${plexDeva.variable} ${plexMono.variable} ${sourceSerif.variable} h-full antialiased`}
    >
      <body className="bg-paper text-ink flex min-h-full flex-col">
        <Masthead />
        <main className="flex-1">{children}</main>
        <footer className="border-line mt-16 border-t">
          <div className="text-ink-faint mx-auto flex w-full max-w-6xl flex-col gap-1 px-5 py-8 text-xs sm:flex-row sm:items-center sm:justify-between">
            <p>
              Unofficial. Always confirm against{" "}
              <a
                className="decoration-line-strong hover:text-ink underline underline-offset-2"
                href="https://entrance.ioe.edu.np"
                target="_blank"
                rel="noreferrer"
              >
                entrance.ioe.edu.np
              </a>{" "}
              before acting.
            </p>
            <p>Answers are generated and may be wrong.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
