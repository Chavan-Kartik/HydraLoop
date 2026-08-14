import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "HydraLoop Command Center",
  description: "Co-evolutionary adversarial payment security lab",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-mono text-slate-200">
        <div className="mx-auto max-w-6xl px-6 py-6">
          <Nav />
          {children}
        </div>
      </body>
    </html>
  );
}
