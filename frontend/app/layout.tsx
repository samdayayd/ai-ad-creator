import type { Metadata } from "next";
import { Orbitron } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { AuthProvider } from "@/lib/auth";
import { LanguageProvider } from "@/lib/LanguageProvider";

const orbitron = Orbitron({ subsets: ["latin"], weight: ["600", "700", "800"], variable: "--font-display" });

export const metadata: Metadata = {
  title: "AdStorm Studio",
  description: "Paste a product URL, get a full ad set for every channel — one click.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={orbitron.variable}>
      <body className="flex min-h-screen flex-col">
        <LanguageProvider>
          <AuthProvider>
            <Navbar />
            <main className="mx-auto w-full max-w-4xl flex-1 px-4 pb-16 pt-8">{children}</main>
            <Footer />
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
