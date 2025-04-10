function toggleNokFields3(index, selectedValue) {
    // Remove a cor de fundo de todos os botões
    const buttons = document.querySelectorAll(`#ok${index}, #nok${index}, #nc${index}, #nt${index}`);
    buttons.forEach(button => {
        button.style.backgroundColor = ""; 
        button.style.color = ""; 
    });

    const selectedButton = document.getElementById(`${selectedValue.toLowerCase()}${index}`);
    
    if (selectedValue === "OK") {
        selectedButton.style.backgroundColor = "#28a745"; 
        selectedButton.style.color = "white"; 
    } else if (selectedValue === "NOK") {
        selectedButton.style.backgroundColor = "#dc3545"; 
        selectedButton.style.color = "white"; 
    } else if (selectedValue === "NC") {
        selectedButton.style.backgroundColor = "#ffc107"; 
        selectedButton.style.color = "white"; 
    } else if (selectedValue === "NT") {
        selectedButton.style.backgroundColor = "#6c757d";
        selectedButton.style.color = "white"; 
    }

    const nokFields = document.getElementById(`nokFields${index}`);
    
    if (selectedValue === "NOK") {
        nokFields.style.display = 'block'; 
    } else {
        nokFields.style.display = 'none';
    }
}
