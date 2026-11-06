pgrep -af cloudflared
grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' ~/server/cloudflared.log | sort -u
