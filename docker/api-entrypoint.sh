#!/bin/sh
# Warms the two artefacts the API reads but does not build on demand: the vector index
# and the scraped notice cache. Both live on volumes, so this is a first-run cost.
# Neither is fatal -- retrieval degrades to no context, and notices to an empty feed --
# so a cold or unreachable Ollama delays good answers rather than blocking startup.
set -e

wait_for_ollama() {
    url="${OLLAMA_BASE_URL:-http://localhost:11434}"
    i=0
    while [ "$i" -lt 60 ]; do
        if python -c "import sys,urllib.request; urllib.request.urlopen('$url/api/tags', timeout=2)" 2>/dev/null; then
            return 0
        fi
        i=$((i + 1))
        sleep 2
    done
    echo "warn: no Ollama at $url after 120s." >&2
    echo "      On Linux, Ollama listens on 127.0.0.1 by default, which a container" >&2
    echo "      cannot reach. Either bind it to all interfaces --" >&2
    echo "        sudo systemctl edit ollama   # Environment=\"OLLAMA_HOST=0.0.0.0\"" >&2
    echo "      -- or run it in a container with compose.ollama.yaml. See README." >&2
    return 1
}

if [ ! -f /app/.chroma/chroma.sqlite3 ]; then
    echo "no vector index found, building it (first run only)..."
    wait_for_ollama && ioe-index || echo "warn: index build failed; answers will run without documents" >&2
fi

if [ ! -f /app/.cache/notices.json ]; then
    echo "no notice cache found, scraping..."
    ioe-notices || echo "warn: notice scrape failed; the notices feed will be empty" >&2
fi

exec "$@"
