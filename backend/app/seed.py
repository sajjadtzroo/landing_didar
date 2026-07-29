"""Seed 10 products + 8 FAQs. Idempotent: skips if products already exist.
Run: python -m app.seed   (docker entrypoint runs it after migrations)
"""

import asyncio

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models.faq import FAQ
from app.models.product import Product

IMG = "https://didargold.com/images"

# The real Didar Gold catalogue — names, categories, prices and images sourced
# directly from didargold.com (18 pieces). Prices are the store's listed values
# in Toman (shown there as "میلیون تومان"). Weights are the real figures where
# published (first 6); left as None (→ shown without weight) where not.
# tuple: (name, sku, weight_g, price, image, category)
PRODUCTS = [
    ("گردنبند آترین", "NK-ATRIN", 7.20, 248_000_000, f"{IMG}/didar-ui/product-01.jpg", "گردنبند"),
    ("دستبند ویرا", "BR-VIRA", 11.50, 196_000_000, f"{IMG}/didar-ui/product-02.jpg", "دستبند"),
    ("انگشتر مهتاب", "RG-MAHTAB", 4.90, 172_000_000, f"{IMG}/didar-ui/product-03.jpg", "انگشتر"),
    ("گوشواره نادیا", "ER-NADIA", 5.60, 218_000_000, f"{IMG}/didar-ui/product-04.jpg", "گوشواره"),
    ("انگشتر لیلا", "RG-LEILA", 4.20, 165_000_000, f"{IMG}/didar-ui/product-05.jpg", "انگشتر"),
    ("گردنبند رها", "NK-RAHA", 7.10, 232_000_000, f"{IMG}/didar-ui/product-06.jpg", "گردنبند"),
    ("انگشتر سارا", "RG-SARA", None, 184_000_000, f"{IMG}/didar-products/product-07.jpg", "انگشتر"),
    ("گردنبند نوا", "NK-NAVA", None, 226_000_000, f"{IMG}/didar-products/product-08.jpg", "گردنبند"),
    ("دستبند مینا", "BR-MINA", None, 312_000_000, f"{IMG}/didar-products/product-09.jpg", "دستبند"),
    ("گوشواره دریا", "ER-DARYA", None, 198_000_000, f"{IMG}/didar-products/product-10.jpg", "گوشواره"),
    ("انگشتر شایان", "RG-SHAYAN", None, 205_000_000, f"{IMG}/didar-products/product-11.jpg", "انگشتر"),
    ("نیم‌ست آوا", "ST-AVA", None, 418_000_000, f"{IMG}/didar-products/product-12.jpg", "نیم‌ست"),
    ("گردنبند نور", "NK-NOOR", None, 244_000_000, f"{IMG}/didar-products/product-13.jpg", "گردنبند"),
    ("دستبند طلا", "BR-TALA", None, 286_000_000, f"{IMG}/didar-products/product-14.jpg", "دستبند"),
    ("انگشتر پارسا", "RG-PARSA", None, 176_000_000, f"{IMG}/didar-products/product-15.jpg", "انگشتر"),
    ("گوشواره بهار", "ER-BAHAR", None, 238_000_000, f"{IMG}/didar-products/product-16.jpg", "گوشواره"),
    ("گردنبند روشن", "NK-ROSHAN", None, 268_000_000, f"{IMG}/didar-products/product-17.jpg", "گردنبند"),
    ("ست آریانا", "ST-ARIANA", None, 446_000_000, f"{IMG}/didar-products/product-18.jpg", "ست"),
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


async def run() -> None:
    async with SessionLocal() as db:
        count = await db.scalar(select(func.count()).select_from(Product))
        if count:
            print(f"seed: {count} products already exist — skipping")
            return
        # Landing shows 10 products (per the brief). The full 18-piece catalogue
        # stays defined above; bump this slice to seed more.
        for i, (name, sku, wt, price, image, category) in enumerate(PRODUCTS[:10]):
            db.add(
                Product(
                    name=name,
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
        print(f"seed: inserted {len(PRODUCTS)} products, {len(FAQS)} faqs")


if __name__ == "__main__":
    asyncio.run(run())
