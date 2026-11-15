import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "쇼츠 공장 — AI 쇼츠 대본·자막·썸네일 생성기",
  description: "주제만 입력하면 유튜브 쇼츠 대본·SRT 자막·썸네일 문구를 한 번에 생성합니다.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
