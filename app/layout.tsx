import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ANATOMY ATLAS | 3D 인체 해부도",
  description: "골격, 근육, 내부 장기를 레이어와 단면으로 탐색하는 3D 인체 해부 뷰어.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="antialiased">{children}</body>
    </html>
  );
}
