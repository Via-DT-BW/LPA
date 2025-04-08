function toggleNokFields2(index) {
    const nokFields = document.getElementById(`nokFields${index}`);
    const nokRadio = document.getElementById(`nok${index}`);
    const ncRadio = document.getElementById(`nc${index}`);
    
    if (nokRadio.checked) {
        nokFields.style.display = 'block';
    } else {
        nokFields.style.display = 'none';
    }
}    