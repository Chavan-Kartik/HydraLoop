import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar, MobileNav } from "@/components/Sidebar";
import { KpiBar } from "@/components/KpiBar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "HydraLoop - Adversarial Payment Security Lab",
  description:
    "A co-evolutionary lab that breeds agentic-commerce fraud and hardens the defense in a closed loop, until the attack stops paying.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="bg-canvas font-sans text-ink antialiased">
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <MobileNav />
            <KpiBar />
            <main className="flex-1 px-4 py-4 lg:px-6 lg:py-5">
              <div className="mx-auto w-full max-w-[1600px]">{children}</div>
            </main>
            <footer className="border-t border-line px-4 py-2.5 text-2xs text-ink-ghost lg:px-6">
              Synthetic, sandboxed, behavioural-metadata-only. No PII. Every decision on a
              tamper-evident trail.
            </footer>
          </div>
        </div>
      </body>
    </html>
  );
}
