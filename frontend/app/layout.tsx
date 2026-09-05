import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "PayWall.ai — AI Agent Payment Guard",
  description:
    "The authorization and safety layer between AI agents and Razorpay. Verify intent, enforce policy, detect risk, grow revenue.",
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
        {children}
      </body>
    </html>
  );
}
