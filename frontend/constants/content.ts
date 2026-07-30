// All UI copy lives here — no hardcoded strings in templates. Persian (fa), RTL.
export const CONTENT = {
  brand: 'دیدار گلد',
  phone: '+982191002020',
  phoneDisplay: '۰۲۱–۹۱۰۰۲۰۲۰',
  email: 'info@didargold.com',
  whatsapp: 'https://wa.me/989120000000',
  telegram: 'https://t.me/didargold',
  instagram: 'https://instagram.com/didargold',

  // Default banner + per-landing overrides (keyed by /l/<slug>).
  promo: 'با خرید +۲۰۰ گرم از کالکشن لوکس، ۱٪ تخفیف روی کل فاکتور',
  promoByLanding: {
    one: 'با خرید +۲۰۰ گرم از کالکشن لوکس، ۱٪ تخفیف روی کل فاکتور',
    two: 'با خرید +۲۰۰ گرم از کالکشن روزمره، ۱٪ تخفیف روی کل فاکتور دریافت کنید',
    three: 'با خرید +۲۰۰ گرم از کالکشن‌ها، ۲٪ تخفیف روی کل فاکتور',
  } as Record<string, string>,

  nav: {
    order: 'سفارش',
  },

  hero: {
    eyebrow: 'DIDAR GOLD · LUXURY',
    headline: 'درخشش طلای ناب، از دیدار',
    supporting: 'تأمین‌کننده عمده جواهرات طلا برای فروشگاه‌های معتبر سراسر کشور.',
    cta: 'مشاهده محصولات',
  },

  trust: [
    { title: 'اصالت و ردیابی', sub: 'بر پایه اطلاعات معتبر' },
    { title: 'مسیر گارانتی', sub: 'معرفی پوشش خدمات' },
    { title: 'بررسی بازخرید', sub: 'ورودی درخواست اولیه' },
  ],

  products: {
    eyebrow: 'مجموعه دیدار',
    title: 'محصولات',
    description: 'گزیده‌ای از طرح‌های طلای ۱۸ عیار، آماده برای سفارش عمده فروشگاه‌ها.',
    priceOnRequest: 'استعلام قیمت',
    // Two landing carousels, keyed by product.category.
    daily: {
      eyebrow: 'کالکشن روزمره',
      title: 'طلای لوکس روزمره',
      description: 'طرح‌های سبک و کاربردی برای استفاده روزانه، مناسب فروش پرگردش فروشگاه.',
    },
    luxury: {
      eyebrow: 'کالکشن لوکس',
      title: 'طلای لوکس',
      description: 'قطعات شاخص و سنگین‌وزن برای مشتریان خاص و ویترین ممتاز فروشگاه.',
    },
    add: 'افزودن به سبد',
    added: 'انتخاب‌شده',
    weight: 'وزن',
    karat: 'عیار',
    ojrat: 'اجرت',
    sku: 'کد',
    gram: 'گرم',
    quantity: 'تعداد',
    viewDetails: 'مشاهده جزئیات',
    related: 'محصولات مرتبط',
  },

  cart: {
    title: 'سبد سفارش',
    empty: 'سبد شما خالی است.',
    remove: 'حذف',
    continue: 'ادامه و ثبت سفارش',
    itemsCount: (n: number) => `${n} کالا`,
    total: 'جمع کل',
  },

  faq: {
    eyebrow: 'راهنمای خرید',
    title: 'سؤالات متداول',
    description: 'پاسخ روشن به پرسش‌های رایج درباره سفارش، قیمت‌گذاری، ارسال و اصالت طلا.',
  },

  form: {
    title: 'ثبت اطلاعات سفارش',
    summary: 'خلاصه سفارش شما',
    fullName: 'نام و نام خانوادگی',
    phone: 'شماره موبایل',
    storeName: 'نام فروشگاه',
    province: 'استان',
    provincePlaceholder: 'انتخاب استان',
    city: 'شهر (اختیاری)',
    note: 'توضیحات (اختیاری)',
    submit: 'ثبت سفارش',
    submitting: 'در حال ثبت…',
    errors: {
      fullName: 'نام را کامل وارد کنید (بین ۳ تا ۶۰ حرف).',
      phone: 'شماره موبایل معتبر وارد کنید، مثال: ۰۹۱۲۱۲۳۴۵۶۷.',
      storeName: 'نام فروشگاه را وارد کنید (بین ۲ تا ۸۰ حرف).',
      province: 'استان را انتخاب کنید.',
      note: 'توضیحات نباید بیشتر از ۳۰۰ حرف باشد.',
      generic: 'ثبت سفارش با خطا مواجه شد. دوباره تلاش کنید.',
    },
  },

  success: {
    title: 'سفارش شما ثبت شد',
    reference: 'کد پیگیری',
    next: 'کارشناسان ما به‌زودی برای هماهنگی با شما تماس می‌گیرند.',
    call: 'همین حالا تماس بگیرید',
  },

  footer: {
    tagline: 'تأمین‌کننده عمده طلا و جواهرات ۱۸ عیار',
    hoursTitle: 'نشانی و ساعات کاری',
    socialTitle: 'ما را دنبال کنید',
    address: 'تهران، مجتمع دیدار',
    hours: 'شنبه تا چهارشنبه، ۱۰ تا ۱۸',
    rights: 'تمامی حقوق برای دیدار گلد محفوظ است.',
    call: 'تماس تلفنی',
  },
} as const
