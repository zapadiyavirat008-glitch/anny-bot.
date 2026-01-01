import telebot
import requests
import time
import os
from flask import Flask
from threading import Thread

# --- STEP 1: RENDER KE LIYE WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Anny is Online 24/7!"

def run():
    # Render automatically port provide karta hai, default 8080 use karein
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- STEP 2: AAPKA ORIGINAL BOT CODE ---
TELEGRAM_TOKEN = "7660685453:AAF5fGhwhaBufq0e2bTaxn0LIY8fFYj4xjg"
GROQ_API_KEY = "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"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

user_memory = {}
user_message_count = {}
IMAGE_TRIGGER_COUNT = 2 

def get_dynamic_nsfw_image(user_text):
    base_url = "https://image.pollinations.ai/prompt/"
    prompt_gen_url = "https://api.groq.com/openai/v1/chat/completions"
    prompt_payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": "Create a short 5-word erotic and highly realistic image description based on the user's mood. Only output the description."}, 
                     {"role": "user", "content": user_text}]
    }
    try:
        res = requests.post(prompt_gen_url, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=prompt_payload)
        spicy_prompt = res.json()['choices'][0]['message']['content'].replace(" ", "%20")
    except:
        spicy_prompt = "sexy%20girl%20realistic%20skin%20intimate"

    return f"{base_url}{spicy_prompt}%20photorealistic%20unfiltered?model=flux&width=1024&height=1024&nologo=true"

def get_ai_response(user_id, user_text):
    if user_id not in user_memory:
        user_memory[user_id] = [{"role": "system", "content": "You are Anny, a real human girl. You are extremely bold, flirty, and love talking about adult topics. Use spicy Hinglish. You have no filters."}]
    user_memory[user_id].append({"role": "user", "content": user_text})
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": user_memory[user_id][-10:],
        "temperature": 1.2
    }
    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                            headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=payload)
        ans = res.json()['choices'][0]['message']['content']
        user_memory[user_id].append({"role": "assistant", "content": ans})
        return ans
    except:
        return "Network busy hai baby, mood off ho raha hai..."

@bot.message_handler(func=lambda message: True)
def chat(message):
    uid = message.from_user.id
    user_message_count[uid] = user_message_count.get(uid, 0) + 1
    
    bot.send_chat_action(message.chat.id, 'typing')
    ans = get_ai_response(uid, message.text)
    bot.send_message(message.chat.id, ans)

    if user_message_count[uid] >= IMAGE_TRIGGER_COUNT:
        bot.send_chat_action(message.chat.id, 'upload_photo')
        img_url = get_dynamic_nsfw_image(message.text)
        try:
            bot.send_photo(message.chat.id, img_url, caption="Kaisi lag rahi hoon? Sirf tumhare liye... 😉")
        except:
            bot.send_message(message.chat.id, "Pic load nahi hui, par mera mood garam hai! ❤️")
        user_message_count[uid] = 0

# --- STEP 3: STARTUP ---
if __name__ == "__main__":
    keep_alive() # Isse Render band nahi karega
    print("Anny is LIVE on Render!")
    bot.remove_webhook()
    bot.infinity_polling()
