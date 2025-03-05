function realizarLPA() {
    var selectedLine = document.getElementById("filter_prod_line").value;
    if (!selectedLine) {
        alert("Selecione uma linha de produção primeiro.");
        return;
    }

    fetch("/get_user_data")
    .then(response => response.json())
    .then(user => {
        document.getElementById("Nr_colaborador").value = user.Nr_colaborador || "";
        document.getElementById("username").value = user.username || "";

        document.getElementById("selected-line").innerText = selectedLine;
        document.getElementById("dataAtual").value = formatarDataAtual();
        document.getElementById("lpa-section").classList.remove("hidden");

        fetch("/get_data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ production_line: selectedLine })
        })
        .then(response => response.json())
        .then(data => {
            var lpaItemsContainer = document.getElementById("lpa-items");
            lpaItemsContainer.innerHTML = "";
            if (!data.length) {
                alert("Nenhuma pergunta encontrada para esta linha de produção.");
                return;
            }

            data.forEach((item, index) => {
                lpaItemsContainer.innerHTML += `
                    <div class="form-group">
                        <label>${index + 1} - ${item.pergunta}</label>
                        <div class="radio-group">
                            <div class="custom-control custom-radio custom-control-inline">
                                <input type="radio" id="ok${index}" name="item${index}" value="OK" 
                                    class="custom-control-input" onchange="toggleNokFields(${index})">
                                <label class="custom-control-label" for="ok${index}">OK</label>
                            </div>
                            <div class="custom-control custom-radio custom-control-inline">
                                <input type="radio" id="nok${index}" name="item${index}" value="NOK" 
                                    class="custom-control-input" onchange="toggleNokFields(${index})">
                                <label class="custom-control-label" for="nok${index}">NOK</label>
                            </div>
                            <div class="custom-control custom-radio custom-control-inline">
                                <input type="radio" id="nc${index}" name="item${index}" value="NC" 
                                    class="custom-control-input" onchange="toggleNokFields(${index})">
                                <label class="custom-control-label" for="nc${index}">NC</label>
                            </div>
                            <div class="custom-control custom-radio custom-control-inline">
                                <input type="radio" id="nt${index}" name="item${index}" value="NT" 
                                    class="custom-control-input" onchange="toggleNokFields(${index})">
                                <label class="custom-control-label" for="nt${index}">NT</label>
                            </div>
                        </div>
                        <div id="nokFields${index}" class="nok-description">
                            <input type="text" class="form-control mt-2" placeholder="Descreva a não conformidade..." id="naoConformidade${index}">
                            <input type="text" class="form-control mt-2" placeholder="Ação corretiva..." id="acaoCorretiva${index}">
                            <input type="date" class="form-control mt-2" id="prazo${index}">
                        </div>
                    </div>
                `;
            });                        
        });
    })
    .catch(error => {
        console.error("Erro ao buscar dados do usuário:", error);
        alert("Erro ao carregar os dados do usuário.");
    });
}
