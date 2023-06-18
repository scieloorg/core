function highlight(term, element) {
    // Highlight
    options = {
        'diacritics': true,
        'separateWordSearch': true,
        'debug': false,
        'filter': function (node, term, totalCounter, counter) {
            if ($.inArray(term, stopwords) != -1) {
                return false;
            } else {
                return true;
            }
        }
    };

    $(element).mark(term, options);
}


function addHidden(form, key, value) {
    // Create a hidden input element, and append it to the form:
    $('<input>').attr({
        type: 'hidden',
        id: key,
        name: key,
        value: value
    }).appendTo(form);

}