// Tracks the last landing page the user visited so خانه stays visible
// after they navigate away to /shop, /products, etc.
export const useLandingContext = () =>
  useState<string | null>('landingSlug', () => null)
