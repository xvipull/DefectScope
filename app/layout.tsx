import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DefectScope | Vision Quality Inspection',
  description: 'A human-in-the-loop visual inspection console.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
