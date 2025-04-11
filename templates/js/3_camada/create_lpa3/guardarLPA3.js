function salvarLPA3(event) {
    event.preventDefault();
    var selectedLine = document.getElementById("filter_prod_line").value;
    var dataAuditoria = formatarDataAtual3();
    var registoPeca = document.getElementById("numeroPeca").value;
    var respostas = [];
    var hasValidationError = false;

    if (!selectedLine || !registoPeca) {
        toastr.error("Por favor, preencha todos os campos obrigatórios antes de submeter.");
        return;
    }

    var perguntas = document.querySelectorAll("#lpa-items .form-group");

    for (let index = 0; index < perguntas.length; index++) {
        let item = perguntas[index];
        let pergunta = item.querySelector("label").innerText.split(" - ")[1];
        let resposta = document.querySelector(`input[name="item${index}"]:checked`);

        if (!resposta) {
            toastr.error(`Por favor, responda à pergunta ${index + 1} antes de submeter.`);
            return;
        }

        let respostaObj = {
            pergunta: pergunta,
            resposta: resposta.value
        };

        if (resposta.value === "NOK") {
            let naoConformidade = document.getElementById(`naoConformidade${index}`).value;
            let acaoCorretiva = document.getElementById(`acaoCorretiva${index}`).value;
            let prazoInput = document.getElementById(`prazo${index}`).value;

            if (!naoConformidade || !acaoCorretiva || !prazoInput) {
                toastr.error(`Preencha todos os campos para a não conformidade na pergunta ${index + 1}.`);
                return;
            }

            let ano = new Date(prazoInput).getFullYear().toString();
            if (!/^\d{4}$/.test(ano)) {
                toastr.error(`O ano do prazo na pergunta ${index + 1} deve ter 4 dígitos.`);
                return;
            }

            let anoNum = parseInt(ano, 10);
            if (anoNum < 2000 || anoNum > 2099) {
                toastr.error(`O ano do prazo na pergunta ${index + 1} deve estar entre 2000 e 2099.`);
                return;
            }

            respostaObj.nao_conformidade = naoConformidade;
            respostaObj.acao_corretiva = acaoCorretiva;
            respostaObj.prazo = formatarDataPrazo3(prazoInput);
        }

        respostas.push(respostaObj);
    }

    var loadingToast = toastr.info("A submeter LPA de 3ª camada...", {
        timeOut: 0,
        extendedTimeOut: 0,
        tapToDismiss: false,
        closeButton: false,
        progressBar: true
    });

    fetch("/save_lpa3", {
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
            toastr.success("LPA de 3ª camada guardado com sucesso!");
            setTimeout(() => {
                window.location.href = "/3_camada";
            }, 1500);
        } else {
            toastr.error("Erro ao guardar LPA de 3ª camada: " + data.error);
        }
    })
    .catch(error => {
        toastr.clear(loadingToast);
        toastr.error("Erro ao guardar. Tente novamente.");
    });
}
