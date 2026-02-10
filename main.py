import discord
import ollama
import re
from ddgs import DDGS

# --- CONFIGURATION ---
DISCORD_TOKEN = 'TOKEN HERE'
MODEL_NAME = 'deepseek-r1:14b'  # Or 'llama3' if you prefer

# A persona that encourages using the search data naturally
SYSTEM_PROMPT = """
SYSTEM PROMPT HERE
"""

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def perform_web_search(query):
    print(f"I'm looking up: {query}")
    try:
        # The new 'ddgs' library uses the same class name
        results = DDGS().text(query, max_results=3)
        
        if not results:
            return None
        
        summary = "SEARCH RESULTS:\n"
        for result in results:
            summary += f"- {result['title']}: {result['body']}\n"
        return summary
    except Exception as e:
        print(f"Search error: {e}")
        return None

def clean_thinking(text):
    # Removes the <think>...</think> blocks from DeepSeek models
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

@client.event
async def on_ready():
    print(f'{client.user} is Online and ready for you, Danny.')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            # Clean the prompt
            user_input = message.content.replace(f'<@{client.user.id}>', '').strip()
            
            final_prompt = user_input
            
            # --- THE SEARCH LOGIC ---
            # Triggers if you start the message with "search", "google", or "find"
            triggers = ('search', 'google', 'find', 'look up')
            if user_input.lower().startswith(triggers):
                # Isolate the thing we need to search for
                search_query = user_input
                for trigger in triggers:
                    search_query = search_query.replace(trigger, '', 1)
                
                # Get the data
                search_data = perform_web_search(search_query.strip())
                
                # If we found data, inject it into the prompt strictly
                if search_data:
                    final_prompt = f"{search_data}\n\nUser Question: {user_input}"
            # ------------------------

            try:
                # Generate response
                response = ollama.chat(
                    model=MODEL_NAME, 
                    messages=[
                        {'role': 'system', 'content': SYSTEM_PROMPT},
                        {'role': 'user', 'content': final_prompt},
                    ],
                    options={
                        'temperature': 0.7, # Good balance of factual + lively
						'top_k': 50,
                        'num_ctx': 4096
                    }
                )
                
                # Clean and Send
                raw_reply = response['message']['content']
                clean_reply = clean_thinking(raw_reply)
                
                # Discord 2000 char limit check
                if len(clean_reply) > 2000:
                    for i in range(0, len(clean_reply), 2000):
                        await message.channel.send(clean_reply[i:i+2000])
                else:
                    await message.channel.send(clean_reply)

            except Exception as e:
                print(f"Error: {e}")
                await message.channel.send("I'm having a little trouble connecting right now.")

client.run(DISCORD_TOKEN)
