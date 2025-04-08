function salvarLPA2(event) {
    event.preventDefault();
    var selectedLine = document.getElementById("filter_prod_line").value;
    var dataAuditoria = formatarDataAtual2();
    var registoPeca = document.getElementById("numeroPeca").value;
    var respostas = [];
    var hasValidationError = false;

    if (!selectedLine || !registoPeca) {
        toastr.error("Por favor, preencha todos os campos obrigatórios antes de submeter.");
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

                let ano = new Date(prazoInput).getFullYear().toString();
                if (!/^\d{4}$/.test(ano)) {
                    toastr.error(`O ano do prazo na pergunta ${index + 1} deve ter 4 dígitos.`);
                    hasValidationError = true;
                    return;
                }

                let anoNum = parseInt(ano, 10);
                if (anoNum < 2000 || anoNum > 2099) {
                    toastr.error(`O ano do prazo na pergunta ${index + 1} deve estar entre 2000 e 2099.`);
                    hasValidationError = true;
                    return;
                }

                respostaObj.nao_conformidade = naoConformidade;
                respostaObj.acao_corretiva = acaoCorretiva;
                respostaObj.prazo = formatarDataPrazo2(prazoInput);
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

    var loadingToast = toastr.info("A submeter LPA de 2ª camada...", {
        timeOut: 0,
        extendedTimeOut: 0,
        tapToDismiss: false,
        closeButton: false,
        progressBar: true
    });

    fetch("/save_lpa2", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            linha: selectedLine,
            data_auditoria: dataAuditoria,
            registo_peca: registoPeca,
            respostas: respostas
        })
    })
    .then(response => response.json())
    .then(data => {
        toastr.clear(loadingToast);
        if (data.success) {
            toastr.success("LPA de 2ª camada guardado com sucesso!");
            setTimeout(() => {
                window.location.href = "/2_camada";
            }, 1500);
        } else {
            toastr.error("Erro ao guardar LPA de 2ª camada: " + data.error);
        }
    })
    .catch(error => {
        toastr.clear(loadingToast);
        toastr.error("Erro ao guardar. Tente novamente.");
    });
}