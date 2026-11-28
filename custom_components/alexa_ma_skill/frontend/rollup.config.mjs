import { readFileSync } from "node:fs";

import resolve from "@rollup/plugin-node-resolve";
import terser from "@rollup/plugin-terser";
import typescript from "@rollup/plugin-typescript";

// Lit is bundled into the panel. Keep the original BSD-3-Clause notice in the
// built artifact even though Terser removes comments from the minified code.
const litLicense = readFileSync(
    new URL("./node_modules/lit/LICENSE", import.meta.url),
    "utf8",
).trim();
const licenseBanner = `/*!\nLit 3.3.3\n\n${litLicense}\n*/`;

export default {
    input: "src/alexa-ma-panel.ts",
    output: {
        file: "dist/alexa-ma-panel.js",
        format: "es",
        sourcemap: false,
    },
    plugins: [
        resolve({ browser: true }),
        typescript({ tsconfig: "./tsconfig.json" }),
        terser({
            format: { comments: false },
            compress: { passes: 2 },
        }),
        {
            name: "license-banner",
            renderChunk(code) {
                return { code: `${licenseBanner}\n${code}`, map: null };
            },
        },
    ],
};
