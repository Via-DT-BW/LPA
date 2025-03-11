document.getElementById('apply-filters').addEventListener('click', function() {
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

    fetch("/get_lpa_data", {
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
                    let key = `${lpa.linha} - Turno ${lpa.turno} - ${lpa.data_auditoria}`;
                    if (!groupedLPAs[key]) {
                        groupedLPAs[key] = {
                            linha: lpa.linha,
                            data_auditoria: lpa.data_auditoria,
                            turno: lpa.turno,
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
                                onclick="verDetalhes('${groupedLPAs[key].linha}', '${groupedLPAs[key].data_auditoria}', '${groupedLPAs[key].turno}')">
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

function verDetalhes(linha, dataAuditoria, turno) {
    fetch("/get_lpa_details", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            "linha": linha,
            "data_auditoria": dataAuditoria,
            "turno": turno
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Resposta da API:", data);
        var modalBody = document.getElementById('modalBody');
        if (!modalBody) {
            console.error('Elemento modalBody não encontrado.');
            return;
        }
        modalBody.innerHTML = ''; 

        if (data.error) {
            modalBody.innerHTML = `<p class="text-muted text-center">${data.error}</p>`;
        } else if (data.length === 0) {
            modalBody.innerHTML = '<p class="text-muted text-center">Nenhum detalhe encontrado.</p>';
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

            if (Array.isArray(data)) {
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
            } else {
                modalBody.innerHTML = '<p class="text-muted text-center">Formato de resposta inválido.</p>';
            }

            tableContent += `</tbody></table>`;
            modalBody.innerHTML += tableContent;
        }
    })
    .catch(error => {
        console.error('Erro ao carregar detalhes do LPA:', error);
        var modalBody = document.getElementById('modalBody');
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="alert alert-danger text-center" role="alert">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    Erro ao carregar os detalhes do LPA!
                </div>
            `;
        }
    });
}
