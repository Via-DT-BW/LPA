function salvarLPA() {
    var selectedLine = document.getElementById("filter_prod_line").value;
    var dataAuditoria = formatarDataAtual(); 
    var turno = document.getElementById("turno").value;
    var registoPeca = document.getElementById("numeroPeca").value;
    var respostas = [];

    if (!selectedLine || !turno || !registoPeca) {
        alert("Por favor, preencha todos os campos obrigatórios antes de salvar.");
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
                    alert(`Preencha todos os campos para a não conformidade na pergunta ${index + 1}.`);
                    return;
                }

                respostaObj.nao_conformidade = naoConformidade;
                respostaObj.acao_corretiva = acaoCorretiva;
                respostaObj.prazo = formatarDataPrazo(prazoInput); 
            }

            respostas.push(respostaObj);
        }
    });

    if (respostas.length === 0) {
        alert("Por favor, responda a pelo menos uma pergunta.");
        return;
    }

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
        if (data.success) {
            alert("LPA salvo com sucesso!");
            location.reload();  
        } else {
            alert("Erro ao salvar LPA: " + data.error);
        }
    })
    .catch(error => {
        console.error("Erro ao salvar LPA:", error);
        alert("Erro ao salvar. Tente novamente.");
    });
}

