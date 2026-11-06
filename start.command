#!/bin/zsh
set -e
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/uvicorn || ! -f frontend/out/index.html ]]; then
  echo 'READMEの起動手順でPythonパッケージのインストールと画面のビルドを行ってください。'
  read '?Enterキーで終了'
  exit 1
fi
echo 'Enterprise AI Helpdesk: http://127.0.0.1:8765'
echo '終了するには Control+C を押してください。'
exec .venv/bin/uvicorn helpdesk.main:app --app-dir backend --host 127.0.0.1 --port 8765 --no-access-log
