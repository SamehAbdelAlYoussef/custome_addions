(function() {
    function initPricing() {
        var container = document.getElementById('ms-billing-toggle');
        if (!container) return;
        var buttons = container.querySelectorAll('.ms-toggle-btn');
        if (!buttons.length) return;

        function setCycle(cycle) {
            for (var i = 0; i < buttons.length; i++) {
                if (buttons[i].getAttribute('data-cycle') === cycle) {
                    buttons[i].style.background = '#fff';
                    buttons[i].style.color = '#1A5276';
                } else {
                    buttons[i].style.background = 'transparent';
                    buttons[i].style.color = '#fff';
                }
            }
            var mp = document.querySelectorAll('.ms-price-monthly');
            var yp = document.querySelectorAll('.ms-price-yearly');
            var mb = document.querySelectorAll('.ms-btn-monthly');
            var yb = document.querySelectorAll('.ms-btn-yearly');
            for (var i = 0; i < mp.length; i++) mp[i].style.display = cycle === 'monthly' ? 'block' : 'none';
            for (var i = 0; i < yp.length; i++) yp[i].style.display = cycle === 'yearly' ? 'block' : 'none';
            for (var i = 0; i < mb.length; i++) mb[i].style.display = cycle === 'monthly' ? 'block' : 'none';
            for (var i = 0; i < yb.length; i++) yb[i].style.display = cycle === 'yearly' ? 'block' : 'none';
        }

        for (var i = 0; i < buttons.length; i++) {
            (function(btn) {
                btn.addEventListener('click', function() {
                    setCycle(btn.getAttribute('data-cycle'));
                });
            })(buttons[i]);
        }
        setCycle('monthly');
    }

    if (document.readyState === 'complete') { initPricing(); }
    else { window.addEventListener('load', initPricing); }
    setTimeout(initPricing, 1000);
    setTimeout(initPricing, 3000);
})();
