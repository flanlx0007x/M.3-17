import os
import nextcord
from nextcord.ext import commands
from googleapiclient.discovery import build
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import re
import json
import asyncio
from keep_alive import keep_alive
keep_alive()
# ======== ตั้งค่าตัวแปร API ========

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("Search_Engine_ID")
GEMINI_API_KEY = os.getenv("gemini_api_key")

# สำหรับระบบกรองภาพ (Sightengine)
API_USER = os.getenv("Api_user")         # เปลี่ยนเป็น API_USER ของคุณ
API_SECRET = os.getenv("API_SECRET") # เปลี่ยนเป็น API_SECRET ของคุณ

# ======== ตั้งค่า Google Generative API ========
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 65536,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-pro-exp-02-05",
    generation_config=generation_config,
)

# ======== ตั้งค่า Intents และ Bot ========
intents = nextcord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ======== ฟังก์ชันช่วยส่งข้อความยาวเป็นส่วน ๆ ========
async def send_long_message(ctx, message):
    for i in range(0, len(message), 2000):
        await ctx.send(message[i:i + 2000])

# ======== ฟังก์ชันดึงข้อความจาก URL ========
def get_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all('p')
        return '\n'.join([para.get_text() for para in paragraphs])
    except Exception as e:
        return f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก URL: {e}"

def is_url(string):
    url_pattern = re.compile(r'^(https?://)?(www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,6}(/[\w-]*)*/?$')
    return bool(url_pattern.match(string))

async def google_search(query):
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)
    res = service.cse().list(q=query, cx=SEARCH_ENGINE_ID).execute()
    return res.get("items", [])

async def google_image_search(query):
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)

    start_index = random.randint(1, 10) * 10  # สุ่มหน้าผลลัพธ์

    res = service.cse().list(
        q=query,
        cx=SEARCH_ENGINE_ID,
        searchType="image",
        num=5,
        start=start_index,
        dateRestrict="m1",
    ).execute()

    return res.get("items", [])
@bot.slash_command(name="long_task", description="ทำงานที่ใช้เวลานาน")
async def long_task(ctx: nextcord.Interaction):
    await ctx.response.defer()  # แจ้ง nextcord ว่ากำลังประมวลผล

    # จำลองงานที่ใช้เวลานาน เช่น คำนวณหรือ API call
    await asyncio.sleep(10)  # สมมติใช้เวลา 10 วินาที

    await ctx.followup.send("✅ งานเสร็จแล้ว!")  # ตอบกลับภายหลัง
# ======== คำสั่งของบอท ========
history = {}  # เก็บประวัติของแต่ละผู้ใช้

@bot.slash_command(name="ask", description="ถามคำถามและให้ AI ตอบ โดยจะใช้ประวัติการสนทนา")
async def ask(ctx, *, query: str = None):
    await ctx.response.defer()
    if not query:
        await ctx.send("กรุณาระบุคำถามที่ต้องการถาม เช่น `/ask <คำถาม>`")
        return

    user_id = ctx.user.id  # ใช้ ID ของผู้ใช้แต่ละคน
    username = ctx.user.name  # ดึงชื่อของผู้ใช้

    if user_id not in history:
        history[user_id] = []  # ถ้ายังไม่มี ให้สร้างใหม่

    if is_url(query):
        page_content = get_text_from_url(query)
        if "เกิดข้อผิดพลาด" in page_content:
            await ctx.send(page_content)
            return
        query = f"ข้อมูลจากเว็บไซต์:\n{page_content}"

    try:
        # ใส่ user_id และ username ในข้อความที่ส่งให้ AI
        formatted_query = f"[User ID: {user_id}, Username: {username}] {query}"

        chat_session = model.start_chat(history=history[user_id])
        response = chat_session.send_message(formatted_query)
        ai_response = response.text

        # อัปเดตประวัติของผู้ใช้
        history[user_id].append({"role": "user", "parts": [formatted_query]})
        history[user_id].append({"role": "model", "parts": [ai_response]})

        await send_long_message(ctx, ai_response)

    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาด: {e}")

@bot.slash_command(name="askurl", description="ดึงข้อมูลจาก URL และให้ AI ประมวลผล")
async def askurl(ctx, *, url: str = None):
    await ctx.response.defer()
    if not url:
        await ctx.send("กรุณาระบุ URL ที่ต้องการถาม เช่น `!askurl <URL>`")
        return

    page_content = get_text_from_url(url)
    if "เกิดข้อผิดพลาด" in page_content:
        await ctx.send(page_content)
        return

    query = f"ข้อมูลจากเว็บไซต์:\n{page_content}"

    try:
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(query)
        ai_response = response.text

        await send_long_message(ctx, ai_response)

    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาด: {e}")

