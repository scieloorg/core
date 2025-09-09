document.addEventListener("DOMContentLoaded", function() {
    var currentUrl = encodeURIComponent(window.location.href);

    // Facebook
    var fb = document.querySelector('.glyphBtn.facebook').parentElement;
    if (fb) fb.href = "https://www.facebook.com/sharer/sharer.php?u=" + currentUrl;

    // Twitter
    var tw = document.querySelector('.glyphBtn.twitter').parentElement;
    if (tw) tw.href = "https://twitter.com/intent/tweet?text=" + currentUrl;

    // Google+
    var gp = document.querySelector('.shareGooglePlus');
    if (gp) gp.href = "https://plus.google.com/share?url=" + currentUrl;

    // LinkedIn
    var li = document.querySelector('.shareLinkedIn');
    if (li) li.href = "https://www.linkedin.com/shareArticle?mini=true&url=" + currentUrl;

    // Reddit
    var rd = document.querySelector('.shareReddit');
    if (rd) rd.href = "https://www.reddit.com/submit?url=" + currentUrl;

    // StumbleUpon
    var su = document.querySelector('.shareStambleUpon');
    if (su) su.href = "https://www.stumbleupon.com/submit?url=" + currentUrl;

    // CiteULike
    var cu = document.querySelector('.shareCiteULike');
    if (cu) cu.href = "https://www.citeulike.org/posturl?url=" + currentUrl;

    // Mendeley
    var md = document.querySelector('.shareMendeley');
    if (md) md.href = "https://www.mendeley.com/import/?url=" + currentUrl;
});

// Responsivo: abre/fecha o menu ao clicar no botão de compartilhar
document.addEventListener("DOMContentLoaded", function() {
    const btn = document.getElementById('dropdown-menu-share');
    const menu = document.getElementById('menu-share');

    btn.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = menu.style.display === 'block';
        menu.style.display = isOpen ? 'none' : 'block';
        btn.setAttribute('aria-expanded', !isOpen);
    });

    // Fecha o menu ao clicar fora
    document.addEventListener('click', function(e) {
        if (menu.style.display === 'block') {
            menu.style.display = 'none';
            btn.setAttribute('aria-expanded', 'false');
        }
    });

    // Impede o fechamento ao clicar dentro do menu
    menu.addEventListener('click', function(e) {
        e.stopPropagation();
    });
});