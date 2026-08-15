# Visual baselines

Full-page Playwright screenshots of the key pages, captured against the live
docker stack (`frontend:3000`) — the reference for eyeballing visual
regressions after design changes.

Regenerate (stack must be up):

```bash
docker run --rm --network landing_didar_default -v "$PWD/e2e/baselines:/out" \
  mcr.microsoft.com/playwright:v1.50.0-noble sh -c \
  "npm i -g playwright@1.50.0 && playwright screenshot --full-page \
   --viewport-size=390,844 --wait-for-timeout=4000 \
   http://frontend:3000/shop /out/shop-mobile.png"
```

Viewports: mobile 390×844 (site is mobile-first), desktop 1440×900.
Pages: /shop (both), /l/one, /products/<slug>, /account/login, /verify,
/admin/login. Keep filenames stable so diffs stay meaningful.
