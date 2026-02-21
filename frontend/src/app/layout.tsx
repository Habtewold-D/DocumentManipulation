import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Geist_Mono } from "next/font/google";
import { AppHeader } from "@/components/app/AppHeader";
import { Providers } from "./providers";
import "./globals.css";

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PDF Agent — AI-Powered Document Workspace",
  description: "Upload, edit, version, and compare PDFs using natural-language commands backed by MCP tools.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${geistMono.variable} font-sans antialiased`}
      >
        <Providers>
          <AppHeader />
          <div className="min-h-[calc(100vh-3.5rem)]">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}
