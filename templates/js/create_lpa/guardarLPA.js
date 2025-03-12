function salvarLPA(event) {
    event.preventDefault();

    var selectedLine = document.getElementById("filter_prod_line").value;
    var dataAuditoria = formatarDataAtual();
    var turno = document.getElementById("turno").value;
    var registoPeca = document.getElementById("numeroPeca").value;
    var respostas = [];
    var hasValidationError = false;

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
                var naoConformidade = document.getElementById(`naoConformidade${index}`).value;
                var acaoCorretiva = document.getElementById(`acaoCorretiva${index}`).value;
                var prazoInput = document.getElementById(`prazo${index}`).value;

                if (!naoConformidade || !acaoCorretiva || !prazoInput) {
                    toastr.error(`Preencha todos os campos para a não conformidade na pergunta ${index + 1}.`);
                    hasValidationError = true;
                    return;
                }

                respostaObj.nao_conformidade = naoConformidade;
                respostaObj.acao_corretiva = acaoCorretiva;
                respostaObj.prazo = formatarDataPrazo(prazoInput);
            }

            respostas.push(respostaObj);
        }
    });

    if (hasValidationError) {
        return;
    }

    if (respostas.length === 0) {
        toastr.error("Por favor, responda a pelo menos uma pergunta.");
        return;
    }

    // 🟢 Exibir Toastr de carregamento
    var loadingToast = toastr.info("Salvando LPA...", {
        timeOut: 0, // Não fecha automaticamente
        extendedTimeOut: 0,
        tapToDismiss: false,
        closeButton: false,
        progressBar: true
    });

    console.log("Respostas capturadas:", respostas.length);

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
        toastr.clear(loadingToast); // Remover Toastr de carregamento

        if (data.success) {
            toastr.success("LPA guardado com sucesso!");

            // 🔹 Pequeno delay antes de recarregar a página (para o toastr ser visto)
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            toastr.error("Erro ao guardar LPA: " + data.error);
        }
    })
    .catch(error => {
        toastr.clear(loadingToast);
        console.error("Erro ao guardar LPA:", error);
        toastr.error("Erro ao guardar. Tente novamente.");
    });
}
