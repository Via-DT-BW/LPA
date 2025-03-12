function salvarLPA(event) {
    event.preventDefault();
    
    var selectedLine = document.getElementById("filter_prod_line").value;
    var dataAuditoria = formatarDataAtual();
    var turno = document.getElementById("turno").value;
    var registoPeca = document.getElementById("numeroPeca").value;
    var respostas = [];
    var hasValidationError = false; // Add this flag
    
    if (!selectedLine || !turno || !registoPeca) {
        toastr.error("Por favor, preencha todos os campos obrigatórios antes de salvar.");
        return;
    }
    
    document.querySelectorAll("#lpa-items .form-group").forEach((item, index) => {
        var pergunta = item.querySelector("label").innerText.split(" - ")[1];
        var resposta = document.querySelector(`input[name="item${index}"]:checked`);
        
        if (resposta) {
            var respostaObj = {
                pergunta: pergunta,
                resposta: resposta.value
            };
            
            if (resposta.value === "NOK") {
                // Verificar se os campos obrigatórios estão preenchidos
                var naoConformidade = document.getElementById(`naoConformidade${index}`).value;
                var acaoCorretiva = document.getElementById(`acaoCorretiva${index}`).value;
                var prazoInput = document.getElementById(`prazo${index}`).value;
                
                // Se algum dos campos obrigatórios estiver vazio, mostrar mensagem de erro
                if (!naoConformidade || !acaoCorretiva || !prazoInput) {
                    toastr.error(`Preencha todos os campos para a não conformidade na pergunta ${index + 1}.`);
                    hasValidationError = true; // Set the flag instead of return
                    return; // This only exits the current iteration
                }
                
                // Adicionar os dados de não conformidade ao objeto de resposta
                respostaObj.nao_conformidade = naoConformidade;
                respostaObj.acao_corretiva = acaoCorretiva;
                respostaObj.prazo = formatarDataPrazo(prazoInput);
            }
            
            // Adiciona a resposta à lista de respostas
            respostas.push(respostaObj);
        }
    });
    
    // Check validation flag before proceeding
    if (hasValidationError) {
        return; // Stop the function if there was a validation error
    }
    
    if (respostas.length === 0) {
        toastr.error("Por favor, responda a pelo menos uma pergunta.");
        return;
    }
    
    console.log("Respostas capturadas:", respostas.length);
    
    // Enviar os dados para o backend
    fetch("/save_lpa", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            linha: selectedLine,
            data_auditoria: dataAuditoria,
            turno: turno,
            registo_peca: registoPeca,
            respostas: respostas
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            toastr.success("LPA guardado com sucesso!");
            location.reload();  // Atualiza a página após salvar com sucesso
        } else {
            toastr.error("Erro ao guardar LPA: " + data.error);
        }
    })
    .catch(error => {
        console.error("Erro ao guardar LPA:", error);
        toastr.error("Erro ao guardar. Tente novamente.");
    });
}