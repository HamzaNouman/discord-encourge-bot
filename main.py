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
"""

import asyncio
import logging
import os
import platform
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError   # Python 3.9+

# ── Windows fix: ProactorEventLoop raises a harmless but noisy RuntimeError
# on shutdown. SelectorEventLoop avoids it entirely and works fine for bots.
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import discord
from discord.ext import commands
from dotenv import load_dotenv

# ─── Load environment variables from .env ────────────────────────────────────
load_dotenv()

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
CHANNEL_ID: int    = int(os.getenv("CHANNEL_ID", "0"))
TZ_NAME: str       = os.getenv("TIMEZONE", "UTC")

if not DISCORD_TOKEN:
    raise EnvironmentError("DISCORD_TOKEN is missing. Add it to your .env file.")
if not CHANNEL_ID:
    raise EnvironmentError("CHANNEL_ID is missing. Add it to your .env file.")

# ─── Resolve timezone ─────────────────────────────────────────────────────────
# On Windows, zoneinfo requires the `tzdata` pip package (no OS-level tz database).
# Install it with:  pip install tzdata
# As a safe fallback we use the built-in timezone.utc so the bot always starts.
try:
    LOCAL_TZ = ZoneInfo(TZ_NAME)
except (ZoneInfoNotFoundError, KeyError):
    logging.warning(
        f"Timezone '{TZ_NAME}' not found. "
        "Install tzdata (pip install tzdata) for full timezone support. "
        "Falling back to UTC."
    )
    LOCAL_TZ = timezone.utc   # stdlib fallback — always available, no package needed

# ─── Scheduler configuration ─────────────────────────────────────────────────
# Change these values to control when messages are sent (24-hour clock, local time).
SEND_HOUR_MIN: int = 4   # Earliest hour to send (noon)
SEND_HOUR_MAX: int = 21   # Latest hour to send   (9 PM)

# How many messages to send each day (chosen randomly within this range).
MESSAGES_PER_DAY_MIN: int = 100
MESSAGES_PER_DAY_MAX: int = 200

# ─── Reaction emojis ─────────────────────────────────────────────────────────
# These are added automatically to every bot message to encourage engagement.
REACTION_EMOJIS: list[str] = ["🌱", "👍", "💬", "❤️", "✨"]

# ─── Question bank (30 Arabic questions) ─────────────────────────────────────
# Mix of: mood check-ins 🌡️ | recovery reflections 🔄 | fun icebreakers 🎉
# To add a new question, simply append a new string to this list.
QUESTIONS: list[str] = [
    # 🌡️ Mood check-ins (متابعة المزاج والحالة النفسية)
    "🌡️ كيف تقيّم يومك حتى الآن من 1 إلى 10؟ ولماذا اخترت هذا الرقم؟",
    "🌤️ لو وصفنا حالتك النفسية اليوم بظاهرة جوية (مشمس، غائم، ممطر...)؛ كيف سيكون الطقس؟",
    "🎨 لو يعبر لون واحد عن مزاجك اليوم، ما اللون الذي ستختاره؟",
    "🔋 كم تبلغ نسبة طاقتك الآن؟ وما أكثر شيء شحنك أو استنزفك اليوم؟",
    "💭 ما الشيء الذي يستحوذ على الجزء الأكبر من تفكيرك حالياً؟",

    # 🔄 Recovery & personal growth reflections (التعافي والنمو الشخصي)
    "🌱 ما الإنجاز البسيط الذي حققته اليوم وتراه يستحق التقدير، مهما كان صغيراً؟",
    "🏆 ما أحدث تحدٍّ استطعت تجاوزه، وحمدت الله عليه؟",
    "🔄 ما أهم درس خرجت به من أشد اللحظات صعوبة في رحلتك؟",
    "🤝 من الشخص الذي وجدته سنداً لك في وقتك العصيب؟ وكيف كان أثره؟",
    "🛤️ ما الخطوة الوحيدة التي يمكنك خطوها اليوم لتقترب أكثر من هدفك؟",
    "🙏 ما الشيء الذي تشعر بامتنان حقيقي لوجوده في حياتك اليوم؟",
    "💪 ما نقطة القوة التي اكتشفتها في شخصيتك مؤخراً ولم تكن تلاحظها؟",
    "🌊 ما استراتيجيتك الخاصة في التعامل مع الأيام الثقيلة؟",
    "🦋 ما أثر التغيير الإيجابي الذي تلمسه في نفسك خلال الفترة الأخيرة؟",
    "🌙 لو أتيحت لك فرصة توجيه نصيحة لنفسك قبل عام من الآن، ماذا ستجيب؟",

    # 🎉 Fun icebreakers (تفاعلية وأسئلة خفيفة)
    "☕ القهوة أم الشاي؟ ولماذا ترى أن اختيارك هو الأفضل بلا منازع؟",
    "🍕 لو أُجبرت على تناول وجبة واحدة يومياً لمدة شهر كامل، ماذا ستختار؟",
    "🌍 لو أتيحت لك فرصة السفر غداً دون أي قيود، ما وجهتك الأولى؟",
    "📚 ما آخر كتاب، مقال، أو درس شاهدته وترك أثراً فيك؟",
    "🦸 لو مُنحت قوة خارقة واحدة لليوم، ما القوة التي تختارها؟",
    "🐾 هل تنحاز للقطط أم للكلاب؟ أم أن لديك خياراً مختلفاً تماماً؟",
    "🌟 ما الإنجاز الهادئ الذي حققته هذا الأسبوع ولم تتحدث عنه لأحد؟",
    "🎯 ما المهارة أو التجربة التي تطمح لخوضها قبل نهاية هذا العام؟",

    # 💬 Deep connection questions (نقاشات وتقارب عميق)
    "🤔 ما الشيء الذي تتمنى لو يفهمه الآخرون عنك بوضوح أكبر؟",
    "💌 لو كتبت رسالة لنفسك بعد 5 سنوات، ما السطر الأول الذي ستفتتح به الرسالة؟",
    "🌈 ما الموقف الصغير الذي رسم على وجهك ابتسامة هذا الأسبوع؟",
    "🧩 ما الجانب الخفي في شخصيتك الذي تعتقد أن معظم الناس لا يعرفونه؟",
    "🔑 ما الكلمة الوحيدة التي تختصر بها مرحلتك الحالية من الحياة؟ ولماذا؟",
]

# ─── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("icebreaker_bot")

# ─── Bot setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
# We don't need message_content for this bot (we only send, not read messages).

bot = commands.Bot(command_prefix="!", intents=intents)


# ─── Question tracker (prevents consecutive duplicates) ───────────────────────
class QuestionTracker:
    """Tracks recently used questions to avoid consecutive repeats."""

    def __init__(self, questions: list[str]) -> None:
        self._questions = questions.copy()
        self._used_indices: list[int] = []           # indices of recently used Qs
        self._no_repeat_window: int = max(1, len(questions) // 3)  # avoid last 1/3

    def pick(self) -> str:
        """Return a random question that wasn't used recently."""
        available = [
            i for i in range(len(self._questions))
            if i not in self._used_indices[-self._no_repeat_window:]
        ]
        # Safety fallback: if somehow all are excluded, reset
        if not available:
            self._used_indices.clear()
            available = list(range(len(self._questions)))

        chosen_index = random.choice(available)
        self._used_indices.append(chosen_index)

        # Keep the history list from growing indefinitely
        if len(self._used_indices) > self._no_repeat_window * 2:
            self._used_indices = self._used_indices[-self._no_repeat_window:]

        return self._questions[chosen_index]


