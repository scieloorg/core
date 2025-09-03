function adicionarParametrosUrlAoForm(form) {
  const urlParams = new URLSearchParams(window.location.search);

  urlParams.forEach((value, key) => {
    if (!form.querySelector(`[name="${key}"]`)) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = key;
      input.value = value;
      form.appendChild(input);
    }
  });
}

// Aplicar a todos os formulários automaticamente
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', function(e) {
    const submitter = e.submitter
    if (submitter && submitter.id == 'tab-all') {
      e.preventDefault();
      window.location.href = this.getAttribute('action') || window.location.pathname;
      return;
    }
    adicionarParametrosUrlAoForm(this);
  });
});