function formatarDataAtual() {
    const dataAtual = new Date();
    const dia = String(dataAtual.getDate()).padStart(2, '0');
    const mes = String(dataAtual.getMonth() + 1).padStart(2, '0');
    const ano = dataAtual.getFullYear();
    const horas = String(dataAtual.getHours()).padStart(2, '0');
    const minutos = String(dataAtual.getMinutes()).padStart(2, '0');
    
    return `${dia}/${mes}/${ano} - ${horas}:${minutos}`;
}

function salvarLPA() {
    var selectedLine = document.getElementById("filter_prod_line").value;
    var dataAuditoria = formatarDataAtual();
    var turno = document.getElementById("turno").value;
    var registoPeca = document.getElementById("numeroPeca").value;
    var respostas = [];
    var valido = true;  

    document.querySelectorAll("#lpa-items .form-group").forEach((item, index) => {
        var pergunta = item.querySelector("label").innerText;
        var resposta = document.querySelector(`input[name="item${index}"]:checked`);
        
        if (resposta) {
            var respostaObj = {
                pergunta: pergunta,
                resposta: resposta.value
            };

            if (resposta.value === "NOK") {
                var naoConformidade = document.getElementById(`naoConformidade${index}`).value;
                var acaoCorretiva = document.getElementById(`acaoCorretiva${index}`).value;

                if (!naoConformidade.trim() || !acaoCorretiva.trim()) {
                    valido = false;
                    alert(`Por favor, preencha todos os campos de descrição e ação corretiva para a pergunta: ${pergunta}`);
                    return; 
                }

                respostaObj.nao_conformidade = naoConformidade;
                respostaObj.acao_corretiva = acaoCorretiva;
                
                var prazoInput = document.getElementById(`prazo${index}`);
                if (prazoInput && prazoInput.value) {
                    respostaObj.prazo = formatarDataPrazo(prazoInput.value);
                }
            }

            respostas.push(respostaObj);
        }
    });

    if (!valido) {
        return;  
    }

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