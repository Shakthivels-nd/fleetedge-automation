#!/bin/bash
# ------------------------------
# Start local HTTP server to serve Allure HTML report and open in browser
# ------------------------------    

# --- Find project root (one level above this script) ---
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="$PROJECT_DIR/reports/allure-results"
REPORT_DIR="$PROJECT_DIR/reports/allure-report"
PORT=8080

echo "Starting local HTTP server on port $PORT..."
echo "Opening ${REPORT_DIR} in browser..."
# Use Python 3 built-in server if available
if command -v python3 >/dev/null 2>&1; then
    cd "$REPORT_DIR"
    python3 -m http.server "$PORT" >/dev/null 2>&1 &
    SERVER_PID=$!
elif command -v python >/dev/null 2>&1; then
    cd "$REPORT_DIR"
    python -m SimpleHTTPServer "$PORT" >/dev/null 2>&1 &
    SERVER_PID=$!
else
    echo "No Python installed. Cannot start HTTP server."
    exit 1
fi

URL="http://localhost:$PORT"
echo "Opening report at $URL"

case "$(uname)" in
  Darwin*) open "$URL" ;;        # macOS
  Linux*) xdg-open "$URL" ;;     # Linux
  CYGWIN*|MINGW*|MSYS*) start "$URL" ;;  # Windows Git Bash
  *) echo "Please open $URL manually." ;;
esac

# Keep the server running until Ctrl+C
echo "Press Ctrl+C to stop the server..."
wait $SERVER_PID