tracker = QuestionTracker(QUESTIONS)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now_local() -> datetime:
    """Return the current time in LOCAL_TZ."""
    return datetime.now(tz=LOCAL_TZ)


def _random_send_times_today() -> list[datetime]:
    """
    Generate 1–2 random send times for today, within the configured window.
    Returns a sorted list of timezone-aware datetimes.
    """
    count = random.randint(MESSAGES_PER_DAY_MIN, MESSAGES_PER_DAY_MAX)
    today = _now_local().date()
    times: list[datetime] = []

    # Build a list of candidate minute-slots in the window (to avoid same minute)
    total_minutes = (SEND_HOUR_MAX - SEND_HOUR_MIN) * 60
    if total_minutes < count:
        raise ValueError("Time window too narrow for the requested message count.")

    chosen_minutes = random.sample(range(total_minutes), count)

    for offset_minutes in chosen_minutes:
        hour   = SEND_HOUR_MIN + offset_minutes // 60
        minute = offset_minutes % 60
        send_dt = datetime(today.year, today.month, today.day,
                           hour, minute, tzinfo=LOCAL_TZ)
        times.append(send_dt)

    return sorted(times)


async def _send_question(channel: discord.TextChannel) -> None:
    """Pick a question, send it, and add reactions."""
    question = tracker.pick()

    # Optional header to make it visually distinct in the channel
    header = "━━━━━━━━━━━━━━━━━━━━━━━━\n💬 **سؤال اليوم** | Check-in\n━━━━━━━━━━━━━━━━━━━━━━━━"
    content = f"{header}\n\n{question}"

    try:
        message = await channel.send(content)
        log.info(f"Sent question to #{channel.name}: {question[:60]}…")

        # Add reactions to encourage low-effort engagement
        for emoji in REACTION_EMOJIS:
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException as e:
                log.warning(f"Could not add reaction {emoji}: {e}")

    except discord.Forbidden:
        log.error("Bot lacks permission to send messages in the target channel.")
    except discord.HTTPException as e:
        log.error(f"Failed to send message: {e}")


