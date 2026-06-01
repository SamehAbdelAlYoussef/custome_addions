(function() {
    function initSignup() {
        // ── Loading overlay on form submit ──
        var form = document.getElementById('ms-signup-form');
        if (form) {
            form.addEventListener('submit', function() {
                var overlay = document.getElementById('ms-loading');
                if (overlay) { overlay.style.display = 'flex'; }
            });
        }

        // ── Subdomain availability check ──
        var subInput = document.querySelector('input[name="subdomain"]');
        var statusEl = document.getElementById('ms-subdomain-status');
        var timer = null;

        if (subInput && statusEl) {
            subInput.addEventListener('input', function() {
                var val = subInput.value.trim().toLowerCase();
                subInput.value = val.replace(/[^a-z0-9\-]/g, '');
                val = subInput.value;

                if (timer) clearTimeout(timer);
                if (val.length < 3) {
                    statusEl.textContent = 'Minimum 3 characters';
                    statusEl.style.color = '#888';
                    return;
                }

                statusEl.textContent = 'Checking...';
                statusEl.style.color = '#888';

                timer = setTimeout(function() {
                    fetch('/signup/check-subdomain?subdomain=' + encodeURIComponent(val))
                        .then(function(r) { return r.json(); })
                        .then(function(data) {
                            if (data.available) {
                                statusEl.innerHTML = '<span style="color:#1A6B3A;font-weight:600;">\u2713 Available</span>';
                            } else {
                                statusEl.innerHTML = '<span style="color:#e74c3c;font-weight:600;">\u2717 ' + (data.reason || 'Already taken') + '</span>';
                            }
                        })
                        .catch(function() { statusEl.textContent = ''; });
                }, 500);
            });
        }

        // ── Load Cloudflare Turnstile ──
        var tsContainer = document.getElementById('ms-turnstile-container');
        if (tsContainer) {
            var sitekey = tsContainer.getAttribute('data-sitekey');
            if (sitekey) {
                var script = document.createElement('script');
                script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=msTurnstileReady';
                script.async = true;
                script.defer = true;
                document.head.appendChild(script);

                window.msTurnstileReady = function() {
                    if (window.turnstile) {
                        window.turnstile.render('#ms-turnstile-container', {
                            sitekey: sitekey,
                            theme: 'light',
                            callback: function(token) {
                                // Token is auto-added to form as cf-turnstile-response
                            },
                        });
                    }
                };
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSignup);
    } else {
        initSignup();
    }
})();
