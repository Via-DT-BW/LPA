function toggleNokFields3(index) {
    const isNok = document.getElementById(`nok${index}`).checked;
    const fields = document.getElementById(`nokFields${index}`);
    fields.style.display = isNok ? "block" : "none";
}
