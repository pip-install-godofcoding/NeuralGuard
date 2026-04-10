import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "NeuralGuard — LLM Proxy Dashboard",
  description:
    "Monitor your AI costs, track savings from semantic caching and smart routing, and verify response trustworthiness.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-slate-950 text-slate-100 antialiased min-h-screen selection:bg-indigo-500/30`}>
        {children}
      </body>
    </html>
  );
}
