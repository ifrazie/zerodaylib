import './globals.css';

import { Inter } from 'next/font/google';
import Sidebar from './Sidebar';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'Zero Day Librarian - Hackathon Demo',
  description: 'Zero Day Librarian Hackathon Demo Dashboard',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Sidebar>{children}</Sidebar>
      </body>
    </html>
  );
}
