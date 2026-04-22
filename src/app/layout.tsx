import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ZECT — Engineering Delivery Control Tower",
  description:
    "AI-governed engineering productivity platform for planning, coding, review, and deployment readiness.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 text-slate-900 antialiased`}>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 p-6 md:p-8 overflow-x-hidden">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
