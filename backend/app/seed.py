"""Seed 10 products + 8 FAQs. Idempotent: skips if products already exist.
Run: python -m app.seed   (docker entrypoint runs it after migrations)
"""

import asyncio

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models.faq import FAQ
from app.models.landing import Landing, LandingProduct
from app.models.product import Product

IMG = "https://didargold.com/images"

# The real Didar Gold catalogue — names, categories, prices and images sourced
# directly from didargold.com (18 pieces). Prices are the store's listed values
# in Toman (shown there as "میلیون تومان"). Weights are the real figures where
# published (first 6); left as None (→ shown without weight) where not.
# tuple: (name, slug, sku, weight_g, price, image, category)
PRODUCTS = [
    ("گردنبند آترین", "atrin-necklace", "NK-ATRIN", 7.20, 248_000_000, "/images/products/product-01.jpg", "گردنبند"),
    ("دستبند ویرا", "vira-bracelet", "BR-VIRA", 11.50, 196_000_000, "/images/products/product-02.jpg", "دستبند"),
    ("انگشتر مهتاب", "mahtab-ring", "RG-MAHTAB", 4.90, 172_000_000, "/images/products/product-03.jpg", "انگشتر"),
    ("گوشواره نادیا", "nadia-earrings", "ER-NADIA", 5.60, 218_000_000, "/images/products/product-04.jpg", "گوشواره"),
    ("انگشتر لیلا", "leila-ring", "RG-LEILA", 4.20, 165_000_000, "/images/products/product-05.jpg", "انگشتر"),
    ("گردنبند رها", "raha-necklace", "NK-RAHA", 7.10, 232_000_000, "/images/products/product-06.jpg", "گردنبند"),
    ("انگشتر سارا", "sara-ring", "RG-SARA", None, 184_000_000, "/images/products/product-07.jpg", "انگشتر"),
    ("گردنبند نوا", "nava-necklace", "NK-NAVA", None, 226_000_000, "/images/products/product-08.jpg", "گردنبند"),
    ("دستبند مینا", "mina-bracelet", "BR-MINA", None, 312_000_000, "/images/products/product-09.jpg", "دستبند"),
    ("گوشواره دریا", "darya-earrings", "ER-DARYA", None, 198_000_000, "/images/products/product-10.jpg", "گوشواره"),
    ("انگشتر شایان", "shayan-ring", "RG-SHAYAN", None, 205_000_000, f"{IMG}/didar-products/product-11.jpg", "انگشتر"),
    ("نیم‌ست آوا", "ava-set", "ST-AVA", None, 418_000_000, f"{IMG}/didar-products/product-12.jpg", "نیم‌ست"),
    ("گردنبند نور", "noor-necklace", "NK-NOOR", None, 244_000_000, f"{IMG}/didar-products/product-13.jpg", "گردنبند"),
    ("دستبند طلا", "tala-bracelet", "BR-TALA", None, 286_000_000, f"{IMG}/didar-products/product-14.jpg", "دستبند"),
    ("انگشتر پارسا", "parsa-ring", "RG-PARSA", None, 176_000_000, f"{IMG}/didar-products/product-15.jpg", "انگشتر"),
    ("گوشواره بهار", "bahar-earrings", "ER-BAHAR", None, 238_000_000, f"{IMG}/didar-products/product-16.jpg", "گوشواره"),
    ("گردنبند روشن", "roshan-necklace", "NK-ROSHAN", None, 268_000_000, f"{IMG}/didar-products/product-17.jpg", "گردنبند"),
    ("ست آریانا", "ariana-set", "ST-ARIANA", None, 446_000_000, f"{IMG}/didar-products/product-18.jpg", "ست"),
]

