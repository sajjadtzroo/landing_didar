"""Canonical default content for a landing page.

A new/blank landing renders a complete "standard" landing from these defaults;
the frontend mirrors them in `constants/content.ts` and merges a landing's stored
`content` JSON over them field-by-field (missing key -> this default shows).

Single source of truth on the backend side — used by `seed.py` and migration
0007's backfill. Keep in loose sync with the frontend CONTENT object (documented,
not auto-synced — they're different languages/runtimes).
"""

import copy

# Per-category labels for the product carousels. Also used by the 0007 backfill to
# turn each landing's existing category split into named groups.
SECTION_LABELS: dict[str, dict[str, str]] = {
    "daily": {
        "eyebrow": "کالکشن روزمره",
        "title": "طلای روزمره",
        "description": "طرح‌های سبک و کاربردی برای استفاده روزانه، مناسب فروش پرگردش فروشگاه.",
    },
    "lux_daily": {
        "eyebrow": "کالکشن لوکس روزمره",
        "title": "طلای لوکس روزمره",
        "description": "طرح‌های روزمره با جلوه‌ای لوکس‌تر؛ حد فاصل کاربردی و خاص.",
    },
    "luxury": {
        "eyebrow": "کالکشن لوکس",
        "title": "طلای لوکس",
        "description": "قطعات شاخص و سنگین‌وزن برای مشتریان خاص و ویترین ممتاز فروشگاه.",
    },
    "watch": {
        "eyebrow": "کالکشن ساعت",
        "title": "ساعت طلا",
        "description": "ساعت‌های طلای ۱۸ عیار با طراحی کلاسیک و مدرن؛ ترکیب کاربرد و لوکس.",
    },
}

HERO_DEFAULT = {
    "eyebrow": "DIDAR GOLD · LUXURY",
    "headline": "درخشش طلای ناب، از دیدار",
    "supporting": "تأمین‌کننده عمده جواهرات طلا برای فروشگاه‌های معتبر سراسر کشور.",
    "cta": "مشاهده محصولات",
}

# icon = whitelisted Lucide name (see TrustBar's ICONS map on the frontend).
TRUST_DEFAULT = [
    {"icon": "BadgeCheck", "title": "اصالت و ردیابی", "sub": "بر پایه اطلاعات معتبر"},
    {"icon": "FileCheck", "title": "مسیر گارانتی", "sub": "معرفی پوشش خدمات"},
    {"icon": "RefreshCw", "title": "بررسی بازخرید", "sub": "ورودی درخواست اولیه"},
]

