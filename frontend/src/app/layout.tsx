import './globals.css';

import { Inter, JetBrains_Mono } from 'next/font/google';
import Sidebar from './Sidebar';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains-mono',
  display: 'swap',
});

export const metadata = {
  title: 'Zero Day Librarian',
  description: 'Multi-agent vulnerability management with governed, auditable decisions.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body>
        <Sidebar>{children}</Sidebar>
      </body>
    </html>
  );
}
