import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Enterprise AI Helpdesk | 社内ITサポート',
  description: '社内マニュアルの検索、出典の確認、問い合わせへの引き継ぎを体験できるポートフォリオ。架空データを使用。',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ja"><body>{children}</body></html>;
}