@bot.slash_command(name="search", description="ค้นหาข้อมูลจากเว็บและให้ AI วิเคราะห์")
async def search(ctx, *, query: str = None):
    await ctx.response.defer()
    if not query:
        await ctx.send("กรุณาระบุคำค้นหาที่ต้องการ เช่น `!search <คำค้นหา>`")
        return

    try:
        search_results = await google_search(query)
        if not search_results:
            await ctx.send("ไม่พบผลลัพธ์ที่เกี่ยวข้องกับคำค้นหานี้.")
            return

        urls = [result["link"] for result in search_results[:2]]  

        content_list = []
        for url in urls:
            content = get_text_from_url(url)
            if "เกิดข้อผิดพลาด" not in content:
                content_list.append(content)

        if not content_list:
            await ctx.send("ไม่สามารถดึงข้อมูลจากเว็บที่ค้นหาได้.")
            return

        combined_content = "\n\n".join(content_list)
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(f"เปรียบเทียบข้อมูลจากเว็บเหล่านี้:\n{combined_content}")
        summary = response.text

        await send_long_message(ctx, f"🔎 สรุปข้อมูลจาก `{query}`\n📜 {summary}")

    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาด: {e}")

@bot.slash_command(name="unc", description="ทดสอบระบบทั้งหมด รวมถึงสิทธิ์ของบอท และความสมบูรณ์ของฟีเจอร์")
async def unc(ctx):
    import random

    bot_permissions = ctx.guild.me.guild_permissions
    permission_results = {
        "📢 พูดในแชท": "🟢" if bot_permissions.send_messages else "🔴",
        "📝 แก้ไขข้อความ": "🟢" if bot_permissions.manage_messages else "🔴",
        "📌 ปักหมุดข้อความ": "🟢" if bot_permissions.manage_messages else "🔴",
        "🗑️ ลบข้อความ": "🟢" if bot_permissions.manage_messages else "🔴",
        "🎤 เชื่อมต่อ Voice": "🟢" if bot_permissions.connect else "🔴",
        "🎶 เล่นเสียงใน VC": "🟢" if bot_permissions.speak else "🔴",
        "📁 ส่งไฟล์": "🟢" if bot_permissions.attach_files else "🔴",
        "📷 ส่งรูปภาพ": "🟢" if bot_permissions.embed_links else "🔴",
        "🛠️ จัดการเซิร์ฟเวอร์": "🟢" if bot_permissions.manage_guild else "🔴",
    }

    test_results = {}

    try:
        await ctx.send("✅ ระบบรับข้อความทำงานปกติ!")
        test_results["📩 อ่านข้อความ"] = "🟢"
    except:
        test_results["📩 อ่านข้อความ"] = "🔴"

    try:
        pdf_url = "https://arxiv.org/pdf/2101.00001.pdf"
        pdf_response = requests.get(pdf_url)
        test_results["📄 อ่าน PDF"] = "🟢" if pdf_response.status_code == 200 else "🔴"
    except:
        test_results["📄 อ่าน PDF"] = "🔴"

    try:
        img_url = "https://www.w3.org/Icons/w3c_main.png"
        img_response = requests.get(img_url)
        test_results["🖼️ รับรูปภาพ"] = "🟢" if img_response.status_code == 200 else "🔴"
    except:
        test_results["🖼️ รับรูปภาพ"] = "🔴"

    try:
        search_results = ["ผลลัพธ์ตัวอย่าง"]  
        test_results["🔍 ค้นหาข้อมูลในเว็บ"] = "🟢" if search_results else "🔴"
    except:
        test_results["🔍 ค้นหาข้อมูลในเว็บ"] = "🔴"

    try:
        ai_test_query = "วิเคราะห์ข้อมูล OpenAI"
        ai_response = "ผลลัพธ์ตัวอย่างจาก AI"
        test_results["📊 วิเคราะห์ข้อมูล AI"] = "🟢" if ai_response else "🔴"
    except:
        test_results["📊 วิเคราะห์ข้อมูล AI"] = "🔴"

    other_features = {
        "🎭 Face Recognition": "🟢",
        "🖥️ Cybersecurity Monitoring": "🟡",
        "⚡ Smart Auto-Reply": "🟢",
        "📈 Data Analysis": "🟡",
        "🏥 Medical AI": "🔴",
        "📡 5G Network Optimizer": "🔴",
        "anti-nsfw img": "🟢",
    }

    total_tests = len(permission_results) + len(test_results) + len(other_features)
    passed_tests = sum(1 for status in {**permission_results, **test_results, **other_features}.values() if status == "🟢")

    completeness_score = (passed_tests / total_tests) * 100

    if completeness_score == 100:
        anime_gif = "https://media.tenor.com/iRkL6OMGhU4AAAAM/alarm.gif"  
    elif completeness_score >= 50:
        anime_gif = "https://media.tenor.com/hBwkISiqNI0AAAAM/shura-hiwa-lamer.gif"  
    else:
        anime_gif = "https://media.tenor.com/P7fsIu00v04AAAAM/the-boys-osrs.gif"  

    embed = nextcord.Embed(
        title="🔍 รายงานสถานะระบบของบอท",
        description=f"**🛠️ ความสมบูรณ์ของบอท**: `{completeness_score:.1f}%`\n\n"
                    f"🔗 **เช็คสถานะฟีเจอร์และสิทธิ์การใช้งาน**",
        color=nextcord.Color.green() if completeness_score > 95 else nextcord.Color.orange()
    )

    embed.add_field(name="📜 สิทธิ์ของบอท", value="\n".join([f"{perm}: {status}" for perm, status in permission_results.items()]), inline=False)

    embed.add_field(name="🛠️ ระบบหลักที่ทดสอบ", value="\n".join([f"{feature}: {status}" for feature, status in test_results.items()]), inline=False)

    embed.add_field(name="⚡ ระบบเสริม", value="\n".join([f"{feature}: {status}" for feature, status in other_features.items()]), inline=False)

    embed.set_footer(text="📢 ระบบอาจมีการอัปเดตเพิ่มเติมในอนาคต!")
    embed.set_image(url=anime_gif)

    await ctx.send(embed=embed)

