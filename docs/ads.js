import config from './ads-config.js';
// Leave the placement inert until a real provider account and consent setup exist.
const placement = document.querySelector('[data-ad-placement]');
if (placement && config.enabled) {
  if (!/^ca-pub-\d{16}$/.test(config.publisherId) || !/^\d+$/.test(config.slotId)) {
    console.error('Ads are disabled: valid publisher and ad-slot IDs are required.');
  } else {
    // The configured certified CMP must be installed before enabling this integration.
    const label = document.createElement('span');
    label.textContent = 'ADVERTISEMENT';
    const unit = document.createElement('ins');
    unit.className = 'adsbygoogle';
    unit.style.display = 'block';
    unit.dataset.adClient = config.publisherId;
    unit.dataset.adSlot = config.slotId;
    unit.dataset.adFormat = 'auto';
    unit.dataset.fullWidthResponsive = 'true';
    placement.replaceChildren(label, unit);
    const script = document.createElement('script');
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${config.publisherId}`;
    script.onload = () => (window.adsbygoogle = window.adsbygoogle || []).push({});
    script.onerror = () => placement.hidden = true;
    document.head.append(script);
  }
}
