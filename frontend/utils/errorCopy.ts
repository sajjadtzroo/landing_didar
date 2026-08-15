// Persian copy for the app-level error page (error.vue) — one entry per
// status we can say something useful about, plus 4xx/5xx buckets so every
// code in the 400–599 range renders a sensible page. `retry` marks statuses
// where reloading the same URL can plausibly succeed.

export interface ErrorCopy {
  title: string
  message: string
  retry: boolean
}

const KNOWN: Record<number, Omit<ErrorCopy, 'retry'> & { retry?: boolean }> = {
  400: {
    title: 'درخواست نامعتبر است',
    message: 'چیزی در درخواست شما درست نبود. آدرس را بررسی کنید یا از فروشگاه شروع کنید.',
  },
  401: {
    title: 'ورود لازم است',
    message: 'برای دیدن این صفحه ابتدا باید وارد حساب خود شوید.',
  },
  403: {
    title: 'دسترسی مجاز نیست',
    message: 'شما اجازهٔ دسترسی به این صفحه را ندارید.',
  },
  404: {
    title: 'صفحه پیدا نشد',
    message: 'صفحه‌ای که دنبالش بودید وجود ندارد یا جابه‌جا شده است.',
  },
  408: {
    title: 'درخواست طولانی شد',
    message: 'پاسخ‌گویی بیش از حد طول کشید. دوباره تلاش کنید.',
    retry: true,
  },
  410: {
    title: 'این صفحه دیگر در دسترس نیست',
    message: 'محتوایی که دنبالش بودید برداشته شده است.',
  },
  422: {
    title: 'اطلاعات قابل پردازش نیست',
    message: 'داده‌های ارسال‌شده معتبر نبود. فرم را بررسی و دوباره ارسال کنید.',
  },
  429: {
    title: 'تعداد درخواست‌ها زیاد است',
    message: 'کمی صبر کنید و دوباره تلاش کنید.',
    retry: true,
  },
  500: {
    title: 'خطایی در سرور رخ داد',
    message: 'مشکلی از سمت ما پیش آمده و در حال بررسی آن هستیم.',
    retry: true,
  },
  502: {
    title: 'سرویس موقتاً در دسترس نیست',
    message: 'در حال به‌روزرسانی یا رفع مشکل هستیم؛ چند لحظهٔ دیگر تلاش کنید.',
    retry: true,
  },
  503: {
    title: 'سرویس موقتاً در دسترس نیست',
    message: 'در حال به‌روزرسانی یا رفع مشکل هستیم؛ چند لحظهٔ دیگر تلاش کنید.',
    retry: true,
  },
  504: {
    title: 'پاسخ‌گویی سرور طول کشید',
    message: 'اتصال به سرور بیش از حد طول کشید. دوباره تلاش کنید.',
    retry: true,
  },
}

export function errorCopy(statusCode?: number): ErrorCopy {
  const code = statusCode ?? 500
  const known = KNOWN[code]
  if (known) return { retry: false, ...known }
  if (code >= 500)
    return {
      title: 'خطایی در سرور رخ داد',
      message: 'مشکلی از سمت ما پیش آمده و در حال بررسی آن هستیم.',
      retry: true,
    }
  return {
    title: 'امکان پردازش درخواست نیست',
    message: 'درخواست شما قابل انجام نبود. از فروشگاه شروع کنید.',
    retry: false,
  }
}