FAQS = [
    (
        "حداقل مقدار سفارش چقدر است؟",
        "حداقل سفارش عمده برای هر طرح ۵۰ گرم است. برای سرویس‌های کامل بسته به مدل متفاوت است؛ کارشناسان ما هنگام تماس دقیق اعلام می‌کنند.",
    ),
    (
        "قیمت‌گذاری بر چه اساسی انجام می‌شود؟",
        "قیمت هر قطعه بر اساس نرخ روز طلا به‌علاوه اجرت ساخت و سود فروش محاسبه می‌شود. چون نرخ طلا روزانه تغییر می‌کند، قیمت نهایی هنگام ثبت سفارش تأیید می‌شود.",
    ),
    (
        "ارسال و بیمه محموله چگونه است؟",
        "تمام محموله‌ها با پست بیمه‌شده و باربری امن ارسال می‌شوند. هزینه بیمه بر عهده فروشنده است و تا تحویل کالا اعتبار دارد.",
    ),
    (
        "شرایط مرجوعی و تعویض چیست؟",
        "کالای سالم تا ۷۲ ساعت پس از تحویل قابل تعویض است؛ اجرت ساخت قطعات سفارشی مرجوع نمی‌شود.",
    ),
    (
        "اصالت و عیار طلا چگونه تضمین می‌شود؟",
        "همه محصولات دارای انگ استاندارد و کد رهگیری هستند و با فاکتور رسمی و برگه ضمانت اصالت ارسال می‌شوند.",
    ),
    (
        "شرایط پرداخت چگونه است؟",
        "پرداخت به‌صورت نقدی، کارت‌به‌کارت یا تسویه اعتباری برای مشتریان دائمی امکان‌پذیر است. جزئیات هنگام تماس هماهنگ می‌شود.",
    ),
    (
        "زمان آماده‌سازی و تحویل چقدر است؟",
        "سفارش‌های موجود ۲ تا ۳ روز کاری و سفارش‌های ساخت اختصاصی ۷ تا ۱۴ روز کاری زمان می‌برند.",
    ),
    (
        "امکان سفارش طرح اختصاصی وجود دارد؟",
        "بله، طرح‌های اختصاصی با پلاک اسم و نقش دلخواه پذیرفته می‌شود. نمونه طرح را هنگام تماس برای شما ارسال می‌کنیم.",
    ),
    # ---- Merged from didargold.com (ServicesPage) — ownership experience ----
    (
        "بازخرید چگونه انجام می‌شود؟",
        "پس از ثبت درخواست، اصالت، وزن، وضعیت فیزیکی و شرایط بازار بررسی می‌شود و نتیجه ارزیابی به‌صورت شفاف اعلام خواهد شد.",
    ),
    (
        "خدمات پس از فروش شامل چیست؟",
        "راهنمای نگهداری، بازبینی قطعه، پاک‌سازی تخصصی، بررسی تعمیر و ثبت سوابق خدمات از بخش‌های اصلی این تجربه هستند.",
    ),
]


# Three fixed landings (slug is immutable — /l/<slug> + the `/` redirect depend
# on it). Admin edits title/hero video + product selection, not the slug.
LANDINGS = [
    ("one", "لندینگ اصلی"),
    ("two", "لندینگ دوم"),
    ("three", "لندینگ سوم"),
]


async def _seed_catalog(db) -> None:
    count = await db.scalar(select(func.count()).select_from(Product))
    if count:
        print(f"seed: {count} products already exist — skipping catalog")
        return
    # Landing shows 10 products (per the brief). The full 18-piece catalogue
    # stays defined above; bump this slice to seed more.
    seeded = PRODUCTS[:10]
    for i, (name, slug, sku, wt, price, image, category) in enumerate(seeded):
        db.add(
            Product(
                name=name,
                slug=slug,
                sku=sku,
                description=(
                    f"{name} — {category} طلای ۱۸ عیار دیدار، "
                    "همراه با خدمات اصالت و گارانتی."
                ),
                weight_grams=wt,
                karat=18,
                price=price,
                image_url=image,
                is_active=True,
                sort_order=i,
            )
        )
    for i, (q, a) in enumerate(FAQS):
        db.add(FAQ(question=q, answer=a, is_active=True, sort_order=i))
    await db.commit()
    print(f"seed: inserted {len(seeded)} products, {len(FAQS)} faqs")


async def _seed_landings(db) -> None:
    # Independent guard: products usually already exist on a live DB, so this must
    # NOT hang off the catalog early-return, or landings would never seed.
    count = await db.scalar(select(func.count()).select_from(Landing))
    if count:
        print(f"seed: {count} landings already exist — skipping landings")
        return
    products = (
        await db.execute(
            select(Product).where(Product.is_active).order_by(Product.sort_order)
        )
    ).scalars().all()
    for slug, title in LANDINGS:
        landing = Landing(
            slug=slug,
            title=title,
            hero_video_url="/media/hero.mp4",
            hero_poster_url="/media/hero-poster.jpg",
        )
        db.add(landing)
        await db.flush()  # assign landing.id before the association rows
        for i, p in enumerate(products):
            db.add(
                LandingProduct(landing_id=landing.id, product_id=p.id, sort_order=i)
            )
    await db.commit()
    print(f"seed: inserted {len(LANDINGS)} landings ({len(products)} products each)")


async def run() -> None:
    async with SessionLocal() as db:
        await _seed_catalog(db)
        await _seed_landings(db)


if __name__ == "__main__":
    asyncio.run(run())
