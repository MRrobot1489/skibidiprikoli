cd ~
sed -i 's/cloudflared tunnel --url/cloudflared tunnel --protocol http2 --url/' start_server.sh
grep -n cloudflared start_server.sh   # проверь, что флаг добавился
pkill cloudflared
rm -f ~/server/cloudflared.log
bash start_server.sh
