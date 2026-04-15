import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "ANTIRIPPER V2",
  description: "Governed NES Knowledge Base",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <nav className="border-b border-white/5 bg-black/50 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-8 h-16 flex items-center space-x-8">
            <a href="/" className="font-bold text-white text-xl tracking-tighter">ANTIRIPPER<span className="text-purple-500">V2</span></a>
            <div className="space-x-6 text-sm font-medium text-gray-300">
              <a href="/games" className="hover:text-emerald-400 transition-colors">Games</a>
              <a href="/drivers" className="hover:text-indigo-400 transition-colors">Drivers</a>
              <a href="/agent-logs" className="hover:text-rose-400 transition-colors">Governance Logs</a>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