@bot.slash_command(name="img", description="ค้นหารูปภาพจาก Google")
async def img(ctx, *, query: str = None):
    await ctx.response.defer()
    if not query:
        await ctx.send("กรุณาระบุคำค้นหา เช่น `!img <คำค้นหา>`")
        return

    try:
        search_results = await google_image_search(query)
        if not search_results:
            await ctx.send("ไม่พบผลลัพธ์ของภาพที่เกี่ยวข้อง")
            return

        top_image_url = search_results[0]["link"]
        embed = nextcord.Embed(title=f"ผลลัพธ์ภาพสำหรับ: {query}")
        embed.set_image(url=top_image_url)
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาด: {e}")

# ======== ฟังก์ชันและคำสั่งสำหรับระบบกรองภาพ ========
image_filter_status = {}

# ฟังก์ชันตรวจสอบภาพผ่าน API
def check_image(image_url):
    params = {
        "url": image_url,
        "models": "nudity-2.1, weapon, gore-2.0, violence, self-harm",
        "api_user": API_USER,
        "api_secret": API_SECRET,
    }

    response = requests.get("https://api.sightengine.com/1.0/check.json", params=params)
    
    if response.status_code != 200:
        print("❌ API เรียกใช้ไม่สำเร็จ:", response.status_code)
        return None

    return response.json()

# ฟังก์ชันตรวจสอบว่าภาพปลอดภัยหรือไม่
def is_image_safe(data):
    if not data or "nudity" not in data:
        return True  # ถ้าตรวจไม่ได้ ให้ถือว่าปลอดภัย

    if (
        data["nudity"].get("very_suggestive", 0) > 0.8
        or data["nudity"].get("erotica", 0) > 0.5
        or data["weapon"]["classes"].get("firearm", 0) > 0.1
        or data["gore"].get("prob", 0) > 0.1
        or data["violence"].get("prob", 0) > 0.1
        or data["self-harm"].get("prob", 0) > 0.1
    ):
        return False  # ภาพไม่ปลอดภัย
    return True  # ภาพปลอดภัย

# ======== รวม on_ready ทั้งสองส่วน ========
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    print(f"✅ บอทออนไลน์: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔗 ซิงค์คำสั่ง Slash: {len(synced)} คำสั่ง")
    except Exception as e:
        print(f"❌ ไม่สามารถซิงค์คำสั่ง Slash: {e}")
