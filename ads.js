import config from './ads-config.js';
// Auto ads choose placements through the AdSense dashboard; no manual units needed.
if (config.enabled) {
  if (!/^ca-pub-\d{16}$/.test(config.publisherId)) {
    console.error('Auto ads are disabled: a valid AdSense publisher ID is required.');
  } else {
    // Configure the certified CMP in AdSense Privacy & messaging before activation.
    const script = document.createElement('script');
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${config.publisherId}`;
    document.head.append(script);
  }
}
