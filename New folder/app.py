"""
╔══════════════════════════════════════════════════════════════════╗
║         Discord Icebreaker & Check-in Bot (Arabic)              ║
║         Built with discord.py v2.0+ | asyncio scheduler         ║
╚══════════════════════════════════════════════════════════════════╝

SETUP INSTRUCTIONS:
───────────────────
1. Install dependencies:
       pip install discord.py python-dotenv

2. Create a `.env` file in the same directory as this script:
       DISCORD_TOKEN=your_bot_token_here
       CHANNEL_ID=123456789012345678
       TIMEZONE=Africa/Cairo          # optional, defaults to UTC

3. Run the bot:
       python icebreaker_bot.py

HOW TO CUSTOMIZE:
─────────────────
• Time window  → change SEND_HOUR_MIN / SEND_HOUR_MAX below
• Messages/day → change MESSAGES_PER_DAY_MIN / MESSAGES_PER_DAY_MAX
• Questions    → add/edit entries in the QUESTIONS list
• Reactions    → edit the REACTION_EMOJIS list

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POLL SYSTEM — Two independent systems, each with its own schedule:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── INDIVIDUAL POLLS ──────────────────────────────────────────────
  Polls sent one per day, rotating through a saved list.

  /addpoll <args>                              Add a poll (Q | opt1 | opt2...)
  /listpolls                                   List all polls
  /deletepoll <number>                         Delete by number
  /setpolltime <HH:MM>                         Set daily send time
  /setpollchannel [#channel]                   Set target channel
  /testpoll                                    Send next poll now

── POLL PACKS ────────────────────────────────────────────────────
  A pack groups multiple polls that are ALL sent together (0.5 s apart).
  Packs rotate independently from individual polls.

  /addpack <Pack Name>                         Create a new empty pack
  /addpackpoll <args>                          Add a poll into a pack (Pack | Q | opt1...)
  /listpacks                                   List all packs + contents
  /deletepack <Pack Name>                      Delete an entire pack
  /deletepackpoll <args>                       Remove one poll from a pack (Pack | number)
  /setpacktime <HH:MM>                         Set daily pack send time
  /setpackchannel [#channel]                   Set pack target channel
  /testpack [Pack Name]                        Send a pack now (next in rotation
                                               if no name given)

── ACCOUNTABILITY ────────────────────────────────────────────────
  Tracks who voted today (individual + packs), sends you a DM report,
  then DMs each member a motivational or warning message.

  /setaccounttime <HH:MM>                      Set daily report time
  /setaccountowner                             Register yourself as report recipient
  /setwarnmsg <message>                        Set warning message for non-voters
  /setmotivemsg <message>                      Set motivation message for voters
  /accountstatus                               Show current settings
  /testaccount                                 Run accountability check now
"""

import asyncio
import json
import logging
import os
import platform
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError   # Python 3.9+

# ── Windows fix ───────────────────────────────────────────────────────────────
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# ─── Load environment variables ───────────────────────────────────────────────
load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
CHANNEL_ID: int    = int(os.getenv("CHANNEL_ID", "0"))
TZ_NAME: str       = os.getenv("TIMEZONE", "UTC")

if not DISCORD_TOKEN:
    raise EnvironmentError("DISCORD_TOKEN is missing. Add it to your .env file.")
if not CHANNEL_ID:
    raise EnvironmentError("CHANNEL_ID is missing. Add it to your .env file.")

# ─── Timezone ─────────────────────────────────────────────────────────────────
try:
    LOCAL_TZ = ZoneInfo(TZ_NAME)
except (ZoneInfoNotFoundError, KeyError):
    logging.warning(
        f"Timezone '{TZ_NAME}' not found. "
        "Install tzdata (pip install tzdata). Falling back to UTC."
    )
    LOCAL_TZ = timezone.utc

# ─── Icebreaker scheduler config ─────────────────────────────────────────────
SEND_HOUR_MIN: int = 9   # Earliest hour to send (noon)
SEND_HOUR_MAX: int = 19   # Latest hour to send   (9 PM)

# How many messages to send each day (chosen randomly within this range).
MESSAGES_PER_DAY_MIN: int = 1
MESSAGES_PER_DAY_MAX: int = 2

# ─── Reaction emojis ─────────────────────────────────────────────────────────
# These are added automatically to every bot message to encourage engagement.
REACTION_EMOJIS: list[str] = ["🌱", "👍", "💬", "❤️", "✨"]

