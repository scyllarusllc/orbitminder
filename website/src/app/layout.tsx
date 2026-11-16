import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OrbitMinder | Your projects. Always in sight.",
  description: "A personal project command center for tracking GitHub activity, follow-ups, and daily priorities.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
