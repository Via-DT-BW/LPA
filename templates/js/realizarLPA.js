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
                    <div class="form-group mb-4 pb-3 border-bottom">
                        <div class="d-flex align-items-center mb-2">
                            <span class="badge badge-secondary mr-2">${index + 1}</span>
                            <label class="mb-0"><strong>${item.pergunta}</strong></label>
                        </div>
                        <div class="radio-group mt-3">
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
                        <div id="nokFields${index}" class="nok-description mt-3">
                            <div class="form-group">
                                <label><i class="fas fa-exclamation-triangle text-danger mr-1"></i> <strong>Incidência (explicar a não conformidade)</strong></label>
                                <input type="text" class="form-control" placeholder="Descreva a não conformidade..." id="naoConformidade${index}">
                            </div>
                            <div class="form-group">
                                <label><i class="fas fa-tools mr-1"></i> <strong>Ação corretiva (a definir pelos responsáveis da linha TL, PL, PLM).</strong></label>
                                <input type="text" class="form-control" placeholder="Ação corretiva..." id="acaoCorretiva${index}">
                            </div>
                            <div class="form-group mb-0">
                                <label><i class="far fa-calendar-alt mr-1"></i> <strong>Prazo</strong></label>
                                <input type="date" class="form-control" id="prazo${index}">
                            </div>
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