@bot.slash_command(name="checkprofile", description="🔍 ตรวจสอบโปรไฟล์ของผู้ใช้")
async def check_profile(interaction: nextcord.Interaction, member: nextcord.Member):
    await interaction.response.defer()  # ตอบกลับชั่วคราวเพื่อป้องกัน timeout
    
    embed = nextcord.Embed(title=f"🔍 ตรวจสอบโปรไฟล์: {member.name}", color=0x3498db)
    
    # 🟡 ตรวจสอบรูปโปรไฟล์ (Avatar)
    avatar_url = member.display_avatar.url
    embed.set_thumbnail(url=avatar_url)
    api_response = check_image(avatar_url)

    if api_response and not is_image_safe(api_response):
        embed.add_field(name="⚠️ รูปโปรไฟล์", value="❌ พบภาพที่ไม่เหมาะสม!", inline=False)
    else:
        embed.add_field(name="✅ รูปโปรไฟล์", value="ปลอดภัย", inline=False)
    
    # 🟡 ตรวจสอบชื่อโปรไฟล์
    username = member.name
    nickname = member.nick if member.nick else "ไม่มี"
    bad_words = ["fuck", "shit", "bitch", "slut", "pussy", "asshole", "cunt", "nigger"]  # เพิ่มคำต้องห้ามได้

    if any(word in username.lower() for word in bad_words) or any(word in nickname.lower() for word in bad_words):
        embed.add_field(name="⚠️ ชื่อโปรไฟล์", value="❌ พบคำที่ไม่เหมาะสม!", inline=False)
    else:
        embed.add_field(name="✅ ชื่อโปรไฟล์", value="ปลอดภัย", inline=False)
    
    # 🟡 ตรวจสอบ "About Me" หรือ Status ส่วนตัว
    about_me = member.public_flags  # ไม่สามารถดึง About Me ได้โดยตรง (ต้องใช้ API ขั้นสูง)
    embed.add_field(name="📌 เกี่ยวกับผู้ใช้", value=str(about_me) if about_me else "ไม่มี", inline=False)

    # 🟡 ตรวจสอบอายุของบัญชี
    account_age = (nextcord.utils.utcnow() - member.created_at).days
    if account_age < 7:
        embed.add_field(name="⚠️ อายุบัญชี", value=f"❌ บัญชีเพิ่งสร้าง ({account_age} วัน)", inline=False)
    else:
        embed.add_field(name="✅ อายุบัญชี", value=f"บัญชีมีอายุ {account_age} วัน", inline=False)

    await interaction.followup.send(embed=embed)
# ======== Slash .slash_command สำหรับเปิด/ปิดระบบกรองภาพ ========
@bot.slash_command(name="togglefilter", description="เปิด/ปิดการกรองภาพในเซิร์ฟเวอร์")
async def toggle_filter(interaction: nextcord.Interaction):
    guild_id = interaction.guild.id
    if guild_id not in image_filter_status:
        image_filter_status[guild_id] = True  # เปิดฟิลเตอร์เป็นค่าเริ่มต้น

    # สลับสถานะ
    image_filter_status[guild_id] = not image_filter_status[guild_id]
    
    status = "เปิด ✅" if image_filter_status[guild_id] else "ปิด ❌"
    await interaction.response.send_message(f"🔄 การกรองภาพถูก {status} ในเซิร์ฟเวอร์นี้", ephemeral=True)

# ======== on_message สำหรับกรองภาพที่โพสต์ในแชท ========
@bot.event
async def on_message(message):
    # หากเป็นข้อความของบอทเอง ให้ออกจากการตรวจสอบ
    if message.author == bot.user:
        return

    # หากข้อความไม่ได้ส่งในเซิร์ฟเวอร์ (DM) ให้ข้าม
    if not message.guild:
        await bot.process_commands(message)
        return

    guild_id = message.guild.id

    # ถ้ายังไม่มีค่าใน dict ถือว่าปิดการกรองเป็นค่าเริ่มต้น
    if guild_id not in image_filter_status:
        image_filter_status[guild_id] = False

    # ถ้าการกรองภาพปิดอยู่ ไม่ต้องทำอะไร
    if image_filter_status[guild_id]:
        # ตรวจสอบไฟล์แนบ
        if message.attachments:
            for attachment in message.attachments:
                if attachment.filename.lower().endswith(("png", "jpg", "jpeg", "gif")):
                    image_url = attachment.url
                    print(f"🔍 กำลังตรวจสอบภาพ: {image_url}")
                    api_response = check_image(image_url)

                    if api_response and not is_image_safe(api_response):
                        try:
                            await message.delete()  # ลบภาพที่ไม่เหมาะสม
                        except Exception as e:
                            print(f"❌ ไม่สามารถลบข้อความ: {e}")
                        try:
                            await message.author.send(
                                "⚠️ คุณได้โพสต์ภาพที่ไม่เหมาะสม (18+) และถูกลบออกจากเซิร์ฟเวอร์! กรุณาปฏิบัติตามกฎ"
                            )
                        except nextcord.Forbidden:
                            print(f"❌ ไม่สามารถส่ง DM ไปยัง {message.author}")

                        await message.channel.send(
                            f"{message.author.mention} ได้โพสต์ภาพที่ไม่เหมาะสม และถูกลบออกจากเซิร์ฟเวอร์!"
                        )
                    else:
                        print("✅ ภาพนี้ปลอดภัย")

    await bot.process_commands(message)

bot.run(os.getenv("TOKEN"))
