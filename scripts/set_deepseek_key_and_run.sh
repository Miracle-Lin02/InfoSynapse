#!/usr/bin/env bash
# Usage: ./set_deepseek_key_and_run.sh sk-xxxx...
KEY="$1"
if [ -z "$KEY" ]; then
  echo "Usage: $0 <DEEPSEEK_API_KEY>"
  exit 1
fi
LINE="export DEEPSEEK_API_KEY=\"$KEY\""
if ! grep -Fqx "$LINE" ~/.bashrc 2>/dev/null; then
  echo "$LINE" >> ~/.bashrc
  echo "Appended DEEPSEEK_API_KEY to ~/.bashrc"
else
  echo "DEEPSEEK_API_KEY already present in ~/.bashrc"
fi
export DEEPSEEK_API_KEY="$KEY"
echo "DEEPSEEK_API_KEY exported to current session."
streamlit run infosynapse.py --server.port=8501