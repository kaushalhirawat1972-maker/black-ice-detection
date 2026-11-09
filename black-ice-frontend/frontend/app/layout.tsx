import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'BLACK ICE DETECTION — Road Perception Intelligence',
  description:
    'Multi-sensor black ice detection dashboard fusing 1080p RGB vision, MLX90640 thermal screening and 2D LiDAR specular dropout analysis in real time.',
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#07172c',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
