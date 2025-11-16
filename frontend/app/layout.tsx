import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { ClassificationProvider } from "@/lib/context/classification-context";

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
      <body className=  {  `${inter.className} min-h-screen bg-slate-950 text-slate-200`  }  >
        <Providers>
          <ClassificationProvider>
            {children}
          </ClassificationProvider>
        </Providers>
      </body>
    </html>
  );
}
