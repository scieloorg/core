/* your custom js go here */
document.addEventListener('DOMContentLoaded', function() {
    const collectionSelect = document.querySelector('select[name="collection"]');
    const journalSelect = document.querySelector('select[name="journal"]');
    const currentJournalId = journalSelect.value; // Armazena o valor atual do journal

    function updateJournals() {
        const selectedCollections = Array.from(collectionSelect.options)
                                    .filter(option => option.selected)
                                    .map(option => option.value);
        fetch(`/filter_journals/?collections[]=${selectedCollections.join('&collections[]=')}`)
            .then(response => response.json())
            .then(data => {
                journalSelect.innerHTML = '';
                const defaultOption = new Option("Selecione um Journal", "");
                journalSelect.add(defaultOption);

                data.forEach(function(journal) {
                    const option = new Option(journal.name, journal.id);
                    if (journal.id.toString() === currentJournalId) {
                        option.selected = true;
                    }
                    journalSelect.add(option);
                });
                if (!journalSelect.querySelector(`option[value="${currentJournalId}"]`)) {
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

// document.addEventListener('DOMContentLoaded', function() {
//     const collectionSelect = document.querySelector('select[name="collection"]');
//     const journalSelect = document.querySelector('select[name="journal"]');

//     function updateJournals() {
//         const selectedCollections = Array.from(collectionSelect.options)
//                                     .filter(option => option.selected)
//                                     .map(option => option.value);
//         fetch(`/filter_journals/?collections[]=${selectedCollections.join('&collections[]=')}`)
//             .then(response => response.json())
//             .then(data => {
//                 journalSelect.innerHTML = '';
//                 // Adicione uma opção vazia ou com texto de 'nenhuma seleção'
//                 const defaultOption = new Option("Selecione um Journal", "");
//                 journalSelect.add(defaultOption);
//                 data.forEach(function(journal) {
//                     const option = new Option(journal.name, journal.id);
//                     journalSelect.add(option);
//                 });
//             })
//             .catch(error => console.error('Error:', error));
//     }
    

//     if (collectionSelect && journalSelect) {
//         collectionSelect.addEventListener('change', updateJournals);
//         updateJournals();
//     }
// });