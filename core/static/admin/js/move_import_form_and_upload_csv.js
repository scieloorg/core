document.addEventListener("DOMContentLoaded", function () {
    const importForm = document.querySelector("form[action*='import']");
    const addButton = document.querySelector("#w-slim-header-buttons");

    if (importForm && addButton) {
        // Remove margens ou define estilo flex se necessário
        importForm.style.marginLeft = "10px";
        importForm.style.display = "inline-block";

        // Move o formulário para logo após o botão "Adicionar organization"
        addButton.appendChild(importForm);
    }
});
// Envia requisição POST para importar CSV e retorna mensagem
document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('csvFileInput');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;


    fileInput.addEventListener('change', function () {
        const formData = new FormData();
        formData.append('csv_file', fileInput.files[0]);

        const pathParts = window.location.pathname.split("/");
        const typeCsv = pathParts[pathParts.length - 2];
        
        formData.append('type_csv', typeCsv);

        fetch("{% url 'import_csv' %}", {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
            },
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            if (data.status) {
                alert(data.message);
                window.location.reload();
            } else {
                alert(data.message);
                window.location.reload();
            }
        })
    });
});
