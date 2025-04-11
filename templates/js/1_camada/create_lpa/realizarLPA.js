function realizarLPA() {
    const selectedLine = document.getElementById("filter_prod_line").value;
    if (!selectedLine) {
        toastr.warning("Selecione uma linha de produção primeiro.", "Aviso");
        return;
    }

    fetch("/get_user_data")
        .then(response => response.json())
        .then(user => {
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
                    const lpaItemsContainer = document.getElementById("lpa-items");
                    lpaItemsContainer.innerHTML = "";

                    if (!data.length) {
                        toastr.error("Nenhuma pergunta encontrada para esta linha de produção.", "Erro");
                        return;
                    }

                    data.forEach((item, index) => {
                        lpaItemsContainer.innerHTML += `
                            <div class="form-group mb-4">
                                <label class="font-weight-bold">${index + 1} - ${item.pergunta}</label>
                                <small class="form-text text-muted mt-1">OBJETIVO: ${item.objetivo || "Não definido"}</small>

                                <div class="btn-group btn-group-toggle mt-2" data-toggle="buttons">
                                    <label class="btn btn-outline-success">
                                        <input type="radio" name="item${index}" id="ok${index}" value="OK" autocomplete="off" onchange="toggleNokFields(${index})"> OK
                                    </label>
                                    <label class="btn btn-outline-danger">
                                        <input type="radio" name="item${index}" id="nok${index}" value="NOK" autocomplete="off" onchange="toggleNokFields(${index})"> NOK
                                    </label>
                                    <label class="btn btn-outline-warning">
                                        <input type="radio" name="item${index}" id="nc${index}" value="NC" autocomplete="off" onchange="toggleNokFields(${index})"> NC
                                    </label>
                                    <label class="btn btn-outline-secondary">
                                        <input type="radio" name="item${index}" id="nt${index}" value="NT" autocomplete="off" onchange="toggleNokFields(${index})"> NT
                                    </label>
                                </div>

                                <div id="nokFields${index}" class="nok-description mt-3" style="display: none;">
                                    <input type="text" class="form-control mt-2" placeholder="Descreva a não conformidade..." id="naoConformidade${index}">
                                    <input type="text" class="form-control mt-2" placeholder="Ação corretiva..." id="acaoCorretiva${index}">
                                    <input type="date" class="form-control mt-2" id="prazo${index}">
                                </div>
                            </div>
                        `;
                    });

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
