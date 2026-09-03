import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "PayWall.ai | AI Agent Payment Guard",
  description:
    "Real-time authorization and safety layer between AI agents and Razorpay. Verify intent, enforce policy, detect risk.",
  keywords: ["AI payments", "agent commerce", "razorpay", "fraud detection", "autonomous agents"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans bg-[#080c14] text-white antialiased`}>
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto bg-[#080c14]">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
