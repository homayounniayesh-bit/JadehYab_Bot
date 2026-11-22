#!/data/data/com.termux/files/usr/bin/bash
# اجرای بات در پسزمینه (برای Termux / اندروید)
cd "$(dirname "$0")" || exit 1
mkdir -p logs

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

termux-wake-lock 2>/dev/null || true

if command -v tmux >/dev/null 2>&1; then
  tmux kill-session -t roadradar 2>/dev/null || true
  tmux new-session -d -s roadradar "cd '$PWD'; source .venv/bin/activate 2>/dev/null; python run.py 2>&1 | tee logs/bot.log"
  echo "✅ بات داخل tmux (Session: roadradar) اجرا شد."
  echo "   دیدن لاگ:  tmux attach -t roadradar"
  echo "   خارج شدن از لاگ بدون متوقف کردن: Ctrl+b سپس d"
  echo "   متوقف کردن: tmux kill-session -t roadradar"
else
  nohup python run.py > logs/bot.log 2>&1 &
  echo $! > logs/bot.pid
  echo "✅ بات در پسزمینه اجرا شد. PID: $(cat logs/bot.pid)"
  echo "   دیدن لاگ:  tail -f logs/bot.log"
  echo "   متوقف کردن: kill \$(cat logs/bot.pid)"
fi