# ─── Daily scheduler loop ─────────────────────────────────────────────────────

async def daily_scheduler() -> None:
    """
    Core scheduling loop. Runs forever:
      1. Computes send times for today (in local TZ).
      2. Skips any times already in the past.
      3. Sleeps until each send time and fires the question.
      4. After all sends, sleeps until midnight to start a fresh day.
    """
    await bot.wait_until_ready()

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        # Might not be cached yet; try fetching explicitly
        try:
            channel = await bot.fetch_channel(CHANNEL_ID)
        except discord.NotFound:
            log.error(f"Channel {CHANNEL_ID} not found. Check your CHANNEL_ID.")
            return
        except discord.Forbidden:
            log.error(f"Bot cannot access channel {CHANNEL_ID}.")
            return

    log.info(f"Scheduler started. Targeting #{channel.name} | TZ: {TZ_NAME}")

    while not bot.is_closed():
        send_times = _random_send_times_today()
        log.info(
            f"Today's schedule ({_now_local().date()}): "
            + ", ".join(t.strftime("%H:%M") for t in send_times)
        )

        for send_time in send_times:
            now = _now_local()
            delay = (send_time - now).total_seconds()

            if delay < 0:
                log.info(f"Skipping past time slot: {send_time.strftime('%H:%M')}")
                continue

            log.info(f"Next message in {delay / 3600:.1f} h at {send_time.strftime('%H:%M %Z')}")
            await asyncio.sleep(delay)
            await _send_question(channel)

        # Sleep until the start of the next day (midnight local time) + 1 min buffer
        now = _now_local()
        tomorrow_midnight = datetime(
            now.year, now.month, now.day, tzinfo=LOCAL_TZ
        ) + timedelta(days=1, minutes=1)
        sleep_seconds = (tomorrow_midnight - _now_local()).total_seconds()
        log.info(f"All done for today. Sleeping {sleep_seconds / 3600:.1f} h until tomorrow.")
        await asyncio.sleep(max(sleep_seconds, 1))


# ─── Bot events ──────────────────────────────────────────────────────────────

@bot.event
async def on_ready() -> None:
    log.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    log.info(f"discord.py version: {discord.__version__}")
    # Start the scheduler as a background task
    bot.loop.create_task(daily_scheduler())


@bot.event
async def on_error(event: str, *args, **kwargs) -> None:
    log.exception(f"Unhandled error in event '{event}'")

# Paste this anywhere below the bot = commands.Bot(...) line

@bot.command(name="test")
async def test_question(ctx):
    """Type !test in Discord to fire a question immediately."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await _send_question(channel)

# ─── Entry point ─────────────────────────────────────────────────────────────

async def main() -> None:
    """Run the bot inside an explicit async context for clean shutdown."""
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