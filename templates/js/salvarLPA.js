function salvarLPA() {
    var selectedLine = document.getElementById("filter_prod_line").value;
    var dataAuditoria = formatarDataAtual();
    var turno = document.getElementById("turno").value;
    var registoPeca = document.getElementById("numeroPeca").value;
    var respostas = [];

    document.querySelectorAll("#lpa-items .form-group").forEach((item, index) => {
        var pergunta = item.querySelector("label").innerText.split(" - ")[1];
        var resposta = document.querySelector(`input[name="item${index}"]:checked`);

        if (resposta) {
            var respostaObj = {
                pergunta: pergunta,
                resposta: resposta.value
            };

            if (resposta.value === "NOK") {
                respostaObj.nao_conformidade = document.getElementById(`naoConformidade${index}`).value;
                respostaObj.acao_corretiva = document.getElementById(`acaoCorretiva${index}`).value;

                var prazoInput = document.getElementById(`prazo${index}`);
                if (prazoInput && prazoInput.value) {
                    respostaObj.prazo = formatarDataPrazo(prazoInput.value);
                }
            }

            respostas.push(respostaObj);
        }
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
