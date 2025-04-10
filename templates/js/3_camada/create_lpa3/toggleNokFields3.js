function toggleNokFields3(index, selectedValue) {
    // Remove a classe 'selected' de todos os botões
    const buttons = document.querySelectorAll(`#ok${index}, #nok${index}, #nc${index}, #nt${index}`);
    buttons.forEach(button => button.classList.remove("selected"));

    // Adiciona a classe 'selected' ao botão clicado
    const selectedButton = document.getElementById(`${selectedValue.toLowerCase()}${index}`);
    selectedButton.classList.add("selected");

    // Exibe ou esconde o campo de descrição dependendo da opção
    const nokFields = document.getElementById(`nokFields${index}`);
    
    if (selectedValue === "NOK") {
        nokFields.style.display = 'block'; // Exibe o campo de descrição
    } else {
        nokFields.style.display = 'none'; // Esconde o campo de descrição
    }
}
