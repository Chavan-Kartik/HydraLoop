/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // ESLint is not part of the install. Keeping it out of package.json avoids a
  // lockfile drift between Node 20 (CI/Vercel) and newer local Node versions on
  // optional WASM resolver packages. Typecheck still runs during `next build`.
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
