// Letras de A a Z
const letters = Array.from({length: 26}, (_, i) => String.fromCharCode(65 + i));
const btnGroup = document.getElementById('letterBtnGroup');
const letterInput = document.getElementById('letterInput');
const form = document.getElementById('letterFilterForm');

letters.forEach(letter => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-sm btn-default';
    btn.textContent = letter;
    btn.onclick = function() {
        letterInput.value = letter;
        form.submit();
    };
    btnGroup.appendChild(btn);
});