FAQ_DEFAULT = [
    {
        "question": "حداقل مقدار سفارش چقدر است؟",
        "answer": "حداقل سفارش عمده برای هر طرح ۵۰ گرم است. برای سرویس‌های کامل بسته به مدل متفاوت است؛ کارشناسان ما هنگام تماس دقیق اعلام می‌کنند.",
    },
    {
        "question": "قیمت‌گذاری بر چه اساسی انجام می‌شود؟",
        "answer": "قیمت هر قطعه بر اساس نرخ روز طلا به‌علاوه اجرت ساخت و سود فروش محاسبه می‌شود. چون نرخ طلا روزانه تغییر می‌کند، قیمت نهایی هنگام ثبت سفارش تأیید می‌شود.",
    },
    {
        "question": "ارسال و بیمه محموله چگونه است؟",
        "answer": "تمام محموله‌ها با پست بیمه‌شده و باربری امن ارسال می‌شوند. هزینه بیمه بر عهده فروشنده است و تا تحویل کالا اعتبار دارد.",
    },
    {
        "question": "شرایط مرجوعی و تعویض چیست؟",
        "answer": "کالای سالم تا ۷۲ ساعت پس از تحویل قابل تعویض است؛ اجرت ساخت قطعات سفارشی مرجوع نمی‌شود.",
    },
    {
        "question": "اصالت و عیار طلا چگونه تضمین می‌شود؟",
        "answer": "همه محصولات دارای انگ استاندارد و کد رهگیری هستند و با فاکتور رسمی و برگه ضمانت اصالت ارسال می‌شوند.",
    },
    {
        "question": "شرایط پرداخت چگونه است؟",
        "answer": "پرداخت به‌صورت نقدی، کارت‌به‌کارت یا تسویه اعتباری برای مشتریان دائمی امکان‌پذیر است. جزئیات هنگام تماس هماهنگ می‌شود.",
    },
    {
        "question": "زمان آماده‌سازی و تحویل چقدر است؟",
        "answer": "سفارش‌های موجود ۲ تا ۳ روز کاری و سفارش‌های ساخت اختصاصی ۷ تا ۱۴ روز کاری زمان می‌برند.",
    },
    {
        "question": "امکان سفارش طرح اختصاصی وجود دارد؟",
        "answer": "بله، طرح‌های اختصاصی با پلاک اسم و نقش دلخواه پذیرفته می‌شود. نمونه طرح را هنگام تماس برای شما ارسال می‌کنیم.",
    },
    {
        "question": "بازخرید چگونه انجام می‌شود؟",
        "answer": "پس از ثبت درخواست، اصالت، وزن، وضعیت فیزیکی و شرایط بازار بررسی می‌شود و نتیجه ارزیابی به‌صورت شفاف اعلام خواهد شد.",
    },
    {
        "question": "خدمات پس از فروش شامل چیست؟",
        "answer": "راهنمای نگهداری، بازبینی قطعه، پاک‌سازی تخصصی، بررسی تعمیر و ثبت سوابق خدمات از بخش‌های اصلی این تجربه هستند.",
    },
]

FOOTER_DEFAULT = {
    "tagline": "تأمین‌کننده عمده طلا و جواهرات ۱۸ عیار",
    "address": "تهران، مجتمع دیدار",
    "hours": "شنبه تا چهارشنبه، ۱۰ تا ۱۸",
    "phone": "+982152002050",
    "phoneDisplay": "۰۲۱–۵۲۰۰۲۰۵۰",
    "email": "info@didargold.com",
    "whatsapp": "https://wa.me/989120000000",
    "telegram": "https://t.me/didargold",
    "instagram": "https://instagram.com/didargold",
    "rights": "تمامی حقوق برای دیدار گلد محفوظ است.",
}

PROMO_DEFAULT = "با خرید +۲۰۰ گرم از کالکشن لوکس، ۱٪ تخفیف روی کل فاکتور"

SECTIONS_DEFAULT = {
    "promo": True,
    "hero": True,
    "trust": True,
    "products": True,
    "faq": True,
    "footer": True,
}


def default_content(groups: list[dict] | None = None) -> dict:
    """A complete content blob for a standard landing. `groups` = product groups
    (`{title, eyebrow, description, product_ids[]}`); empty for a fresh landing."""
    return copy.deepcopy(
        {
            "sections": SECTIONS_DEFAULT,
            "promo": {"text": PROMO_DEFAULT},
            "hero": HERO_DEFAULT,
            "trust": TRUST_DEFAULT,
            "groups": groups or [],
            "faq": FAQ_DEFAULT,
            "footer": FOOTER_DEFAULT,
        }
    )


def groups_from_category_rows(rows: list[tuple]) -> list[dict]:
    """Build product groups from (product_id, category) rows (ordered). One group
    per distinct category in first-seen order, labelled from SECTION_LABELS."""
    order: list[str] = []
    by_cat: dict[str, list[str]] = {}
    for pid, cat in rows:
        if cat not in by_cat:
            by_cat[cat] = []
            order.append(cat)
        by_cat[cat].append(str(pid))
    groups: list[dict] = []
    for cat in order:
        label = SECTION_LABELS.get(
            cat, {"eyebrow": "", "title": cat, "description": ""}
        )
        groups.append({**copy.deepcopy(label), "product_ids": by_cat[cat]})
    return groups
