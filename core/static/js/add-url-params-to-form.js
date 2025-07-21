function adicionarParametrosUrlAoForm(formId) {
  const urlParams = new URLSearchParams(window.location.search);
  const form = document.getElementById(formId);

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

document.getElementById('meuForm').addEventListener('submit', function(e) {
  adicionarParametrosUrlAoForm('meuForm');
});