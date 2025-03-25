function realizarLPA() {
    var selectedLine = document.getElementById("filter_prod_line").value;
    if (!selectedLine) {
        toastr.warning("Selecione uma linha de produção primeiro.", "Aviso");
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
                        toastr.error("Nenhuma pergunta encontrada para esta linha de produção.", "Erro");
                        return;
                    }

                    data.forEach((item, index) => {
                        lpaItemsContainer.innerHTML += `
                            <div class="form-group">
                                <label>${index + 1} - ${item.pergunta}</label>
                                <small class="form-text text-muted mt-2">
                                    OBJETIVO: ${item.objetivo || "Não definido"}
                                </small>
                                <div class="radio-group mt-2">
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

                    toastr.success("Dados carregados com sucesso!", "Sucesso");
                })
                .catch(error => {
                    console.error("Erro ao buscar dados:", error);
                    toastr.error("Erro ao carregar os dados.", "Erro");
                });
        })
        .catch(error => {
            console.error("Erro ao buscar dados do usuário:", error);
            toastr.error("Erro ao carregar os dados do usuário.", "Erro");
        });
}
