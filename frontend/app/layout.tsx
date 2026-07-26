import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "AI Ad Creator",
  description: "Paste a product URL, get a full ad set for every channel — one click.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink-950">
        <AuthProvider>
          <Navbar />
          <main className="mx-auto max-w-4xl px-4 pb-16 pt-8">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
