document.addEventListener('DOMContentLoaded', function () {
  try {
    const holder = document.querySelector('#snippet-total-count');
    if (!holder) return;
    const total = holder.dataset.total ?? '';
    if (!total) return;

    // Encontra o último item do breadcrumb que representa a página atual
    // Estrutura típica: .w-breadcrumbs ol > li (o último é o "ativo")
    const breadcrumb = document.querySelector('.w-breadcrumbs');
    if (!breadcrumb) return;

    const items = breadcrumb.querySelectorAll('ol > li');
    if (!items.length) return;

    const currentItem = items[items.length - 1];

    // O link/título clicável dentro do item atual
    const link = currentItem.querySelector('a');
    if (!link) return;

    // Evita duplicar
    if (link.querySelector('.listing-total-pill')) return;

    const pill = document.createElement('span');
    pill.className = 'listing-total-pill';
    pill.textContent = `(${total})`;

    Object.assign(pill.style, {
      marginLeft: '6px',
      fontSize: '12px',
      lineHeight: '1',
      color: 'var(--w-color-text-meta, #9aa0a6)',
      verticalAlign: 'baseline'
    });

    link.appendChild(pill);

    holder.remove();
  } catch (e) {
    console.warn('Falha ao injetar total da listagem:', e);
  }
});