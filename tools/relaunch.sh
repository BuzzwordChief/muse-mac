#!/bin/zsh
# Restart bin/serve.sh with the env vars given on the command line and wait until healthy.
#   tools/relaunch.sh SPEC=none
#   tools/relaunch.sh DRAFT_N=7 KV=q8_0
ROOT=${0:A:h:h}
pkill -f llama-server 2>/dev/null; sleep 2
env "$@" nohup $ROOT/bin/serve.sh > $ROOT/logs/server.log 2>&1 &
for i in {1..120}; do
  [[ $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:${PORT:-8080}/health) == 200 ]] && { echo "up after ${i}x2s: $*"; exit 0; }
  sleep 2
done
echo "server did not come up"; tail -20 $ROOT/logs/server.log; exit 1
