/**
 * Injects BACKEND_URL from env into frontend/public/config.js.
 * Run during Vercel build so the frontend uses the correct API URL.
 */
const fs = require("fs");
const path = require("path");

const backendUrl = process.env.BACKEND_URL || "";
const outDir = path.join(__dirname, "..", "frontend", "public");
const outPath = path.join(outDir, "config.js");
const content =
  "// Injected at build time from Vercel env BACKEND_URL\n" +
  "window.APP_CONFIG = window.APP_CONFIG || { BACKEND_URL: " +
  JSON.stringify(backendUrl) +
  " };\n";

try {
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(outPath, content, "utf8");
  console.log("Wrote config.js with BACKEND_URL:", backendUrl || "(empty, frontend will use default)");
} catch (err) {
  console.error("inject-backend-url.js error:", err.message);
  console.error("outPath:", outPath);
  process.exit(1);
}