# ─── Question bank (30 Arabic questions) ─────────────────────────────────────
# Mix of: mood check-ins 🌡️ | recovery reflections 🔄 | fun icebreakers 🎉
# To add a new question, simply append a new string to this list.
QUESTIONS: list[str] = [
    # 🌡️ 1. متابعة المزاج والطاقة (Mood & Energy Check-ins) — [15 سؤالاً]
    "🌡️ كيف تقيِّم يومك حتى الآن من 1 إلى 10؟ ولماذا اخترت هذا الرقم؟",
    "🌤️ لو وصفنا حالتك النفسية اليوم بظاهرة جوية (مشمس، غائم، ممطر...)؛ كيف سيكون الطقس؟",
    "🎨 لو يعبّر لون واحد عن مزاجك اليوم، ما اللون الذي ستختاره؟",
    "🔋 كم تبلغ نسبة طاقتك الآن؟ وما أكثر شيء شحنك أو استنزفك اليوم؟",
    "💭 ما الشيء الذي يستحوذ على الجزء الأكبر من تفكيرك حالياً؟",
    "🌊 كيف تجد هدوءك النفسي في أيامك المزدحمة؟",
    "🌱 ما التغيير الصغير في روتينك اليومي الذي تحسن به مزاجك؟",
    "☕ ما المشهد أو اللحظة البسيطة التي جعلت يومك أهدأ اليوم؟",
    "🍃 ما الشيء الذي يمنحك شعوراً بالراحة والسكينة بعد يوم طويل؟",
    "⏱️ لو اقتطعت 10 دقائق لنفسك الآن، كيف ستلقي بها عنك التعب؟",
    "🕯️ ما العادة البسيطة التي لو فعلتها اليوم تشعر أن يومك اكتمل؟",
    "💤 كيف تعتني بنفسك عندما تشعر أن طاقتك الإيجابية أوشكت على النفاد؟",
    "🌧️ هل تحب الأجواء الهادئة والممطرة أم تفضل الأيام المشمسة والمتحركة؟ ولماذا؟",
    "🪞 كلمة واحدة تعبر بها عن شعورك الداخلي في هذه اللحظة؟",
    "📌 ما المكان أو الركن المفضل لديك للجلوس والتفكير في هدوء؟",

    # 🔄 2. التعافي والنمو الشخصي (Growth & Recovery) — [25 سؤالاً]
    "🌱 ما التوفيق أو الإنجاز البسيط الذي يسرّه الله لك اليوم وترى فيه نعمة، مهما كان صغيراً؟",
    "🏆 ما أحدث صعوبة أو تحدٍّ استطعت تجاوزه اليوم، وحمدت الله على تيسيره؟",
    "🔄 ما أهم درس خرجت به من أشد اللحظات صعوبة في رحلتك؟",
    "🤝 من الشخص الذي وجدته سنداً لك في وقتك العصيب؟ وكيف كان أثره؟",
    "🛤️ ما الخطوة السديدة الوحيدة التي يمكنك خطوها اليوم لتقترب أكثر من هدفك؟",
    "🙏 ما النعمة التي تشعر بامتنان حقيقي لوجودها في حياتك اليوم ولم تكن تلتفت لها؟",
    "💪 ما الصفتان اللتان لمستهما في نفسك مؤخراً وتدعوانك للاستمرار والتطور؟",
    "🌊 ما استراتيجيتك الخاصة في التعامل مع الأيام الثقيلة والضغوطات؟",
    "🦋 ما أثر التغيير الإيجابي الذي تلمسه في سلوكك أو تفكيرك خلال الفترة الأخيرة؟",
    "🌙 لو أتيحت لك فرصة توجيه نصيحة لنفسك قبل عام من الآن، ماذا ستجيب؟",
    "📚 ما الدرس الذي تعلمته من خطأ سابق وجعلك أكثر حكمة اليوم؟",
    "🛡️ كيف تحمي نفسك وتفكيرك من الأفكار السلبية عند مرورك بلحظات فتور؟",
    "🎯 ما العادة الصالحة أو النافعة التي تسعى لتثبيتها في روتينك حالياً؟",
    "ما الذي يساعدك على النهوض والبدء من جديد عند الشعور بالإحباط؟",
    "🕊️ ما الذي يجعلك تشعر بالطمأنينة والرضا عن مسارك الحالي؟",
    "🤲 ما الدعاء أو الذكر الذي تجد فيه راحة قلبك عند ضيق الصدر؟",
    "🧠 كيف تتصرف عندما تجد نفسك متشتتاً بين عدة مهام في وقت واحد؟",
    "⏳ ما المهارة التي استثمرت فيها وقتك مؤخراً ولمست فائدتها؟",
    "ما المبدأ الذي تتمسك به وترى أنه يدلك على الطريق الصحيح دائماً؟",
    "💡 ما المفهوم الذي تغير فهمك له تماماً بعد تجربة معينة مررت بها؟",
    "🌿 ما الخطوة التي أدركت متأخراً أنها كانت خيراً لك رغم صعوبتها في البداية؟",
    "📖 ما العبارة أو النصيحة التي قرأتها يوماً وظلت حافزاً لك حتى الآن؟",
    "🔍 كيف تقيم قدرتك على إدارة وقتك وتحديد أولوياتك هذا الأسبوع؟",
    "🚀 ما الذي يساعدك على الاستمرار في السعي عندما يقل الشغف؟",
    "✨ ما العطاء أو المساعدة البسيطة التي قدمتها لأحدهم وشعرت ب أثرها في قلبك؟",

    # 🎯 3. أسئلة تفاعلية وخفيفة (Icebreakers & Daily Habits) — [25 سؤالاً]
    "☕ القهوة أم الشاي؟ ولماذا ترى أن اختيارك هو المفضل لديك دائماً؟",
    "🍕 لو أُجبرت على تناول وجبة واحدة يومياً لمدة شهر كامل، ماذا ستختار؟",
    "🌍 لو أتيحت لك فرصة السفر، أين ستذهب؟",
    "📚 ما آخر كتاب، مقال، أو درس نافع شاهدته وترك أثراً طيباً في نفسك؟",
    "🐾 هل تنحاز للقطط أم للكلاب؟ أم أن لديك اهتماماً بكائن آخر؟",
    "🌟 ما الإنجاز الهادئ الذي أتممته هذا الأسبوع بينك وبين نفسك دون أن تحدث به أحداً؟",
    "🎯 ما المهارة أو التجربة النافعة التي تطمح لتعلمها قبل نهاية هذا العام؟",
    "🍯 ما المشروب الدافيء أو الأكلة التي تعدل مزاجك فوراً في الشتاء أو عند التعب؟",
    "🖋️ هل تفضل كتابة مهامك وملاحظاتك بالورقة والقلم أم عبر التطبيقات الرقمية؟ ولماذا؟",
    "🌅 هل أنت شخص صباحي يستغل البكور، أم يزداد تركيزك ونشاطك في المساء؟",
    "🍳 ما الوجبة البسيطة التي تحب إعدادها بنفسك وتتقنها؟",
    "🎒 ما الشيء الذي لا يمكن أن تغادر المنزل أو تبدأ يومك بدونه؟",
    "🚶‍♂️ هل تفضل المشي الهادئ بمفردك للتفكير، أم التحدث مع صديق مقرب؟",
    "📖 ما نوع الكتب أو الموضوعات التي تستمتع بقراءتها أو البحث عنها في وقت فراغك؟",
    "🍎 ما العادة الصحية البسيطة التي تحاول الحفاظ عليها في غذائك أو يومك؟",
    "🎧 ما نوع المقاطع الصوتية النافعة (بودكاست/محاضرات) التي تحب الاستماع إليها أثناء التنقل؟",
    "🛋️ كيف تقضي وقت راحة مثالي بعد أسبوع حافل بالعمل أو الدراسة؟",
    "🗂️ هل تعتبر نفسك شخصاً مرتباً ومنظماً بطبعك، أم تتكيف مع الفوضى؟",
    "🛠️ ما أداتك أو تطبيقك المفضل على الموبايل الذي يسهل عليك تنظيم حياتك؟",
    "🚲 ما النشاط البدني أو الرياضي الذي تجد فيه تجديداً لنشاطك وحيويتك؟",
    "🧠 لو طلب منك تقديم درس أو شرح موضوع تقرأ عنه للآخرين، ما الموضوع الذي ستختاره؟",
    "🗣️ ما اللغة التي تتمنى تعلمها أو تطوير مستواك فيها مستقبلاً؟",
    "🌳 هل تفضل قضاء وقت الراحة في الأماكن المفتوحة والطبيعة، أم في الأماكن المغلقة؟",
    "✍️ لو أردت كتابة مقال قصير اليوم، ما العنوان الذي ستختاره له؟",
    "🧩 ما اللعبة الذهنية أو التحدي الفكري الذي تستمتع بحله في وقت فراغك؟",

    # 💬 4. نقاشات وتقارب عميق (Deep Reflection & Connection) — [20 سؤالاً]
    "🤔 ما الشيء الذي تتمنى لو يفهمه الآخرون عنك بوضوح أكبر؟",
    "💌 لو كتب سطر تذكيري لنفسك تقرأه بعد 5 سنوات، ماذا ستكتب فيه؟",
    "🌈 ما الموقف الصغير الذي رسم على وجهك ابتسامة صادقة هذا الأسبوع؟",
    "🧩 ما الجانب الهادئ في شخصيتك الذي تعتقد أن معظم الناس لا يلاحظونه؟",
    "🔑 ما الكلمة الوحيدة التي تختصر بها مرحلتك الحالية من الحياة؟ ولماذا؟",
    "🤍 ما الصفة التي تقدرها جداً في الصديق وتجعلك تطمئن إليه؟",
    "🤝 كيف تعبر عن امتنانك وتقديرك للأشخاص المقربين منك عندما يقفون بجانبك؟",
    "🕊️ ما الذي يعنيه لك مفهوم 'التسامح' وسعة الصدر في التعامل مع الآخرين؟",
    "🕯️ ما نصيحتك للتعامل مع لحظات سوء الفهم بين الأصدقاء؟",
    "💎 ما القيمة الأخلاقية التي تحرص على ألا تتنازل عنها مهما كانت الظروف؟",
    "👂 هل تجد نفسك مستماعاً جيداً للآخرين، أم تميل لتقديم الحلول فوراً؟",
    "📖 ما الموقف الذي جعلك تدرك أهمية الصبر وعظم عاقبته؟",
    "🌱 كيف تحافظ على روابط الأخوة والصداقة النافعة رغم شغل الحياة والاهتمامات؟",
    "🧭 ما الذي يمنحك شعوراً بالاتجاه الصحيح عندما تحتار بين خيارين؟",
    "⚖️ كيف توازن بين مساعدة الآخرين وبين إعطاء نفسك حقها من الراحة؟",
    "🛡️ ما الشيء الذي تعلمت أن تقول له 'لا' لحماية وقتك وصحتك النفسية؟",
    "🕯️ ما الكلمة الطيبة التي سمعتها من أحد وما زال أثرها يبعث الدفء في قلبك؟",
    "🍂 كيف تتعامل مع التغيرات المفاجئة في خططك اليومية دون أن تفقد هدوءك؟",
    "🌟 ما الذي يجعل المجتمع أو الجروب بيئة آمنة وملمومة بالنسبة لك؟",
    "📌 ما الأثر الطيب الذي تتمنى أن تتركه في حياة من حولك؟",

    # ⚡ 5. تحديات سريعة ونافعة (5-Minute Challenges) — [15 سؤالاً]
    "💧 تحدي المياه: قوم اشرب كوب ماء كبير الآن، وتعال اكتب تم",
    "🧹 ترتيب سريع: رتب شيئاً واحداً فقط حولك (مكتبك، السرير، أو ترتيب ملفات جهازك) واكتب تم",
    "🤲 تحدي الاستغفار: اذكر الله واستغفره 10 مرات في سرك، ثم اترك إيموجي 🌱 بالأسفل",
    "👀 تحدي راحة العين: انظر إلى مكان بعيد عن الشاشة لمدة 20 ثانية لإراحة عينيك، واكتب تم",
    "📝 تحدي الامتنان: اكتب في الشات 3 نعم بسيطة جداً حولك الآن تشكر الله عليها",
    "🚶‍♂️ تحدي الحركة: قم بالمشي لمدة 3 دقائق داخل الغرفة واعمل على تنشيط جسمك",
    "📱 تحدي الهدوء الرقمي: أغلق تنبيهات التطبيقات غير الضرورية لبعض الوقت لتقليل التشتت",
    "🍃 تحدي الهواء النقي: افتح النافذة واستنشق هواءً نقياً لبضع ثوانٍ لتجديد طاقتك",
    "🔕 تحدي التركيز: ضع هاتفك على وضع الصامت لمدة 15 دقيقة وأنجز فيها مهمة واحدة فقط",
    "📖 تحدي القراءة الصغير: اقرأ صفحة واحدة فقط من كتابك الحالي أو نص نافع وشاركنا بما استفدته",
    "🤝 تحدي الدعاء: ادعُ لأحد أصدقائك في الجروب أو معارفك بظهر الغيب بالخير والتوفيق",
    "🗃️ تحدي تنظيم الهاتف: احذف 5 صور أو ملفات قديمة لا تحتاجها لتخفيف الزحمة على جهازك",
    "🎧 تحدي الاستماع: استمع لمقطع قرآن بصوت ترحم به قلبك لمدة 5 دقائق",
    "🧘‍♂️ تحدي التنفس: خذ 3 أنفاس عميقة وهادئة (شهيق بطيء ثم زفير بطيء) لتهدئة ذهنك",
]

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("icebreaker_bot")

