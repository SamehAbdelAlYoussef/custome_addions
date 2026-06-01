(function() {
    function initSignup() {
        // ── Loading overlay on form submit ──
        var form = document.querySelector('form[action="/signup/submit"]');
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
                        .catch(function() {
                            statusEl.textContent = '';
                        });
                }, 500);
            });
        }
    }

    // Handle both cases: already loaded or not yet loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSignup);
    } else {
        initSignup();
    }
})();
