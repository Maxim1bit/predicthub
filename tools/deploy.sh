#!/bin/bash
# ============================================
# PredictHub — Deploy site to production
# Usage: bash tools/deploy.sh "commit message"
# ============================================

SITE_DIR="$(dirname "$0")/../site"
MSG="${1:-Content update $(date +%Y-%m-%d)}"

cd "$SITE_DIR" || exit 1

# Update sitemap dates
TODAY=$(date +%Y-%m-%d)
sed -i "s|<lastmod>[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}</lastmod>|<lastmod>${TODAY}</lastmod>|g" sitemap.xml 2>/dev/null

cd "$(dirname "$0")/.." || exit 1

git add -A
git diff --cached --quiet && echo "No changes to deploy." && exit 0
git commit -m "$MSG"
git push origin main

echo "✓ Deployed: $MSG"
echo "✓ Date: $(date)"
