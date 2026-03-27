from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "TechVJ running ✅"

# OPTIONAL: run bot in background
def start_bot():
    try:
        import bot  # your bot file
        bot.main()  # change if different function
    except Exception as e:
        print("Bot crashed:", e)

if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
    app.run(host="0.0.0.0", port=5000)
