import resolve from "@rollup/plugin-node-resolve";
import terser from "@rollup/plugin-terser";
import typescript from "@rollup/plugin-typescript";

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
    ],
};
