#!/bin/sh
# TeraGrant Keep-Alive Heartbeat for Android (Termux / Tasker / Cron)
# Pings https://teragrant-agent.onrender.com every 10 minutes to prevent Render free-tier from sleeping.

INTERVAL=600
URL="https://teragrant-agent.onrender.com/healthz"
FALLBACK_URL="https://teragrant-agent.onrender.com/"

echo "==============================================="
echo " TeraGrant Render Keep-Alive (Android/Device) "
echo " Target: $URL"
echo " Interval: Every $(($INTERVAL / 60)) minutes"
echo "==============================================="

while true; do
  DATE=$(date '+%Y-%m-%d %H:%M:%S')
  CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$URL")
  
  # Fallback to root if healthz is not deployed yet
  if [ "$CODE" -eq 404 ]; then
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 30 "$FALLBACK_URL")
  fi

  if [ "$CODE" -eq 200 ]; then
    echo "[$DATE] Ping SUCCESS -> HTTP $CODE (Instance is awake!)"
  else
    echo "[$DATE] Ping returned HTTP $CODE (Waking up...)"
  fi

  sleep $INTERVAL
done
