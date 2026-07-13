/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",              // lean runtime image (PLAYBOOK §6)
  transpilePackages: ["@ringback/ui"],
  reactStrictMode: true,
};

module.exports = nextConfig;
