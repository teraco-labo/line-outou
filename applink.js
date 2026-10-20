/*
  アプリでひらく部品（2026-10-20）  <script src="https://teraco-labo.github.io/line-outou/applink.js" defer></script>
  藤崎さん「他のSNSやホームページも、アプリで開くように」
  ・ふつうの https のリンクは、Safari・Chrome・LINE の中なら、押すとアプリがひらく（2026-10-20 iPhone 実機で確認）→ 触らない
  ・LINE の中：Gemini（てらこ先生AIなど）は、アプリに渡らずウェブになる → LINE の外のブラウザでひらく（openExternalBrowser=1・実機で確認）
  ・Instagram／Facebook／TikTok の中（iPhone）：アプリを呼び出すのを止めることがある → YouTube だけ youtube:// で呼び、ひらかなければウェブへ戻す
  Android はまだ確かめていないので何もしない
*/
(function () {
  var ua = navigator.userAgent;
  var isIOS = /iPhone|iPad|iPod/.test(ua);
  var inLine = / Line\//i.test(ua);
  var inSns = /Instagram|FBAN|FBAV|FB_IAB|musical_ly|BytedanceWebview|TikTok/i.test(ua);
  if (!inLine && !(isIOS && inSns)) return;

  function ytApp(href) {
    var m = href.match(/^https?:\/\/youtu\.be\/([\w-]+)(?:\?(.*))?/);
    if (m) return 'youtube://www.youtube.com/watch?v=' + m[1] + (m[2] ? '&' + m[2] : '');
    m = href.match(/^https?:\/\/(?:www\.|m\.)?youtube\.com\/(.*)$/);
    if (m && !/^embed\//.test(m[1])) return 'youtube://www.youtube.com/' + m[1];
    return null;
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var href = a.href;
    if (inLine && /^https:\/\/gemini\.google\.com\//.test(href) && href.indexOf('openExternalBrowser=') < 0) {
      e.preventDefault();
      location.href = href + (href.indexOf('?') < 0 ? '?' : '&') + 'openExternalBrowser=1';
      return;
    }
    if (isIOS && inSns) {
      var app = ytApp(href);
      if (!app) return;
      e.preventDefault();
      var left = false;
      var onHide = function () { left = true; };
      document.addEventListener('visibilitychange', onHide, { once: true });
      window.addEventListener('pagehide', onHide, { once: true });
      location.href = app;
      setTimeout(function () { if (!left && document.visibilityState === 'visible') location.href = href; }, 1600);
    }
  }, true);
})();
