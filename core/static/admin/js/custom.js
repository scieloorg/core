document.addEventListener('DOMContentLoaded', function() {
    const collectionSelect = document.querySelector('select[name="collection"]');
    const journalSelect = document.querySelector('select[name="journal"]');
    console.log("Journal Select:", journalSelect);

    function updateJournals() {
        // Sempre pega os valores selecionados no momento da atualização
        const currentJournalIds = Array.from(journalSelect.selectedOptions).map(option => option.value);
        console.log("Current Journal IDs:", currentJournalIds);

        const selectedCollections = Array.from(collectionSelect.options)
                                    .filter(option => option.selected)
                                    .map(option => option.value);
        fetch(`/filter_journals/?collections[]=${selectedCollections.join('&collections[]=')}`)
            .then(response => response.json())
            .then(data => {
                journalSelect.innerHTML = '';

                data.forEach(function(journal) {
                    const option = new Option(journal.name, journal.id);
                    if (currentJournalIds.includes(journal.id.toString())) {
                        option.selected = true;
                    }
                    journalSelect.add(option);
                });
                // Se nenhum dos IDs antigos está presente, limpa seleção
                const hasSelected = currentJournalIds.some(id => journalSelect.querySelector(`option[value="${id}"]`));
                if (!hasSelected) {
                    journalSelect.value = "";
                }
            })
            .catch(error => console.error('Error:', error));
    }

    if (collectionSelect && journalSelect) {
        collectionSelect.addEventListener('change', updateJournals);
        updateJournals();
    }
});