# ─── Bot setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True   # required to see guild members for accountability

class IcebreakerBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()
        log.info("Slash commands synced globally.")

bot = IcebreakerBot(command_prefix="!", intents=intents)


# ─── Question tracker ─────────────────────────────────────────────────────────
class QuestionTracker:
    def __init__(self, questions: list[str]) -> None:
        self._questions = questions.copy()
        self._used_indices: list[int] = []
        self._no_repeat_window: int = max(1, len(questions) // 3)

    def pick(self) -> str:
        available = [
            i for i in range(len(self._questions))
            if i not in self._used_indices[-self._no_repeat_window:]
        ]
        if not available:
            self._used_indices.clear()
            available = list(range(len(self._questions)))
        chosen_index = random.choice(available)
        self._used_indices.append(chosen_index)
        if len(self._used_indices) > self._no_repeat_window * 2:
            self._used_indices = self._used_indices[-self._no_repeat_window:]
        return self._questions[chosen_index]


tracker = QuestionTracker(QUESTIONS)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _now_local() -> datetime:
    return datetime.now(tz=LOCAL_TZ)


def _random_send_times_today() -> list[datetime]:
    count = random.randint(MESSAGES_PER_DAY_MIN, MESSAGES_PER_DAY_MAX)
    today = _now_local().date()
    total_minutes = (SEND_HOUR_MAX - SEND_HOUR_MIN) * 60
    if total_minutes < count:
        raise ValueError("Time window too narrow for the requested message count.")
    chosen_minutes = random.sample(range(total_minutes), count)
    times: list[datetime] = []
    for offset_minutes in chosen_minutes:
        hour   = SEND_HOUR_MIN + offset_minutes // 60
        minute = offset_minutes % 60
        send_dt = datetime(today.year, today.month, today.day,
                           hour, minute, tzinfo=LOCAL_TZ)
        times.append(send_dt)
    return sorted(times)


async def _send_question(channel: discord.TextChannel) -> None:
    question = tracker.pick()
    header = "━━━━━━━━━━━━━━━━━━━━━━━━\n💬 **سؤال اليوم** | Check-in\n━━━━━━━━━━━━━━━━━━━━━━━━"
    content = f"{header}\n\n{question}"
    try:
        message = await channel.send(content)
        log.info(f"Sent question to #{channel.name}: {question[:60]}…")
        for emoji in REACTION_EMOJIS:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException as e:
                log.warning(f"Could not add reaction {emoji}: {e}")
    except discord.Forbidden:
        log.error("Bot lacks permission to send messages in the target channel.")
    except discord.HTTPException as e:
        log.error(f"Failed to send message: {e}")


# ─── Daily icebreaker scheduler ───────────────────────────────────────────────
async def daily_scheduler() -> None:
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(CHANNEL_ID)
        except discord.NotFound:
            log.error(f"Channel {CHANNEL_ID} not found.")
            return
        except discord.Forbidden:
            log.error(f"Bot cannot access channel {CHANNEL_ID}.")
            return
    log.info(f"Icebreaker scheduler started. Targeting #{channel.name} | TZ: {TZ_NAME}")
    while not bot.is_closed():
        send_times = _random_send_times_today()
        log.info(
            f"Today's icebreaker schedule ({_now_local().date()}): "
            + ", ".join(t.strftime("%H:%M") for t in send_times)
        )
        for send_time in send_times:
            now = _now_local()
            delay = (send_time - now).total_seconds()
            if delay < 0:
                log.info(f"Skipping past time slot: {send_time.strftime('%H:%M')}")
                continue
            log.info(f"Next icebreaker in {delay / 3600:.1f} h at {send_time.strftime('%H:%M %Z')}")
            await asyncio.sleep(delay)
            await _send_question(channel)
        now = _now_local()
        tomorrow_midnight = datetime(
            now.year, now.month, now.day, tzinfo=LOCAL_TZ
        ) + timedelta(days=1, minutes=1)
        sleep_seconds = (tomorrow_midnight - _now_local()).total_seconds()
        log.info(f"Icebreaker: sleeping {sleep_seconds / 3600:.1f} h until tomorrow.")
        await asyncio.sleep(max(sleep_seconds, 1))


# ╔══════════════════════════════════════════════════════════════════╗
# ║           INDIVIDUAL POLL SYSTEM — نظام التصويت الفردي          ║
# ╚══════════════════════════════════════════════════════════════════╝

POLLS_FILE = "polls.json"
DEFAULT_POLL_HOUR:   int = 22
DEFAULT_POLL_MINUTE: int = 0


def _load_poll_data() -> dict:
    if os.path.exists(POLLS_FILE):
        try:
            with open(POLLS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            log.warning("polls.json corrupt, recreating.")
    return {
        "polls": [],
        "current_index": 0,
        "poll_hour": DEFAULT_POLL_HOUR,
        "poll_minute": DEFAULT_POLL_MINUTE,
        "poll_channel_id": None,
    }


def _save_poll_data(data: dict) -> None:
    with open(POLLS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def _send_daily_poll(channel: discord.TextChannel) -> None:
    data = _load_poll_data()
    polls = data.get("polls", [])
    if not polls:
        log.warning("No individual polls saved.")
        return
    idx = data["current_index"] % len(polls)
    poll_data = polls[idx]
    data["current_index"] = (idx + 1) % len(polls)
    _save_poll_data(data)

    poll = discord.Poll(
        question=poll_data["question"],
        duration=timedelta(hours=24),
        multiple=True,
    )
    for ans_text in poll_data["answers"]:
        poll.add_answer(text=ans_text)

    try:
        await channel.send(poll=poll)
        log.info(f"📊 Individual poll [{idx+1}/{len(polls)}]: {poll_data['question'][:50]}…")
    except discord.Forbidden:
        log.error("Bot lacks permission to send polls in the individual poll channel.")
    except discord.HTTPException as e:
        log.error(f"Failed to send individual poll: {e}")


async def daily_poll_scheduler() -> None:
    await bot.wait_until_ready()
    log.info("📊 Individual poll scheduler running — checking every 20 s...")
    last_sent_date = None
    while not bot.is_closed():
        data = _load_poll_data()
        poll_hour   = data["poll_hour"]
        poll_minute = data["poll_minute"]
        target_channel_id = data.get("poll_channel_id") or CHANNEL_ID
        now = _now_local()
        target_today = now.replace(hour=poll_hour, minute=poll_minute,
                                   second=0, microsecond=0)
        seconds_past_target = (now - target_today).total_seconds()
        if 0 <= seconds_past_target < 59 and now.date() != last_sent_date:
            channel = bot.get_channel(target_channel_id)
            if channel is None:
                try:
                    channel = await bot.fetch_channel(target_channel_id)
                except (discord.NotFound, discord.Forbidden) as e:
                    log.error(f"Individual poll channel error: {e}")
                    await asyncio.sleep(20)
                    continue
            await _send_daily_poll(channel)
            last_sent_date = now.date()
            log.info(f"📊 Individual poll sent for {last_sent_date}.")
        await asyncio.sleep(20)


# ─── Individual poll commands ─────────────────────────────────────────────────

@bot.tree.command(name="addpoll", description="إضافة تصويت فردي جديد")
@app_commands.describe(args="السؤال | الخيار 1 | الخيار 2 | ...")
async def add_poll(interaction: discord.Interaction, args: str):
    if not args or "|" not in args:
        await interaction.response.send_message(
            "❌ **صيغة خاطئة!**\n```\n/addpoll args:السؤال | الخيار 1 | الخيار 2\n```",
            ephemeral=True
        )
        return
    parts    = [p.strip() for p in args.split("|")]
    question = parts[0]
    answers  = parts[1:]
    if not question:
        await interaction.response.send_message("❌ السؤال فارغ!", ephemeral=True)
        return
    if len(answers) < 2:
        await interaction.response.send_message("❌ يجب خيارَيْن على الأقل.", ephemeral=True)
        return
    if len(answers) > 10:
        await interaction.response.send_message("❌ الحد الأقصى 10 خيارات.", ephemeral=True)
        return
    if any(len(a) > 55 for a in answers):
        await interaction.response.send_message("❌ الحد الأقصى لكل خيار 55 حرفاً.", ephemeral=True)
        return
    data = _load_poll_data()
    data["polls"].append({"question": question, "answers": answers})
    _save_poll_data(data)
    answers_preview = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(answers))
    await interaction.response.send_message(
        f"✅ **تمت إضافة التصويت #{len(data['polls'])} بنجاح!**\n\n"
        f"📊 **السؤال:** {question}\n**الخيارات:**\n{answers_preview}"
    )


@bot.tree.command(name="listpolls", description="عرض جميع التصويتات الفردية")
async def list_polls(interaction: discord.Interaction):
    data  = _load_poll_data()
    polls = data.get("polls", [])
    if not polls:
        await interaction.response.send_message(
            "📭 لا توجد تصويتات فردية.\nاستخدم الأمر `/addpoll` لإضافة واحد.",
            ephemeral=True
        )
        return
    current_idx = data["current_index"] % len(polls)
    lines = [
        f"📊 **التصويتات الفردية** ({len(polls)} تصويت)",
        f"⏰ وقت الإرسال: **{data['poll_hour']:02d}:{data['poll_minute']:02d}** ({TZ_NAME})",
        f"▶️ التصويت القادم: **#{current_idx + 1}**\n" + "─" * 35,
    ]
    for i, poll in enumerate(polls):
        marker = "▶️" if i == current_idx else f"{i+1}."
        lines.append(f"{marker} **{poll['question']}**")
        lines.append(f"   └ {' | '.join(poll['answers'])}")
    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(name="deletepoll", description="حذف تصويت فردي برقم")
@app_commands.describe(number="رقم التصويت المراد حذفه")
async def delete_poll(interaction: discord.Interaction, number: int):
    data  = _load_poll_data()
    polls = data.get("polls", [])
    if not polls:
        await interaction.response.send_message("📭 لا توجد تصويتات لحذفها.", ephemeral=True)
        return
    if number < 1 or number > len(polls):
        await interaction.response.send_message(f"❌ اختر رقماً بين 1 و {len(polls)}. استخدم `/listpolls`", ephemeral=True)
        return
    removed = polls.pop(number - 1)
    if data["current_index"] >= len(polls) and polls:
        data["current_index"] = 0
    _save_poll_data(data)
    await interaction.response.send_message(f"🗑️ تم حذف التصويت #{number}:\n> {removed['question']}\n\nتبقى **{len(polls)}** تصويت.")


@bot.tree.command(name="setpolltime", description="تغيير وقت الإرسال اليومي للتصويت الفردي")
@app_commands.describe(time_str="الوقت بصيغة HH:MM")
async def set_poll_time(interaction: discord.Interaction, time_str: str):
    if not time_str or ":" not in time_str:
        await interaction.response.send_message("❌ الصيغة: `/setpolltime HH:MM` — مثال: `/setpolltime 22:00`", ephemeral=True)
        return
    try:
        h, m = time_str.strip().split(":")
        hour, minute = int(h), int(m)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await interaction.response.send_message("❌ وقت غير صحيح. استخدم HH:MM مثل `22:00`", ephemeral=True)
        return
    data = _load_poll_data()
    data["poll_hour"]   = hour
    data["poll_minute"] = minute
    _save_poll_data(data)
    await interaction.response.send_message(
        f"✅ وقت التصويت الفردي → **{hour:02d}:{minute:02d}** ({TZ_NAME})\n"
        f"_(يُطبَّق في الدورة القادمة)_"
    )


@bot.tree.command(name="testpoll", description="إرسال التصويت الفردي القادم الآن للاختبار")
async def test_poll(interaction: discord.Interaction):
    data = _load_poll_data()
    cid  = data.get("poll_channel_id") or CHANNEL_ID
    channel = bot.get_channel(cid) or await bot.fetch_channel(cid)
    if not channel:
        try:
            channel = await bot.fetch_channel(cid)
        except discord.Forbidden:
            await interaction.response.send_message(
                f"Error: I do not have permission to access the channel with ID {cid}. Please check my permissions.",
                ephemeral=True
            )
            return
        except discord.NotFound:
            await interaction.response.send_message(
                f"Error: Could not find a channel with ID {cid}.",
                ephemeral=True
            )
            return
    if not data.get("polls"):
        await interaction.response.send_message("📭 لا توجد تصويتات! أضف تصويت باستخدام `/addpoll`", ephemeral=True)
        return
    await interaction.response.send_message("🚀 جاري إرسال التصويت للاختبار...", ephemeral=True)
    await _send_daily_poll(channel)


# ╔══════════════════════════════════════════════════════════════════╗
# ║              POLL PACK SYSTEM — نظام حزم التصويت                ║
# ║                                                                  ║
# ║  A pack = a named group of polls sent all at once (0.5 s apart) ║
# ║  Packs rotate independently from individual polls.              ║
# ╚══════════════════════════════════════════════════════════════════╝

PACKS_FILE = "poll_packs.json"
DEFAULT_PACK_HOUR:   int = 20
DEFAULT_PACK_MINUTE: int = 0
PACK_SEND_DELAY:   float = 0.5   # seconds between polls inside a pack


def _load_pack_data() -> dict:
    if os.path.exists(PACKS_FILE):
        try:
            with open(PACKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            log.warning("poll_packs.json corrupt, recreating.")
    return {
        "packs": [],
        "current_index": 0,
        "pack_hour": DEFAULT_PACK_HOUR,
        "pack_minute": DEFAULT_PACK_MINUTE,
        "pack_channel_id": None,
    }


def _save_pack_data(data: dict) -> None:
    with open(PACKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _find_pack(data: dict, name: str) -> tuple[int, dict | None]:
    name_lower = name.strip().lower()
    for i, pack in enumerate(data["packs"]):
        if pack["name"].lower() == name_lower:
            return i, pack
    return -1, None


async def _send_pack(channel: discord.TextChannel, pack: dict) -> None:
    polls = pack.get("polls", [])
    if not polls:
        log.warning(f"Pack '{pack['name']}' is empty, skipping.")
        return
    log.info(f"📦 Sending pack '{pack['name']}' ({len(polls)} polls) to #{channel.name}")
    for i, poll_data in enumerate(polls):
        poll = discord.Poll(
            question=poll_data["question"],
            duration=timedelta(hours=24),
            multiple=True,
        )
        for ans_text in poll_data["answers"]:
            poll.add_answer(text=ans_text)
        try:
            await channel.send(poll=poll)
            log.info(f"  └ Poll {i+1}/{len(polls)}: {poll_data['question'][:50]}…")
        except discord.Forbidden:
            log.error("Bot lacks permission to send polls in the pack channel.")
            return
        except discord.HTTPException as e:
            log.error(f"Failed to send pack poll {i+1}: {e}")
        if i < len(polls) - 1:
            await asyncio.sleep(PACK_SEND_DELAY)


async def _send_next_pack(channel: discord.TextChannel) -> None:
    data  = _load_pack_data()
    packs = data.get("packs", [])
    if not packs:
        log.warning("No poll packs saved.")
        return
    idx = data["current_index"] % len(packs)
    pack = packs[idx]
    data["current_index"] = (idx + 1) % len(packs)
    _save_pack_data(data)
    await _send_pack(channel, pack)


async def daily_pack_scheduler() -> None:
    await bot.wait_until_ready()
    log.info("📦 Poll pack scheduler running — checking every 20 s...")
    last_sent_date = None
    while not bot.is_closed():
        data = _load_pack_data()
        pack_hour   = data["pack_hour"]
        pack_minute = data["pack_minute"]
        target_channel_id = data.get("pack_channel_id") or CHANNEL_ID
        now = _now_local()
        target_today = now.replace(hour=pack_hour, minute=pack_minute,
                                   second=0, microsecond=0)
        seconds_past_target = (now - target_today).total_seconds()
        if 0 <= seconds_past_target < 59 and now.date() != last_sent_date:
            channel = bot.get_channel(target_channel_id)
            if channel is None:
                try:
                    channel = await bot.fetch_channel(target_channel_id)
                except (discord.NotFound, discord.Forbidden) as e:
                    log.error(f"Pack channel error: {e}")
                    await asyncio.sleep(20)
                    continue
            await _send_next_pack(channel)
            last_sent_date = now.date()
            log.info(f"📦 Pack sent for {last_sent_date}.")
        await asyncio.sleep(20)


# ─── Poll pack commands ───────────────────────────────────────────────────────

@bot.tree.command(name="addpack", description="إنشاء حزمة تصويت جديدة (فارغة)")
@app_commands.describe(name="اسم الحزمة")
async def add_pack(interaction: discord.Interaction, name: str):
    if not name:
        await interaction.response.send_message("❌ اكتب اسم الحزمة.", ephemeral=True)
        return
    data = _load_pack_data()
    idx, existing = _find_pack(data, name)
    if existing is not None:
        await interaction.response.send_message(f"❌ يوجد حزمة بالاسم **{existing['name']}** بالفعل.", ephemeral=True)
        return
    data["packs"].append({"name": name.strip(), "polls": []})
    _save_pack_data(data)
    await interaction.response.send_message(
        f"✅ **تم إنشاء الحزمة: {name.strip()}** (فارغة)\n\n"
        f"أضف تصويتاً إليها:\n"
        f"```\n/addpackpoll args:{name.strip()} | السؤال | خيار 1 | خيار 2\n```"
    )


@bot.tree.command(name="addpackpoll", description="إضافة تصويت داخل حزمة موجودة")
@app_commands.describe(args="اسم الحزمة | السؤال | الخيار 1 | الخيار 2 | ...")
async def add_pack_poll(interaction: discord.Interaction, args: str):
    if not args or "|" not in args:
        await interaction.response.send_message(
            "❌ **صيغة خاطئة!**\n"
            "```\n/addpackpoll args:اسم الحزمة | السؤال | خيار 1 | خيار 2\n```",
            ephemeral=True
        )
        return
    parts     = [p.strip() for p in args.split("|")]
    pack_name = parts[0]
    question  = parts[1] if len(parts) > 1 else ""
    answers   = parts[2:]
    if not pack_name:
        await interaction.response.send_message("❌ اكتب اسم الحزمة أولاً.", ephemeral=True)
        return
    if not question:
        await interaction.response.send_message("❌ السؤال فارغ.", ephemeral=True)
        return
    if len(answers) < 2:
        await interaction.response.send_message("❌ يجب خيارَيْن على الأقل.", ephemeral=True)
        return
    if len(answers) > 10:
        await interaction.response.send_message("❌ الحد الأقصى 10 خيارات.", ephemeral=True)
        return
    if any(len(a) > 55 for a in answers):
        await interaction.response.send_message("❌ الحد الأقصى لكل خيار 55 حرفاً.", ephemeral=True)
        return
    data = _load_pack_data()
    idx, pack = _find_pack(data, pack_name)
    if pack is None:
        await interaction.response.send_message(
            f"❌ لم أجد حزمة باسم **{pack_name}**.\n"
            f"أنشئها أولاً: `/addpack name:{pack_name}`\n"
            f"أو استعرض الحزم: `/listpacks`",
            ephemeral=True
        )
        return
    pack["polls"].append({"question": question, "answers": answers})
    _save_pack_data(data)
    poll_num = len(pack["polls"])
    answers_preview = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(answers))
    await interaction.response.send_message(
        f"✅ **تمت إضافة التصويت #{poll_num} إلى حزمة '{pack['name']}'**\n\n"
        f"📊 **السؤال:** {question}\n**الخيارات:**\n{answers_preview}"
    )


@bot.tree.command(name="listpacks", description="عرض جميع الحزم ومحتوياتها")
async def list_packs(interaction: discord.Interaction):
    data  = _load_pack_data()
    packs = data.get("packs", [])
    if not packs:
        await interaction.response.send_message(
            "📭 لا توجد حزم تصويت.\nأنشئ حزمة: `/addpack`",
            ephemeral=True
        )
        return
    current_idx = data["current_index"] % len(packs)
    lines = [
        f"📦 **حزم التصويت** ({len(packs)} حزمة)",
        f"⏰ وقت الإرسال: **{data['pack_hour']:02d}:{data['pack_minute']:02d}** ({TZ_NAME})",
        f"▶️ الحزمة القادمة: **{packs[current_idx]['name']}** (#{current_idx + 1})\n" + "─" * 35,
    ]
    for i, pack in enumerate(packs):
        marker = "▶️" if i == current_idx else f"{i+1}."
        poll_count = len(pack["polls"])
        lines.append(f"{marker} **{pack['name']}** — {poll_count} تصويت")
        for j, p in enumerate(pack["polls"]):
            lines.append(f"   {j+1}. {p['question']}")
            lines.append(f"      └ {' | '.join(p['answers'])}")
        lines.append("")
    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(name="deletepack", description="حذف حزمة كاملة بالاسم")
@app_commands.describe(name="اسم الحزمة المراد حذفها")
async def delete_pack(interaction: discord.Interaction, name: str):
    if not name:
        await interaction.response.send_message("❌ اكتب اسم الحزمة.", ephemeral=True)
        return
    data = _load_pack_data()
    idx, pack = _find_pack(data, name)
    if pack is None:
        await interaction.response.send_message(f"❌ لم أجد حزمة باسم **{name}**. استخدم `/listpacks`", ephemeral=True)
        return
    data["packs"].pop(idx)
    if data["current_index"] >= len(data["packs"]) and data["packs"]:
        data["current_index"] = 0
    _save_pack_data(data)
    await interaction.response.send_message(
        f"🗑️ تم حذف الحزمة **{pack['name']}** ({len(pack['polls'])} تصويت).\n"
        f"تبقى **{len(data['packs'])}** حزمة."
    )


@bot.tree.command(name="deletepackpoll", description="حذف تصويت واحد من داخل حزمة")
@app_commands.describe(args="اسم الحزمة | رقم التصويت")
async def delete_pack_poll(interaction: discord.Interaction, args: str):
    if not args or "|" not in args:
        await interaction.response.send_message(
            "❌ **صيغة خاطئة!**\nمثال: `/deletepackpoll args:حزمة الأسبوع | 2`",
            ephemeral=True
        )
        return
    parts     = [p.strip() for p in args.split("|", 1)]
    pack_name = parts[0]
    try:
        number = int(parts[1])
    except (IndexError, ValueError):
        await interaction.response.send_message("❌ الرقم غير صحيح.", ephemeral=True)
        return
    data = _load_pack_data()
    idx, pack = _find_pack(data, pack_name)
    if pack is None:
        await interaction.response.send_message(f"❌ لم أجد حزمة باسم **{pack_name}**. استخدم `/listpacks`", ephemeral=True)
        return
    polls = pack["polls"]
    if number < 1 or number > len(polls):
        await interaction.response.send_message(f"❌ اختر رقماً بين 1 و {len(polls)}.", ephemeral=True)
        return
    removed = polls.pop(number - 1)
    _save_pack_data(data)
    await interaction.response.send_message(
        f"🗑️ تم حذف التصويت #{number} من حزمة **{pack['name']}**:\n"
        f"> {removed['question']}\n\nتبقى **{len(polls)}** تصويت في الحزمة."
    )


@bot.tree.command(name="setpacktime", description="تغيير وقت إرسال الحزم اليومي")
@app_commands.describe(time_str="الوقت بصيغة HH:MM")
async def set_pack_time(interaction: discord.Interaction, time_str: str):
    if not time_str or ":" not in time_str:
        await interaction.response.send_message("❌ الصيغة: `/setpacktime HH:MM` — مثال: `/setpacktime 20:00`", ephemeral=True)
        return
    try:
        h, m = time_str.strip().split(":")
        hour, minute = int(h), int(m)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await interaction.response.send_message("❌ وقت غير صحيح.", ephemeral=True)
        return
    data = _load_pack_data()
    data["pack_hour"]   = hour
    data["pack_minute"] = minute
    _save_pack_data(data)
    await interaction.response.send_message(
        f"✅ وقت إرسال الحزم → **{hour:02d}:{minute:02d}** ({TZ_NAME})\n"
        f"_(يُطبَّق في الدورة القادمة)_"
    )


@bot.tree.command(name="setpackchannel", description="تحديد القناة التي سترسل فيها الحزم")
@app_commands.describe(channel="القناة المستهدفة (اتركها فارغة لمعرفة القناة الحالية)")
async def set_pack_channel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if channel is None:
        data = _load_pack_data()
        cid  = data.get("pack_channel_id") or CHANNEL_ID
        ch   = bot.get_channel(cid)
        await interaction.response.send_message(
            f"📍 قناة الحزم الحالية: {ch.mention if ch else cid}\n"
            "لتغييرها حدد القناة في الأمر `/setpackchannel`",
            ephemeral=True
        )
        return
    if interaction.guild and not channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.response.send_message(f"❌ البوت لا يملك صلاحية الإرسال في {channel.mention}", ephemeral=True)
        return
    data = _load_pack_data()
    data["pack_channel_id"] = channel.id
    _save_pack_data(data)
    await interaction.response.send_message(f"✅ قناة إرسال الحزم → {channel.mention}")


@bot.tree.command(name="testpack", description="إرسال حزمة الآن فوراً للاختبار")
@app_commands.describe(name="اسم الحزمة (اتركه فارغاً لإرسال الحزمة التالية)")
async def test_pack(interaction: discord.Interaction, name: str = None):
    data = _load_pack_data()
    if not data.get("packs"):
        await interaction.response.send_message(
            "📭 لا توجد حزم! أنشئ حزمة أولاً باستخدام `/addpack`",
            ephemeral=True
        )
        return
    target_channel_id = data.get("pack_channel_id") or CHANNEL_ID
    channel = bot.get_channel(target_channel_id) or await bot.fetch_channel(target_channel_id)
    await interaction.response.send_message("🚀 جاري إرسال الحزمة للاختبار...", ephemeral=True)
    if name:
        _, pack = _find_pack(data, name)
        if pack is None:
            await interaction.followup.send(f"❌ لم أجد حزمة باسم **{name}**. استخدم `/listpacks`", ephemeral=True)
            return
        await _send_pack(channel, pack)
    else:
        await _send_next_pack(channel)


# ╔══════════════════════════════════════════════════════════════════╗
# ║          ACCOUNTABILITY SYSTEM — نظام المتابعة والمحاسبة        ║
# ║                                                                  ║
# ║  يتابع من صوّت في تصويتات اليوم (فردية + حزم)                  ║
# ║  في وقت محدد يرسل لك على الخاص:                                ║
# ║    - قائمة الملتزمين + قائمة الغير ملتزمين                     ║
# ║  ثم يرسل لكل غير ملتزم رسالة تحذيرية                          ║
# ║  ويرسل لكل ملتزم رسالة تحفيزية                                 ║
# ║  بعدها يمسح بيانات اليوم من الذاكرة (voted_today.json)         ║
# ╚══════════════════════════════════════════════════════════════════╝

ACCOUNT_FILE     = "accountability.json"
VOTED_TODAY_FILE = "voted_today.json"

DEFAULT_ACCOUNT_HOUR:   int = 23
DEFAULT_ACCOUNT_MINUTE: int = 0


def _load_account_settings() -> dict:
    if os.path.exists(ACCOUNT_FILE):
        try:
            with open(ACCOUNT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            log.warning("accountability.json corrupt, recreating.")
    return {
        "account_hour":   DEFAULT_ACCOUNT_HOUR,
        "account_minute": DEFAULT_ACCOUNT_MINUTE,
        "owner_id":       None,
        "warn_message":   "⚠️ لاحظنا غيابك عن التصويت اليوم، نتمنى تكون بخير وننتظر مشاركتك غداً! 💙",
        "motive_message": "🌟 ما شاء الله! شكراً على التزامك ومشاركتك اليوم، استمر! 💪",
    }


def _save_account_settings(data: dict) -> None:
    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_voted_today() -> dict:
    if os.path.exists(VOTED_TODAY_FILE):
        try:
            with open(VOTED_TODAY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"voted_ids": [], "date": str(_now_local().date())}


def _save_voted_today(data: dict) -> None:
    with open(VOTED_TODAY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _clear_voted_today() -> None:
    """امسح قائمة المصوّتين بعد إرسال التقرير — يبقى الملف لكن القائمة فارغة."""
    _save_voted_today({"voted_ids": [], "date": str(_now_local().date())})
    log.info("🗑️ تم مسح بيانات التصويت اليومي من الذاكرة.")


# ─── تسجيل المصوّتين تلقائياً ────────────────────────────────────────────────

@bot.event
async def on_poll_vote_add(member: discord.Member, answer: discord.PollAnswer) -> None:
    """يُستدعى تلقائياً كلما صوّت شخص في أي poll أرسله البوت."""
    if member.bot:
        return
    data      = _load_voted_today()
    today_str = str(_now_local().date())
    if data.get("date") != today_str:
        data = {"voted_ids": [], "date": today_str}
    if member.id not in data["voted_ids"]:
        data["voted_ids"].append(member.id)
        _save_voted_today(data)
        log.info(f"✅ تسجيل تصويت: {member.display_name} ({member.id})")


# ─── منطق الجرد ──────────────────────────────────────────────────────────────

async def _run_accountability(guild: discord.Guild) -> None:
    settings   = _load_account_settings()
    voted_data = _load_voted_today()
    voted_ids  = set(voted_data.get("voted_ids", []))

    owner_id = settings.get("owner_id")
    if not owner_id:
        log.warning("accountability: لم يُحدَّد owner_id — استخدم /setaccountowner")
        return

    try:
        owner = await bot.fetch_user(owner_id)
    except discord.NotFound:
        log.error(f"accountability: لم أجد المستخدم {owner_id}")
        return

    # fetch_members guarantees a fresh complete list regardless of cache state
    all_members   = [m async for m in guild.fetch_members(limit=None) if not m.bot]
    committed     = [m for m in all_members if m.id in voted_ids]
    not_committed = [m for m in all_members if m.id not in voted_ids]

    committed_names     = "\n".join(f"  ✅ {m.display_name}" for m in committed)     or "  — لا أحد"
    not_committed_names = "\n".join(f"  ❌ {m.display_name}" for m in not_committed) or "  — لا أحد"

    report = (
        f"📋 **تقرير الجرد اليومي — {_now_local().strftime('%Y-%m-%d')}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ **الملتزمون ({len(committed)}):**\n{committed_names}\n\n"
        f"❌ **الغير ملتزمون ({len(not_committed)}):**\n{not_committed_names}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 المجموع: {len(all_members)} عضو | "
        f"نسبة الالتزام: {len(committed)/max(len(all_members),1)*100:.0f}%"
    )

    try:
        await owner.send(report)
        log.info(f"📋 تم إرسال تقرير الجرد للـ owner ({owner.name})")
    except discord.Forbidden:
        log.error("accountability: لا أستطيع إرسال رسائل خاصة للـ owner — افتح الـ DMs.")

    warn_msg   = settings.get("warn_message",   "")
    motive_msg = settings.get("motive_message", "")

    for member in not_committed:
        try:
            await member.send(warn_msg)
            await asyncio.sleep(0.5)
        except discord.Forbidden:
            log.warning(f"لا أستطيع مراسلة {member.display_name} (DM مغلق)")
        except discord.HTTPException as e:
            log.error(f"خطأ في إرسال تحذير لـ {member.display_name}: {e}")

    for member in committed:
        try:
            await member.send(motive_msg)
            await asyncio.sleep(0.5)
        except discord.Forbidden:
            log.warning(f"لا أستطيع مراسلة {member.display_name} (DM مغلق)")
        except discord.HTTPException as e:
            log.error(f"خطأ في إرسال تحفيز لـ {member.display_name}: {e}")

    _clear_voted_today()
    log.info("✅ انتهى الجرد اليومي.")


# ─── مُجدِّل الجرد اليومي ────────────────────────────────────────────────────

async def daily_accountability_scheduler() -> None:
    await bot.wait_until_ready()
    log.info("📋 مُجدِّل الجرد يعمل — يتحقق كل 20 ثانية...")
    last_sent_date = None
    while not bot.is_closed():
        settings       = _load_account_settings()
        account_hour   = settings["account_hour"]
        account_minute = settings["account_minute"]
        now            = _now_local()
        target_today   = now.replace(hour=account_hour, minute=account_minute,
                                     second=0, microsecond=0)
        seconds_past   = (now - target_today).total_seconds()
        if 0 <= seconds_past < 59 and now.date() != last_sent_date:
            if bot.guilds:
                await _run_accountability(bot.guilds[0])
                last_sent_date = now.date()
            else:
                log.error("accountability: البوت غير موجود في أي سيرفر.")
        await asyncio.sleep(20)


# ─── أوامر نظام المحاسبة (slash commands) ────────────────────────────────────

@bot.tree.command(name="setaccounttime", description="تحديد وقت إرسال تقرير الجرد اليومي")
@app_commands.describe(time_str="الوقت بصيغة HH:MM — مثال: 23:00")
async def set_account_time(interaction: discord.Interaction, time_str: str):
    if not time_str or ":" not in time_str:
        s = _load_account_settings()
        await interaction.response.send_message(
            f"❌ الصيغة: `/setaccounttime HH:MM`\n"
            f"⏰ الوقت الحالي: **{s['account_hour']:02d}:{s['account_minute']:02d}**",
            ephemeral=True
        )
        return
    try:
        h, m = time_str.strip().split(":")
        hour, minute = int(h), int(m)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await interaction.response.send_message("❌ وقت غير صحيح. استخدم HH:MM مثل `23:00`", ephemeral=True)
        return
    s = _load_account_settings()
    s["account_hour"]   = hour
    s["account_minute"] = minute
    _save_account_settings(s)
    await interaction.response.send_message(
        f"✅ وقت الجرد اليومي → **{hour:02d}:{minute:02d}** ({TZ_NAME})"
    )


@bot.tree.command(name="setaccountowner", description="سجّل نفسك كمستلم تقارير الجرد اليومي على الخاص")
async def set_account_owner(interaction: discord.Interaction):
    s = _load_account_settings()
    s["owner_id"] = interaction.user.id
    _save_account_settings(s)
    try:
        await interaction.user.send("✅ تم تسجيلك كمستلم تقارير الجرد اليومي. ستصلك التقارير هنا.")
        await interaction.response.send_message(
            f"✅ تم تسجيل **{interaction.user.display_name}** كمستلم للتقارير. تحقق من رسائلك الخاصة!",
            ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            f"✅ تم حفظ معرفك، لكن ⚠️ **رسائلك الخاصة مغلقة!**\n"
            f"افتح الـ DMs من إعدادات الخصوصية حتى يصلك التقرير.",
            ephemeral=True
        )


@bot.tree.command(name="setwarnmsg", description="تحديد الرسالة التي ترسل للغير ملتزمين")
@app_commands.describe(message="نص الرسالة التحذيرية")
async def set_warn_msg(interaction: discord.Interaction, message: str):
    if not message:
        s = _load_account_settings()
        await interaction.response.send_message(
            f"📝 رسالة الغير ملتزمين الحالية:\n> {s['warn_message']}",
            ephemeral=True
        )
        return
    s = _load_account_settings()
    s["warn_message"] = message
    _save_account_settings(s)
    await interaction.response.send_message(
        f"✅ تم حفظ رسالة الغير ملتزمين:\n> {message}",
        ephemeral=True
    )


@bot.tree.command(name="setmotivemsg", description="تحديد الرسالة التي ترسل للملتزمين")
@app_commands.describe(message="نص الرسالة التحفيزية")
async def set_motive_msg(interaction: discord.Interaction, message: str):
    if not message:
        s = _load_account_settings()
        await interaction.response.send_message(
            f"📝 رسالة الملتزمين الحالية:\n> {s['motive_message']}",
            ephemeral=True
        )
        return
    s = _load_account_settings()
    s["motive_message"] = message
    _save_account_settings(s)
    await interaction.response.send_message(
        f"✅ تم حفظ رسالة الملتزمين:\n> {message}",
        ephemeral=True
    )


@bot.tree.command(name="accountstatus", description="عرض إعدادات نظام الجرد الحالية")
async def account_status(interaction: discord.Interaction):
    s     = _load_account_settings()
    voted = _load_voted_today()
    owner = None
    if s.get("owner_id"):
        try:
            owner = await bot.fetch_user(s["owner_id"])
        except discord.NotFound:
            pass
    await interaction.response.send_message(
        f"📋 **إعدادات نظام الجرد**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ وقت التقرير: **{s['account_hour']:02d}:{s['account_minute']:02d}** ({TZ_NAME})\n"
        f"👤 مستلم التقرير: **{owner.display_name if owner else '❌ غير محدد'}**\n"
        f"📊 صوّتوا اليوم حتى الآن: **{len(voted['voted_ids'])}** عضو\n\n"
        f"⚠️ رسالة الغير ملتزمين:\n> {s['warn_message']}\n\n"
        f"🌟 رسالة الملتزمين:\n> {s['motive_message']}",
        ephemeral=True
    )


@bot.tree.command(name="testaccount", description="تشغيل الجرد فوراً للاختبار")
async def test_account(interaction: discord.Interaction):
    if not bot.guilds:
        await interaction.response.send_message("❌ البوت غير موجود في أي سيرفر.", ephemeral=True)
        return
    s = _load_account_settings()
    if not s.get("owner_id"):
        await interaction.response.send_message(
            "❌ لم يُحدَّد مستلم التقرير. استخدم `/setaccountowner` أولاً.",
            ephemeral=True
        )
        return
    await interaction.response.send_message("🚀 جاري تشغيل الجرد للاختبار...", ephemeral=True)
    await _run_accountability(bot.guilds[0])
    await interaction.followup.send("✅ انتهى الجرد التجريبي.", ephemeral=True)


# ╔══════════════════════════════════════════════════════════════════╗
# ║                     Events & Entry Point                        ║
# ╚══════════════════════════════════════════════════════════════════╝

@bot.event
async def on_ready() -> None:
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info(f"discord.py version: {discord.__version__}")
    bot.loop.create_task(daily_scheduler())                # icebreaker questions
    bot.loop.create_task(daily_poll_scheduler())           # individual polls
    bot.loop.create_task(daily_pack_scheduler())           # poll packs
    bot.loop.create_task(daily_accountability_scheduler()) # accountability report


@bot.event
async def on_error(event: str, *args, **kwargs) -> None:
    log.exception(f"Unhandled error in event '{event}'")


async def main() -> None:
    async with bot:
        try:
            await bot.start(DISCORD_TOKEN)
        except discord.LoginFailure:
            log.critical("Invalid DISCORD_TOKEN. Double-check your .env file.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")