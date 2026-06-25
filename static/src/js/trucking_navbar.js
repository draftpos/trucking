/** @odoo-module **/

const observer = new MutationObserver(() => {
    const brandEls = document.querySelectorAll('.o_menu_brand, .o_navbar_brand');
    brandEls.forEach(brandEl => {
        if (brandEl && brandEl.textContent.trim() === 'Trucking') {
            brandEl.style.display = 'none';
        } else if (brandEl) {
            brandEl.style.display = '';
        }
    });
});

observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
