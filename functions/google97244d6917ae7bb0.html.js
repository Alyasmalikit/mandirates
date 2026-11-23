// Google Search Console verification file, served by Cloudflare Pages.
// It lives in the functions folder, so the daily site rebuild never deletes it.
export const onRequestGet = () =>
  new Response('google-site-verification: google97244d6917ae7bb0.html', {
    status: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'public, max-age=3600' }
  });
