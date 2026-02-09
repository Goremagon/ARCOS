#!/usr/bin/env bash

set -euo pipefail

rm -rf ARCOS-e2088b93 ARCOS-fe0ca8a1 ARCOS-6e3da4c3
rm -f test_email.py plotter.py backtester.py backtester_v3.py
rm -f deploy_cloud_run.sh

find . -type d -name "__pycache__" -prune -exec rm -rf {} +

echo "🧹 ARCOS Sanitization Complete. Repository optimized for v4.1."
