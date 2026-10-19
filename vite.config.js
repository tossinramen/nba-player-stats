import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const BOARD = fileURLToPath(new URL("./public/board.json", import.meta.url)).toLowerCase();

// Reload open tabs when `npm run update` / `python update.py` writes new data.
function boardReload() {
  return {
    name: "board-reload",
    configureServer(server) {
      server.watcher.add(BOARD);
      const onChange = file => {
        if (path.resolve(file).toLowerCase() === BOARD) server.ws.send({ type: "full-reload" });
      };
      server.watcher.on("add", onChange);
      server.watcher.on("change", onChange);
    },
  };
}

export default defineConfig({
  plugins: [react(), boardReload()],
  server: {
    watch: { ignored: ["**/data/**", "**/nbaprops/**", "**/__pycache__/**"] },
  },
});
