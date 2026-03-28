(function() {
    const API_ENDPOINT = "https://salemmania.org/";
    fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            path: window.location.pathname,
            referrer: document.referrer
        })
    }).catch(() => {}); // Silent fail
})();
