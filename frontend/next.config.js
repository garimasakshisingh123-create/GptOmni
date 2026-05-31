/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow images from google.com for favicons
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'www.google.com',
        pathname: '/s2/favicons/**',
      },
    ],
  },
};

module.exports = nextConfig;
