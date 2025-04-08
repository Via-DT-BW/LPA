document.getElementById('apply-filters').addEventListener('click', function () {
    var linha = document.getElementById('filter_prod_line').value;
    var data_inicio = document.getElementById('filter_date_inicio').value;
    var data_fim = document.getElementById('filter_date_fim').value;

    if (!data_inicio || !data_fim) {
        toastr.error('Ambos os campos de data são obrigatórios!', 'Erro');
        return;
    }

    if (new Date(data_inicio) > new Date(data_fim)) {
        toastr.error('A data de início não pode ser maior que a data de fim!', 'Erro');
        return;
    }

    fetch("/get_lpa_data2", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            "linha": linha,
            "data_inicio": data_inicio,
            "data_fim": data_fim
        })
    })
        .then(response => response.json())
        .then(data => {
            var lpaList = document.getElementById('lpa-list');
            lpaList.innerHTML = '';

            if (data.length === 0) {
                lpaList.innerHTML = '<p class="text-muted ml-4 mt-2">Nenhum LPA encontrado para as datas selecionadas.</p>';
                toastr.info('Nenhum LPA encontrado.', 'Informação');
            } else {
                let groupedLPAs = {};

                data.forEach(lpa => {
                    if (new Date(lpa.data_auditoria) >= new Date(data_inicio) && new Date(lpa.data_auditoria) <= new Date(data_fim)) {
                        let key = `${lpa.linha} - ${formatarData(lpa.data_auditoria)}`;
                        if (!groupedLPAs[key]) {
                            groupedLPAs[key] = {
                                linha: lpa.linha,
                                data_auditoria: lpa.data_auditoria,
                                auditor: lpa.auditor
                            };
                        }
                    }
                });

                if (Object.keys(groupedLPAs).length === 0) {
                    lpaList.innerHTML = '<p class="text-muted ml-4 mt-2">Nenhum LPA encontrado nas datas especificadas.</p>';
                    toastr.info('Nenhum LPA encontrado nas datas selecionadas.', 'Informação');
                } else {
                    Object.keys(groupedLPAs).forEach(key => {
                        var item = `<div class="col-md-4 text-center">
                            <div class="card p-4">
                                <strong>${key}</strong>
                                <button class="btn btn-ver float-right" data-toggle="modal" data-target="#lpaModal"
                                    onclick="verDetalhes2('${groupedLPAs[key].linha}', '${groupedLPAs[key].data_auditoria}', '${groupedLPAs[key].auditor}')">
                                    <i class="fas fa-eye"></i> Ver
                                </button>
                            </div>
                        </div>`;
                        lpaList.insertAdjacentHTML('beforeend', item);
                    });
                    toastr.success('LPAs carregados com sucesso!', 'Sucesso');
                }
            }
        })
        .catch(error => {
            console.error('Erro ao carregar LPAs:', error);
            toastr.error('Erro ao carregar LPAs.', 'Erro');
        });
});

function verDetalhes2(linha, dataAuditoria, auditor) {
    fetch("/get_lpa_details2", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            "linha": linha,
            "data_auditoria": dataAuditoria
        })
    })
        .then(response => response.json())
        .then(data => {
            console.log("Resposta da API:", data); // Adicionando um log para ajudar na depuração.

            var modalBody = document.getElementById('modalBody2');
            if (!modalBody) {
                console.error('Elemento modalBody2 não encontrado.');
                return;
            }
            modalBody.innerHTML = '';

            let headerInfo = `
                <div class="audit-info-header mb-4">
                    <div class="card border-primary">
                        <div class="card-body p-3">
                            <div class="row">
                                <div class="col-md-6">
                                    <p class="mb-1"><strong><i class="fas fa-industry mr-2"></i> Linha:</strong> ${linha}</p>
                                    <p class="mb-1"><strong><i class="fas fa-calendar-alt mr-2"></i> Data:</strong> ${formatarData(dataAuditoria)}</p>
                                </div>
                                <div class="col-md-6">
                                    <p class="mb-1"><strong><i class="fas fa-user mr-2"></i> Auditor:</strong> ${auditor}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            modalBody.innerHTML = headerInfo;

            // Verificar se a resposta é um array
            if (!Array.isArray(data) || data.length === 0) {
                modalBody.innerHTML += '<p class="text-muted text-center">Nenhum detalhe encontrado.</p>';
            } else {
                let tableContent = `
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th>Pergunta</th>
                                <th class="text-center">Resposta</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                // Se a resposta for um array, processamos os dados
                data.forEach(item => {
                    let responseClass = item.resposta === 'OK' ? 'status-ok' : 'status-nok';

                    tableContent += `
                        <tr>
                            <td>${item.pergunta}</td>
                            <td class="text-center">
                                <span class="${responseClass}">${item.resposta}</span>
                            </td>
                        </tr>
                    `;
                });

                tableContent += `</tbody></table>`;
                modalBody.innerHTML += tableContent;
            }
        })
        .catch(error => {
            console.error('Erro ao carregar detalhes do LPA 2ª Camada:', error);
            var modalBody = document.getElementById('modalBody2');
            if (modalBody) {
                modalBody.innerHTML = `
                    <div class="alert alert-danger text-center" role="alert">
                        <i class="fas fa-exclamation-triangle mr-2"></i>
                        Erro ao carregar os detalhes do LPA 2ª Camada. Por favor, tente novamente.
                    </div>
                `;
            }
        });
}

function formatarData(dataString) {
    if (!dataString) return '-';
    try {
        const data = new Date(dataString);
        const dia = String(data.getDate()).padStart(2, '0');
        const mes = String(data.getMonth() + 1).padStart(2, '0'); // Mês começa em 0
        const ano = data.getFullYear();
        return `${dia}/${mes}/${ano}`;
    } catch (e) {
        console.error("Erro ao formatar data:", e);
        return dataString;
    }
}