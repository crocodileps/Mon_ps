import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { MobileNav } from "@/components/layout/mobile-nav";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Mon_PS - Dashboard Quantitatif",
  description: "Système de trading quantitatif pour paris sportifs",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className="dark">
      <body className={`${inter.className} min-h-screen bg-slate-950 text-slate-200`}>
        <Providers>
          <div className="flex h-screen w-full bg-slate-950 text-slate-200 overflow-hidden">
            {/* Sidebar Desktop */}
            <Sidebar />

            {/* Main Content */}
            <main className="flex-1 flex flex-col overflow-y-auto">
              <Header />
              <div className="flex-1 p-4 md:p-8 pb-24 md:pb-8">
                {children}
              </div>
            </main>

            {/* Mobile Nav */}
            <MobileNav />
          </div>
        </Providers>
      </body>
    </html>
  );
}
